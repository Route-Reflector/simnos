"""Wire parity pins for the #317 P-2 py->A3 migration.

P-2 moved the three shipped py ``commands`` dicts (cisco_ios / arista_eos /
huawei_smartax) into their A3 platform dirs. Two conversion classes need a
byte-level pin that the merged oracle snapshot (frozen *after* the migration)
cannot supply on its own:

- **handler -> static output**: the py handlers that only rendered a fixed
  template became A3 ``output`` / ``output_template`` files. The expected
  fixtures under ``tests/assets/p2_migration_wire/`` were frozen from the
  *pre-migration* merged view (the py handler renders), so these tests prove
  the A3 files reproduce the old wire byte-for-byte (design #317 P-2
  "byte 照合"). Comparison is on ``splitlines()`` — the driver's
  ``_render_response`` emits each body line with the session newline, so a
  single trailing-``\\n`` difference (the A3 file-encoding convention) is
  wire-neutral.
- **handler -> static transition**: the four dict-returning transition handlers
  (arista ``exit``, huawei ``return`` / ``disable`` / ``quit``) became static
  ``transitions`` / ``new_mode`` / ``exit`` data. Each pin below mirrors one
  branch of the deleted handler (see the pre-P-2
  ``tests/plugins/nos/test_arista_eos.py::TestMakeExit`` /
  ``test_huawei_smartax.py::TestModeCallables``).

These pins may be dropped when P-4 removes the legacy inflow (the merged
oracle then owns the surface); until then they are the migration's direct
byte evidence. TODO(#317 P-4): when dropping, decide the fate of the arista
``show_ip_int_brief.txt`` / ``show_ip_interface_brief.txt`` byte-identity
guarantee currently riding on these fixtures — keep a small permanent identity
test or accept comment-only sync (see the cross-sync notes in both yamls).
"""

import functools
import os

import pytest

from a3_paths import sanitize_command_stem
from simnos.core.nos import Nos
from simnos.core.resolved_command import ResolvedPlatform, Transition
from simnos.plugins.nos import nos_plugins
from simnos.plugins.shell.cmd_shell import build_resolved_platform

FIXTURE_DIR = os.path.join("tests", "assets", "p2_migration_wire")


@functools.cache
def _merged(platform: str) -> ResolvedPlatform:
    """The served merged view (Host.start wiring), one build per platform."""
    return build_resolved_platform(Nos(filename=nos_plugins[platform]), {})


class TestStaticOutputParity:
    """A3 outputs reproduce the pre-migration py handler renders byte-for-byte."""

    @pytest.mark.parametrize(
        ("platform", "command"),
        [
            ("cisco_ios", "show version"),
            ("cisco_ios", "show running-config"),
            ("arista_eos", "show version"),
            ("arista_eos", "show running-config"),
            ("arista_eos", "show ip int brief"),
            ("arista_eos", "show ip interface brief"),
            # Not a handler conversion, but the raw-capture A3 `.txt` was
            # replaced by the py literal (the served wire — the old capture was
            # shadow-dead), so it gets the same fixture pin.
            ("arista_eos", "show hostname"),
        ],
    )
    def test_output_matches_frozen_pre_migration_wire(self, platform, command):
        fixture = os.path.join(FIXTURE_DIR, f"{platform}__{sanitize_command_stem(command)}.expected.txt")
        with open(fixture, encoding="utf-8") as fh:
            expected = fh.read()
        rendered = _merged(platform).commands[command].output.render("R1")
        assert rendered is not None
        assert rendered.splitlines() == expected.splitlines()


class TestStaticTransitionParity:
    """The static transition data mirrors the deleted per-mode handler branches."""

    def test_arista_exit_transitions(self):
        """make_exit: user/enable closed the session, config dropped to enable."""
        rc = _merged("arista_eos").commands["exit"]
        assert rc.modes == frozenset({"user", "enable", "config"})
        assert rc.transitions == {
            "user": Transition(exit=True),
            "enable": Transition(exit=True),
            "config": Transition(new_mode="enable"),
        }
        # The config branch answered `{"output": ""}` — an empty literal body.
        assert rc.output.render("R1") == ""

    def test_huawei_return_is_static_noop_to_enable(self):
        """_return: only reachable from enable, where it answered new_mode=enable."""
        rc = _merged("huawei_smartax").commands["return"]
        assert rc.modes == frozenset({"enable"})
        assert rc.new_mode == "enable"
        assert rc.output.render("R1") == ""

    def test_huawei_disable_drops_to_user(self):
        """disable: enable -> user; in user the static target is a no-op transition."""
        rc = _merged("huawei_smartax").commands["disable"]
        assert rc.modes == frozenset({"user", "enable"})
        assert rc.new_mode == "user"
        assert rc.output.render("R1") == ""

    def test_huawei_quit_exits(self):
        rc = _merged("huawei_smartax").commands["quit"]
        assert rc.modes == frozenset({"user", "enable"})
        assert rc.exit is True

    def test_remaining_handlers_stay_dynamic(self):
        """The genuinely dynamic commands still dispatch through a bound handler."""
        for platform, command, qualname in (
            ("cisco_ios", "show clock", "CiscoIOS.make_show_clock"),
            ("arista_eos", "show clock", "AristaEOS.make_show_clock"),
            ("huawei_smartax", "display board", "HuaweiSmartAX.make_display_board"),
        ):
            out = _merged(platform).commands[command].output
            assert out.kind == "handler"
            assert out.handler is not None and getattr(out.handler, "__qualname__", None) == qualname
