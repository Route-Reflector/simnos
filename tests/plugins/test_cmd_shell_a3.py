"""Integration tests for the A3 platform path through Nos -> CMDShell (#264 / PR-2).

PR-1 covered the legacy adapter end of `_rebuild`; these pin the new A3 branch:
`Nos._from_platform_dir` loads a platform dir into `resolved_platform`, and the
shell merges the still-legacy inflows (BASIC, py-module commands, inventory)
over the A3 statics with the right precedence and the A3 modes.

`TestA3HotReload` pins the #274/#281 dev hot-reload path on top: per-platform
watch rollup to a platform-dir target, per-shell snapshot isolation (multi-host /
multi-session), the per-host reload lock (#281 / D6), the `resolved_platform`
rollback, and the mode-degrade contract — all against tmp platforms (the real
tree is never mutated, so no xdist serialization is needed).
"""

import os
import threading
import time

import pytest

from simnos.core.host import HostRenderConfig
from simnos.core.nos import Nos
from simnos.plugins.shell import cmd_shell as cmd_shell_module
from simnos.plugins.shell.cmd_shell import CMDShell, build_resolved_platform


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _a3_platform(tmp_path, *, auth=None):
    """A minimal A3 cisco-like platform dir with user/enable/config modes."""
    root = tmp_path / "cisco_ios"
    meta = (
        "modes:\n"
        '  user:\n    prompt: "{{ base_prompt }}>"\n'
        '  enable:\n    prompt: "{{ base_prompt }}#"\n'
        '  config:\n    prompt: "{{ base_prompt }}(config)#"\n'
        "initial_mode: user\n"
    )
    if auth is not None:
        meta += f"auth: {auth}\n"
    _write(root / "platform.yaml", meta)
    commands = root / "commands"
    _write(
        commands / "show_version.yaml", "command: show version\ntype: ntc\nmode: [enable]\noutput: show_version.txt\n"
    )
    _write(commands / "show_version.txt", "Cisco IOS Software, Version 15.0\n")
    _write(commands / "enable.yaml", "command: enable\ntype: simnos\nmode: [user]\nnew_mode: enable\n")
    _write(commands / "default.yaml", "command: _default_\ntype: simnos\noutput: default.txt\n")
    _write(commands / "default.txt", "% Invalid input detected\n")
    return root


def _shell_for(nos, *, inventory_config=None):
    return CMDShell(
        nos=nos,
        nos_inventory_config=inventory_config or {},
        base_prompt="R1",
        is_running=threading.Event(),
    )


class TestNosFromPlatformDir:
    def test_loads_resolved_platform(self, tmp_path):
        root = _a3_platform(tmp_path)
        nos = Nos(filename=str(root))
        assert nos.resolved_platform is not None
        assert nos.name == "cisco_ios"
        assert set(nos.resolved_platform.modes) == {"user", "enable", "config"}
        assert nos.resolved_platform.initial_mode == "user"
        assert "show version" in nos.resolved_platform.commands

    def test_legacy_commands_stay_empty(self, tmp_path):
        # The A3 path does not populate the legacy command dict / scalar prompts.
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        assert nos.commands == {}

    def test_auth_is_wired_from_platform_meta(self, tmp_path):
        # `auth` has live SSH behavior, so it must reach nos.auth, not be a dead
        # schema field (#264 / claude #2).
        nos = Nos(filename=str(_a3_platform(tmp_path, auth="none")))
        assert nos.auth == "none"
        assert nos.resolved_platform is not None
        assert nos.resolved_platform.auth == "none"

    def test_auth_defaults_none(self, tmp_path):
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        assert nos.auth is None

    def test_shell_merged_platform_carries_auth(self, tmp_path):
        # The merged ResolvedPlatform the shell builds must mirror the A3 auth,
        # not silently drop it (2nd round codex/claude #3).
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path, auth="none"))))
        assert shell.platform.auth == "none"


