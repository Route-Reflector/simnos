"""CLI entry-point tests for the #267 subcommand refresh.

Covers `simnos.plugins.utils.cli`: import side-effect safety (no module-level
`parse_args`/`basicConfig`), the `build_parser` contract (subcommand required,
`-i`/`-d`/`--sys-config` non-empty + `-i`/`-d` mutex, `-l` placement +
normalization), the ad-hoc
inventory builder (default/explicit/zero port, host-name + credential folding),
the `_cmd_up` dispatch + reload-env lifecycle across every raise path, and
`list-platforms` output. `_cmd_up`'s blocking `while True: time.sleep` loop is
broken by patching `cli.time.sleep` to raise `KeyboardInterrupt` (the same
signal a real Ctrl-C delivers), so the "normal" path is exercised without a
real server. The empty-`SIMNOS_SYS_CONFIG` loud-fail lives with the other
sys_config tests in `tests/core/test_simnos.py::TestSysConfig` (core locality).
"""

import importlib
import logging
import os
import sys

import pytest

from simnos.core.simnos import DEFAULT_PORT_START
from simnos.plugins.nos import available_platforms
from simnos.plugins.utils import cli


class TestImportSafety:
    """Importing the module must not read sys.argv or configure logging (#267 / D3)."""

    def test_reimport_with_bogus_argv_does_not_exit(self, monkeypatch):
        # The old module ran `parse_args()` at import time, so a bogus argv
        # raised SystemExit on import. Reloading must now be inert.
        monkeypatch.setattr(sys, "argv", ["pytest", "--not-a-simnos-flag", "garbage"])
        importlib.reload(cli)  # must not raise SystemExit

    def test_reimport_does_not_call_basicconfig(self, monkeypatch):
        calls = []
        monkeypatch.setattr(logging, "basicConfig", lambda *a, **k: calls.append((a, k)))
        monkeypatch.setattr(sys, "argv", ["pytest"])
        importlib.reload(cli)
        assert calls == []


class TestBuildParser:
    """`build_parser` is pure construction; parse-time contracts (#267 / D2)."""

    def test_subcommand_required(self):
        with pytest.raises(SystemExit) as exc:
            cli.build_parser().parse_args([])
        assert exc.value.code == 2

    def test_inventory_and_device_type_are_mutually_exclusive(self):
        with pytest.raises(SystemExit) as exc:
            cli.build_parser().parse_args(["up", "-i", "inv.yaml", "-d", "cisco_ios"])
        assert exc.value.code == 2

    @pytest.mark.parametrize("flag", ["-i", "-d"])
    @pytest.mark.parametrize("value", ["", "   "])
    def test_empty_source_flags_rejected_at_parse(self, flag, value):
        # `-d ""` / `-i ""` must die at the CLI boundary (exit 2), never reach the
        # facade where truthiness would silently mis-launch (#267 / D2).
        with pytest.raises(SystemExit) as exc:
            cli.build_parser().parse_args(["up", flag, value])
        assert exc.value.code == 2

    def test_neither_source_is_valid(self):
        args = cli.build_parser().parse_args(["up"])
        assert args.inventory is None
        assert args.device_type is None

    def test_device_type_underscore_alias(self):
        args = cli.build_parser().parse_args(["up", "--device_type", "cisco_ios"])
        assert args.device_type == "cisco_ios"

    def test_log_level_after_subcommand(self):
        args = cli.build_parser().parse_args(["up", "-l", "DEBUG"])
        assert args.log_level == "DEBUG"

    def test_log_level_lowercase_normalized(self):
        args = cli.build_parser().parse_args(["up", "-l", "debug"])
        assert args.log_level == "DEBUG"

    def test_log_level_invalid_rejected(self):
        with pytest.raises(SystemExit) as exc:
            cli.build_parser().parse_args(["up", "-l", "invalid"])
        assert exc.value.code == 2

    def test_log_level_prefix_position_rejected(self):
        # Parent-parser inheritance is after-subcommand only; prefix is exit 2.
        with pytest.raises(SystemExit) as exc:
            cli.build_parser().parse_args(["-l", "DEBUG", "up"])
        assert exc.value.code == 2

    def test_list_platforms_accepts_log_level(self):
        args = cli.build_parser().parse_args(["list-platforms", "-l", "WARNING"])
        assert args.log_level == "WARNING"


class TestBuildAdhocInventory:
    """`_build_adhoc_inventory` produces a minimal NEW single-host dict (#267 / D2)."""

    def _args(self, argv):
        return cli.build_parser().parse_args(argv)

    def test_default_port_when_omitted(self):
        inv = cli._build_adhoc_inventory(self._args(["up", "-d", "cisco_ios"]))
        assert inv == {"hosts": {"cisco_ios": {"device_type": "cisco_ios", "port": DEFAULT_PORT_START}}}

    def test_explicit_port_used(self):
        inv = cli._build_adhoc_inventory(self._args(["up", "-d", "cisco_ios", "-p", "7000"]))
        assert inv["hosts"]["cisco_ios"]["port"] == 7000

    def test_port_zero_not_coerced_to_default(self):
        # `0` must survive as-is so `_allocate_port_single` rejects it loudly,
        # rather than `0 or DEFAULT` silently becoming 6000 (#267 / D2).
        inv = cli._build_adhoc_inventory(self._args(["up", "-d", "cisco_ios", "-p", "0"]))
        assert inv["hosts"]["cisco_ios"]["port"] == 0

    def test_host_name_overrides_key(self):
        inv = cli._build_adhoc_inventory(self._args(["up", "-d", "cisco_ios", "-n", "R1"]))
        assert set(inv["hosts"]) == {"R1"}
        assert inv["hosts"]["R1"]["device_type"] == "cisco_ios"

    def test_credentials_folded_only_when_given(self):
        bare = cli._build_adhoc_inventory(self._args(["up", "-d", "cisco_ios"]))
        assert "username" not in bare["hosts"]["cisco_ios"]
        assert "password" not in bare["hosts"]["cisco_ios"]
        full = cli._build_adhoc_inventory(self._args(["up", "-d", "cisco_ios", "-u", "alice", "-w", "secret"]))
        assert full["hosts"]["cisco_ios"]["username"] == "alice"
        assert full["hosts"]["cisco_ios"]["password"] == "secret"


class _FakeNet:
    """Stand-in for SimNOS that records lifecycle calls without a real server."""

    def __init__(self, *, start_exc=None, stop_exc=None):
        self._start_exc = start_exc
        self._stop_exc = stop_exc
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True
        if self._start_exc is not None:
            raise self._start_exc

    def stop(self):
        self.stopped = True
        if self._stop_exc is not None:
            raise self._stop_exc


@pytest.fixture
def _no_sleep(monkeypatch):
    """Break `_cmd_up`'s `while True` loop the way a real Ctrl-C would."""

    def _raise(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli.time, "sleep", _raise)


def _patch_simnos(monkeypatch, *, net=None, ctor_exc=None):
    """Patch `cli.SimNOS` with a recording factory; return its captured kwargs."""
    captured = {}

    def _factory(*, inventory, sys_config):
        captured["inventory"] = inventory
        captured["sys_config"] = sys_config
        if ctor_exc is not None:
            raise ctor_exc
        return net

    monkeypatch.setattr(cli, "SimNOS", _factory)
    return captured


class TestCmdUpDispatch:
    """`_cmd_up` selects the inventory source and warns on stray ad-hoc flags."""

    def _run(self, monkeypatch, argv):
        net = _FakeNet()
        captured = _patch_simnos(monkeypatch, net=net)
        rc = cli._cmd_up(cli.build_parser().parse_args(argv))
        return rc, net, captured

    def test_neither_passes_none_inventory(self, monkeypatch, _no_sleep):
        rc, net, captured = self._run(monkeypatch, ["up"])
        assert rc == 0
        assert captured["inventory"] is None
        assert net.started and net.stopped

    def test_inventory_path_passed_through(self, monkeypatch, _no_sleep):
        _, _, captured = self._run(monkeypatch, ["up", "-i", "inv.yaml"])
        assert captured["inventory"] == "inv.yaml"

    def test_device_type_builds_dict(self, monkeypatch, _no_sleep):
        _, _, captured = self._run(monkeypatch, ["up", "-d", "cisco_ios", "-p", "6500"])
        assert captured["inventory"] == {"hosts": {"cisco_ios": {"device_type": "cisco_ios", "port": 6500}}}

    def test_sys_config_threaded(self, monkeypatch, _no_sleep):
        # SimNOS is mocked, so the path is only threaded, never opened.
        _, _, captured = self._run(monkeypatch, ["up", "--sys-config", "etc/sc.yaml"])
        assert captured["sys_config"] == "etc/sc.yaml"

    def test_stray_flag_warns_with_inventory(self, monkeypatch, caplog, _no_sleep):
        with caplog.at_level(logging.WARNING):
            self._run(monkeypatch, ["up", "-i", "inv.yaml", "-p", "7000"])
        assert "--port" in caplog.text
        assert "with -i/--inventory" in caplog.text

    def test_stray_flag_warns_without_source(self, monkeypatch, caplog, _no_sleep):
        with caplog.at_level(logging.WARNING):
            self._run(monkeypatch, ["up", "-u", "bob"])
        assert "--username" in caplog.text
        assert "default inventory" in caplog.text

    def test_no_stray_warning_in_adhoc_mode(self, monkeypatch, caplog, _no_sleep):
        with caplog.at_level(logging.WARNING):
            self._run(monkeypatch, ["up", "-d", "cisco_ios", "-p", "7000"])
        assert "ignored" not in caplog.text