class TestShellA3Path:
    def test_modes_and_prompt_from_a3(self, tmp_path):
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path))))
        assert shell.current_mode == "user"
        assert shell.prompt == "R1>"
        assert set(shell.platform.modes) == {"user", "enable", "config"}

    def test_a3_static_command_resolved(self, tmp_path):
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path))))
        cmd = shell.commands["show version"]
        assert cmd.modes == frozenset({"enable"})
        assert cmd.output.render("R1") == "Cisco IOS Software, Version 15.0\n"

    def test_a3_default_overrides_basic_default(self, tmp_path):
        # BASIC contributes a generic _default_; the A3 platform's own _default_
        # sits above it (BASIC < A3) and wins.
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path))))
        assert shell.commands["_default_"].output.render("R1") == "% Invalid input detected\n"

    def test_basic_exit_still_present(self, tmp_path):
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path))))
        assert shell.commands["exit"].exit is True

    def test_py_module_command_overrides_a3_static(self, tmp_path):
        # Simulate a py module loaded after the A3 dir: it fills nos.commands
        # with a dynamic handler that overrides the A3 static `show version`.
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        handler = lambda **kwargs: "dynamic"  # noqa: E731 — minimal handler stand-in
        nos.commands = {"show version": {"output": handler, "help": "dyn", "prompt": "{base_prompt}#"}}
        shell = _shell_for(nos)
        cmd = shell.commands["show version"]
        assert cmd.output.kind == "handler"  # py handler won over the A3 literal
        assert cmd.modes == frozenset({"enable"})  # reverse-mapped via A3 modes

    def test_inventory_command_merges_over_a3(self, tmp_path):
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        inventory = {"commands": {"show inventory": {"output": "INV", "help": "inv", "prompt": "{base_prompt}>"}}}
        shell = _shell_for(nos, inventory_config=inventory)
        assert shell.commands["show inventory"].output.render("R1") == "INV"
        assert shell.commands["show inventory"].modes == frozenset({"user"})

    def test_shell_reuses_shared_platform(self, tmp_path):
        # The server builds the merged platform once (per host) and passes it in;
        # the shell installs that exact object instead of re-normalizing (#264 / Impact).
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        shared = build_resolved_platform(nos, {})
        shell = CMDShell(
            nos=nos,
            nos_inventory_config={},
            base_prompt="R1",
            is_running=threading.Event(),
            resolved_platform=shared,
        )
        assert shell.platform is shared
        assert shell.current_mode == "user"
        assert shell.prompt == "R1>"

    def test_build_shared_platform_none_when_reload_enabled(self, tmp_path, monkeypatch):
        # Dev hot-reload mode: no frozen snapshot, so each connection rebuilds
        # from live nos and file edits propagate to new connections.
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        monkeypatch.setenv("SIMNOS_RELOAD_COMMANDS", "1")
        assert CMDShell.build_shared_platform(nos, {}) is None
        monkeypatch.delenv("SIMNOS_RELOAD_COMMANDS")
        assert CMDShell.build_shared_platform(nos, {}) is not None

    def test_a3_rebuild_is_atomic_on_broken_inflow(self, tmp_path):
        # A broken legacy inflow (canonical-外 prompt the A3 reverse map cannot
        # resolve) must raise without leaving self.* half-updated — same atomic
        # contract the legacy path keeps (#264 / claude #7, D5).
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path))))
        good_commands = shell.commands
        good_prompt = shell.prompt
        shell._inventory_commands = {"bad": {"output": "x", "prompt": "{base_prompt}@@unmappable"}}
        with pytest.raises(ValueError):
            shell._rebuild()
        assert shell.commands is good_commands  # unchanged reference
        assert shell.prompt == good_prompt