class TestCmdUpReloadLifecycle:
    """The reload-env is restored across every raise path (#267 / Risks)."""

    _ENV = "SIMNOS_RELOAD_COMMANDS"

    def test_reload_set_and_restored_to_absent(self, monkeypatch, _no_sleep):
        monkeypatch.delenv(self._ENV, raising=False)
        net = _FakeNet()
        _patch_simnos(monkeypatch, net=net)
        cli._cmd_up(cli.build_parser().parse_args(["up", "-r"]))
        assert net.stopped
        assert self._ENV not in os.environ

    def test_reload_restores_prior_value(self, monkeypatch, _no_sleep):
        monkeypatch.setenv(self._ENV, "OFF")
        _patch_simnos(monkeypatch, net=_FakeNet())
        cli._cmd_up(cli.build_parser().parse_args(["up", "-r"]))
        assert os.environ[self._ENV] == "OFF"

    def test_constructor_failure_skips_stop_and_restores_env(self, monkeypatch, _no_sleep):
        monkeypatch.delenv(self._ENV, raising=False)
        _patch_simnos(monkeypatch, ctor_exc=RuntimeError("bad device_type"))
        with pytest.raises(RuntimeError, match="bad device_type"):
            cli._cmd_up(cli.build_parser().parse_args(["up", "-r", "-d", "cisco_ios"]))
        assert self._ENV not in os.environ  # restored despite no net to stop

    def test_start_failure_calls_stop_and_restores_env(self, monkeypatch, _no_sleep):
        # The CLI-level contract: a start() failure still reaches net.stop() in
        # the finally (whether stop() can tear down a partially-started host is a
        # separate core concern, not pinned here — codex#2 1st).
        monkeypatch.delenv(self._ENV, raising=False)
        net = _FakeNet(start_exc=RuntimeError("bind failed"))
        _patch_simnos(monkeypatch, net=net)
        with pytest.raises(RuntimeError, match="bind failed"):
            cli._cmd_up(cli.build_parser().parse_args(["up", "-r"]))
        assert net.stopped  # stop() attempted on start failure
        assert self._ENV not in os.environ

    def test_stop_failure_still_restores_env(self, monkeypatch, _no_sleep):
        monkeypatch.delenv(self._ENV, raising=False)
        net = _FakeNet(stop_exc=RuntimeError("stop boom"))
        _patch_simnos(monkeypatch, net=net)
        with pytest.raises(RuntimeError, match="stop boom"):
            cli._cmd_up(cli.build_parser().parse_args(["up", "-r"]))
        assert self._ENV not in os.environ  # inner finally restores even if stop raises


class TestAdhocLoudValidation:
    """The minimal ad-hoc dict still hits the facade's loud guards (#267 / Risks)."""

    def test_port_zero_rejected_at_real_construction(self):
        # `--port 0` survives the builder (not coerced to 6000), then the
        # inventory model's Port field (ge=1) rejects it during real SimNOS
        # construction — the loud seam is pydantic, not _allocate_port_single,
        # but the "never silently default" contract holds (codex#1 1st).
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            cli._cmd_up(cli.build_parser().parse_args(["up", "-d", "cisco_ios", "-p", "0"]))

    def test_sys_config_empty_rejected_at_parse(self):
        with pytest.raises(SystemExit) as exc:
            cli.build_parser().parse_args(["up", "--sys-config", ""])
        assert exc.value.code == 2


class TestListPlatforms:
    def test_lists_every_supported_platform(self, capsys):
        rc = cli._cmd_list_platforms(cli.build_parser().parse_args(["list-platforms"]))
        out = capsys.readouterr().out
        assert rc == 0
        assert f"Supported platforms ({len(available_platforms)})" in out
        for name in available_platforms:
            assert name in out


class TestMain:
    def test_force_basicconfig_applies_each_call(self, monkeypatch):
        # force=True so a second main() in the same process re-applies the level
        # (import-safe entry must be re-callable from tests, #267 / Risks).
        monkeypatch.setattr(cli, "_cmd_list_platforms", lambda args: 0)
        cli.main(["list-platforms", "-l", "WARNING"])
        assert logging.getLogger().level == logging.WARNING
        cli.main(["list-platforms", "-l", "DEBUG"])
        assert logging.getLogger().level == logging.DEBUG

    def test_list_platforms_returns_zero(self, capsys):
        assert cli.main(["list-platforms"]) == 0
        assert capsys.readouterr().out  # printed something

    def test_no_subcommand_exits_2(self):
        with pytest.raises(SystemExit) as exc:
            cli.main([])
        assert exc.value.code == 2


class TestRunCli:
    """The pyproject entry point wraps main()'s return code in SystemExit (codex#4 1st)."""

    def test_run_cli_propagates_main_return_code(self, monkeypatch):
        monkeypatch.setattr(cli, "main", lambda: 0)
        with pytest.raises(SystemExit) as exc:
            cli.run_cli()
        assert exc.value.code == 0