class TestOverlayMerge:
    """User overlay layer in `build_resolved_platform` (#286 / Decision 14).

    The overlay slots between the py inflow and inventory: a captured `.txt`
    overrides the packaged A3 output, but a session-local inventory command still
    wins. No render_config / no opt-in leaves the merge unchanged (regression).
    """

    def _overlay(self, tmp_path, files):
        overlay_root = tmp_path / "overlay" / "cisco_ios"
        overlay_root.mkdir(parents=True)
        for name, content in files.items():
            (overlay_root / name).write_text(content, encoding="utf-8")
        return str(overlay_root)

    def test_overlay_overrides_a3_static(self, tmp_path):
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        overlay_root = self._overlay(tmp_path, {"show_version.txt": "OVERLAY version\n"})
        render_config = HostRenderConfig(overlay_root=overlay_root, override_commands="all")
        platform = build_resolved_platform(nos, {}, render_config)
        cmd = platform.commands["show version"]
        assert cmd.output.render("R1") == "OVERLAY version\n"
        assert cmd.modes == frozenset({"enable"})  # base modes inherited (output-only)

    def test_inventory_wins_over_overlay(self, tmp_path):
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        overlay_root = self._overlay(tmp_path, {"show_version.txt": "OVERLAY\n"})
        render_config = HostRenderConfig(overlay_root=overlay_root, override_commands="all")
        inventory = {"show version": {"output": "INVENTORY", "help": "inv", "prompt": "{base_prompt}#"}}
        platform = build_resolved_platform(nos, inventory, render_config)
        assert platform.commands["show version"].output.render("R1") == "INVENTORY"

    def test_overlay_overrides_py_command(self, tmp_path):
        # The py inflow sits below the overlay (a3 < py < overlay < inventory): an
        # overlay output wins over a py-module handler for the same command. Pins
        # the `commands.update` order so a future reorder is caught.
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        handler = lambda **kwargs: "dynamic"  # noqa: E731 — minimal handler stand-in
        nos.commands = {"show version": {"output": handler, "help": "dyn", "prompt": "{base_prompt}#"}}
        overlay_root = self._overlay(tmp_path, {"show_version.txt": "OVERLAY over py\n"})
        render_config = HostRenderConfig(overlay_root=overlay_root, override_commands="all")
        platform = build_resolved_platform(nos, {}, render_config)
        assert platform.commands["show version"].output.render("R1") == "OVERLAY over py\n"

    def test_overlay_adds_new_command(self, tmp_path):
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        overlay_root = self._overlay(tmp_path, {"show_run.txt": "running-config\n"})
        render_config = HostRenderConfig(overlay_root=overlay_root, override_commands=["show run"])
        platform = build_resolved_platform(nos, {}, render_config)
        cmd = platform.commands["show run"]
        assert cmd.type == "custom"
        assert cmd.modes == frozenset()  # all modes
        assert cmd.output.render("R1") == "running-config\n"

    def test_no_render_config_unchanged(self, tmp_path):
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        platform = build_resolved_platform(nos, {}, None)
        assert platform.commands["show version"].output.render("R1") == "Cisco IOS Software, Version 15.0\n"

    def test_overlay_opt_out_when_override_commands_empty(self, tmp_path):
        # overlay_root set but override_commands unset = not opted in (no overlay).
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        overlay_root = self._overlay(tmp_path, {"show_version.txt": "OVERLAY\n"})
        render_config = HostRenderConfig(overlay_root=overlay_root, override_commands=None)
        platform = build_resolved_platform(nos, {}, render_config)
        assert platform.commands["show version"].output.render("R1") == "Cisco IOS Software, Version 15.0\n"

    def test_build_shared_platform_threads_render_config(self, tmp_path):
        # The server-side seam: build_shared_platform passes render_config through
        # so the shared snapshot the server hands to every shell carries the overlay.
        nos = Nos(filename=str(_a3_platform(tmp_path)))
        overlay_root = self._overlay(tmp_path, {"show_version.txt": "OVERLAY version\n"})
        render_config = HostRenderConfig(overlay_root=overlay_root, override_commands="all")
        shared = CMDShell.build_shared_platform(nos, {}, render_config)
        assert shared is not None
        assert shared.commands["show version"].output.render("R1") == "OVERLAY version\n"


def _touch_future(path):
    """Bump a file's mtime past the watcher's snapshot (defeats coarse mtime ties)."""
    future = time.time() + 10
    os.utime(path, (future, future))


def _arista_platform(parent):
    """A second minimal A3 platform (arista_eos) for the multi-host watch tests."""
    root = parent / "arista_eos"
    _write(root / "platform.yaml", 'modes:\n  user:\n    prompt: "{{ base_prompt }}>"\ninitial_mode: user\n')
    _write(
        root / "commands" / "show_version.yaml",
        "command: show version\ntype: ntc\nmode: [user]\noutput: show_version.txt\n",
    )
    _write(root / "commands" / "show_version.txt", "Arista EOS\n")
    return root


def _enable_per_platform_watch(monkeypatch, watch_root, registry):
    """Turn on hot-reload with a tmp-scoped per-platform watch (#281 / D2, D4).

    Sets the env gate and points the two registry lookups `__init__` reads at the
    tmp tree: `nos_plugins` (per-platform source list -> watch roots) and the
    package `__path__` (the rollup `package_root`). Must run BEFORE the shell is
    built, since #281 seeds the watcher baseline at `__init__` (D5).
    """
    monkeypatch.setenv("SIMNOS_RELOAD_COMMANDS", "1")
    monkeypatch.setattr(cmd_shell_module, "nos_plugins", registry)
    monkeypatch.setattr(cmd_shell_module.nos_pkg, "__path__", [str(watch_root)])


class TestA3HotReload:
    """Dev hot-reload over A3 platforms (#274 / #281).

    Covers: an A3 edit / new-file propagating through the real `precmd` watch path
    (per-platform watch, D1/D2), per-shell snapshot isolation across hosts and
    sessions (#281 / D1), the per-host reload lock serializing concurrent reloads
    and the `__init__` self-build read (#281 / D6), the env-off no-walk regression
    (#281 / D2/D5), the post-commit `_rebuild` rollback (D3), and the current-mode
    degrade on a reload that dropped the mode.

    No watcher-reset fixture is needed: the snapshot is per-shell since #281, so a
    tmp-root poll cannot leak into another test.
    """

    def test_a3_edit_propagates_via_precmd(self, tmp_path, monkeypatch):
        """E2E: editing an A3 output file reaches the session through `precmd`.

        The watcher baseline is seeded at `__init__` (env on before construction),
        so the first poll already detects the edit (#281 / D5 — no seed-only poll).
        The watch root is the platform's own subtree via a tmp-scoped registry.
        """
        watch_root = tmp_path / "nos"
        platform_dir = _a3_platform(watch_root / "platforms")
        _enable_per_platform_watch(monkeypatch, watch_root, {"cisco_ios": [str(platform_dir)]})
        shell = _shell_for(Nos(filename=str(platform_dir)))
        target_txt = platform_dir / "commands" / "show_version.txt"
        _write(target_txt, "Cisco IOS Software, Version 16.0\n")
        _touch_future(target_txt)
        shell.precmd("show clock")  # poll: detects the edit against the __init__ baseline, reloads the dir
        assert shell.commands["show version"].output.render("R1") == "Cisco IOS Software, Version 16.0\n"

    def test_a3_new_command_file_appears_via_precmd(self, tmp_path, monkeypatch):
        """E2E: a brand-new command yaml surfaces its command on the next poll.

        Complements the edit test above: this drives the *new-file* detection
        (`get_new_files`, key diff — no mtime involved) through rollup and
        reload, a chain no other test exercises (1st code review claude #3).
        """
        watch_root = tmp_path / "nos"
        platform_dir = _a3_platform(watch_root / "platforms")
        _enable_per_platform_watch(monkeypatch, watch_root, {"cisco_ios": [str(platform_dir)]})
        shell = _shell_for(Nos(filename=str(platform_dir)))
        assert "show clock" not in shell.commands
        _write(
            platform_dir / "commands" / "show_clock.yaml",
            "command: show clock\ntype: simnos\nmode: [user]\noutput: show_clock.txt\n",
        )
        _write(platform_dir / "commands" / "show_clock.txt", "12:00:00 UTC\n")
        shell.precmd("show clock")  # poll: new files detected, dir reloaded
        assert shell.commands["show clock"].output.render("R1") == "12:00:00 UTC\n"

    def test_multi_host_edit_only_reloads_owning_shell(self, tmp_path, monkeypatch):
        """Per-platform watch: an edit is observed by its own shell, not consumed by another (#281 / D1, D2).

        The #281 core fix. Two shells of different platforms share the tree; the
        non-owning shell polls FIRST. With the old process-global consume-once
        snapshot it would consume cisco's edit and the cisco shell would then see
        nothing (cross-host discard). With per-platform watch + per-shell snapshot,
        the arista shell never walks cisco's subtree, so the cisco shell still
        observes the edit on its own poll.
        """
        watch_root = tmp_path / "nos"
        cisco_dir = _a3_platform(watch_root / "platforms")
        arista_dir = _arista_platform(watch_root / "platforms")
        _enable_per_platform_watch(
            monkeypatch, watch_root, {"cisco_ios": [str(cisco_dir)], "arista_eos": [str(arista_dir)]}
        )
        cisco_shell = _shell_for(Nos(filename=str(cisco_dir)))
        arista_shell = _shell_for(Nos(filename=str(arista_dir)))
        cisco_txt = cisco_dir / "commands" / "show_version.txt"
        _write(cisco_txt, "Cisco IOS 99\n")
        _touch_future(cisco_txt)
        arista_shell.precmd("show clock")  # polls first; watches only its own subtree -> does not consume cisco's edit
        assert arista_shell.commands["show version"].output.render("R1") == "Arista EOS\n"
        cisco_shell.precmd("show clock")  # still observes the edit (not discarded by arista)
        assert cisco_shell.commands["show version"].output.render("R1") == "Cisco IOS 99\n"

    def test_multi_session_same_host_both_reload(self, tmp_path, monkeypatch):
        """Two sessions of one host each reflect an edit independently (#281 / D1).

        They share one `Nos` (as in production), but each shell owns its snapshot,
        so the second session is not starved by the first consuming the change —
        the multi-session staleness the old consume-once snapshot caused.
        """
        watch_root = tmp_path / "nos"
        platform_dir = _a3_platform(watch_root / "platforms")
        _enable_per_platform_watch(monkeypatch, watch_root, {"cisco_ios": [str(platform_dir)]})
        nos_obj = Nos(filename=str(platform_dir))
        shell1 = _shell_for(nos_obj)
        shell2 = _shell_for(nos_obj)
        txt = platform_dir / "commands" / "show_version.txt"
        _write(txt, "Shared V2\n")
        _touch_future(txt)
        shell1.precmd("show clock")
        assert shell1.commands["show version"].output.render("R1") == "Shared V2\n"
        shell2.precmd("show clock")  # independent snapshot -> also reflects the edit
        assert shell2.commands["show version"].output.render("R1") == "Shared V2\n"

    def test_concurrent_reload_same_lock_no_corruption(self, tmp_path):
        """Two sessions reloading concurrently under the shared host lock stay consistent (#281 / D6).

        Injects ONE lock into both shells (as `Host.start` does per host) and
        fires `reload_commands` from two threads at a barrier. Per-shell fallback
        locks would not serialize the shared-`nos` mutation, so the explicit
        single lock is what this pins; both shells must end consistent and the
        shared nos uncorrupted.
        """
        platform_dir = _a3_platform(tmp_path)
        nos_obj = Nos(filename=str(platform_dir))
        lock = threading.Lock()
        common = {"nos_inventory_config": {}, "base_prompt": "R1"}
        shell1 = CMDShell(nos=nos_obj, is_running=threading.Event(), reload_lock=lock, **common)
        shell2 = CMDShell(nos=nos_obj, is_running=threading.Event(), reload_lock=lock, **common)
        _write(platform_dir / "commands" / "show_version.txt", "Concurrent\n")
        barrier = threading.Barrier(2)
        errors: list[BaseException] = []

        def _reload(sh):
            barrier.wait()
            try:
                sh.reload_commands([str(platform_dir)])
            except BaseException as exc:  # surface any thread failure to the assert
                errors.append(exc)

        threads = [threading.Thread(target=_reload, args=(sh,)) for sh in (shell1, shell2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert shell1.commands["show version"].output.render("R1") == "Concurrent\n"
        assert shell2.commands["show version"].output.render("R1") == "Concurrent\n"
        assert nos_obj.name == "cisco_ios"  # shared nos not corrupted by the concurrent reloads

    def test_init_self_build_acquires_reload_lock(self, tmp_path):
        """A new connection's self-build runs under the reload lock (#281 / D6, gemini#1).

        When `resolved_platform` is None (hot-reload mode) the `__init__` builds
        from the shared `nos`; that read must hold the per-host lock so a
        concurrent executor reload cannot mutate `nos` mid-read. Holding the lock
        in the main thread must therefore block a shell construction until release.
        """
        platform_dir = _a3_platform(tmp_path)
        nos_obj = Nos(filename=str(platform_dir))
        lock = threading.Lock()
        built: list[CMDShell] = []

        def _build():
            built.append(
                CMDShell(
                    nos=nos_obj,
                    nos_inventory_config={},
                    base_prompt="R1",
                    is_running=threading.Event(),
                    reload_lock=lock,
                )
            )

        with lock:
            t = threading.Thread(target=_build)
            t.start()
            t.join(timeout=0.3)
            blocked = not built  # self-build is waiting on the held lock
        t.join(timeout=2)
        assert blocked
        assert built  # proceeds once the lock is released

    def test_env_off_builds_no_watcher_state(self, tmp_path, monkeypatch):
        """Production (env off): `__init__` builds no watcher state and does no walk (#281 / D2, D5).

        Pins the "本番無変更" core claim and guards against the env-gate / shadowing
        regression (2nd round claude#3): with `SIMNOS_RELOAD_COMMANDS` unset the
        shell holds empty watch roots / snapshot and a None package root.
        """
        monkeypatch.delenv("SIMNOS_RELOAD_COMMANDS", raising=False)
        shell = _shell_for(Nos(filename=str(_a3_platform(tmp_path))))
        assert shell._watch_roots == []
        assert shell._reload_snapshot == {}
        assert shell._package_root is None

    def test_post_commit_rebuild_failure_rolls_back_resolved_platform(self, tmp_path, caplog):
        """A reload that loads but fails `_rebuild` restores `resolved_platform` (D3).

        The broken-yaml case fails *before* `_from_platform_dir` assigns, so it
        cannot pin the D3 attr; this is the post-commit path — the platform
        loses a mode that a legacy inflow's prompt still maps to, so `from_file`
        succeeds and `_rebuild`'s `adapt_commands` raises. Without
        `resolved_platform` in `_NOS_RELOAD_ATTRS` the modeless platform would
        survive the rollback and poison every later rebuild.
        """
        platform_dir = _a3_platform(tmp_path)
        inventory = {"commands": {"conf cmd": {"output": "X", "prompt": "{base_prompt}(config)#"}}}
        nos_obj = Nos(filename=str(platform_dir))
        shell = _shell_for(nos_obj, inventory_config=inventory)
        old_platform = nos_obj.resolved_platform
        old_commands = shell.commands
        # Drop the config mode: load still succeeds (no A3 command references
        # it), but the inventory prompt above no longer reverse-maps.
        _write(
            platform_dir / "platform.yaml",
            'modes:\n  user:\n    prompt: "{{ base_prompt }}>"\n'
            '  enable:\n    prompt: "{{ base_prompt }}#"\n'
            "initial_mode: user\n",
        )
        with caplog.at_level("ERROR", logger="simnos.plugins.shell.cmd_shell"):
            shell.reload_commands([str(platform_dir)])
        assert len(caplog.records) == 1
        assert nos_obj.resolved_platform is old_platform  # rolled back, not the modeless parse
        assert shell.commands is old_commands  # live session untouched

    def test_removed_mode_degrades_to_initial(self, tmp_path):
        """A reload that drops the current mode resets the session to initial_mode."""
        platform_dir = _a3_platform(tmp_path)
        shell = _shell_for(Nos(filename=str(platform_dir)))
        shell._dispatch_general("enable")
        assert shell.current_mode == "enable"
        # Rewrite the platform as user-only (and retarget/remove the commands
        # that referenced the enable mode, so the reload itself succeeds).
        _write(
            platform_dir / "platform.yaml",
            'modes:\n  user:\n    prompt: "{{ base_prompt }}>"\ninitial_mode: user\n',
        )
        (platform_dir / "commands" / "enable.yaml").unlink()
        _write(
            platform_dir / "commands" / "show_version.yaml",
            "command: show version\ntype: ntc\nmode: [user]\noutput: show_version.txt\n",
        )
        shell.reload_commands([str(platform_dir)])
        assert shell.current_mode == "user"
        assert shell.prompt == "R1>"
