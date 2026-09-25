"""Real-device rules that every shipped A3 platform must satisfy.

Each check here pins a behavior a downstream client relies on without entering
privileged mode first, so a platform that drifts from it breaks the client on
the first command rather than in a platform-specific test.
"""

import os

import pytest

from a3_paths import PLATFORMS_DIR as A3_ROOT
from a3_paths import list_a3_platform_names
from simnos.core.platform_loader import load_platform_dir


@pytest.mark.parametrize("platform", list_a3_platform_names(A3_ROOT))
def test_show_version_runs_in_user_mode(platform):
    """`show version` is available in user EXEC wherever a user mode exists.

    Real devices answer `show version` without `enable`, and netmiko drivers
    that do not auto-enable (e.g. arista_eos) send it from the `>` prompt, so an
    enable-only definition returns the platform's unknown-command error there.
    """
    resolved = load_platform_dir(os.path.join(A3_ROOT, platform))
    command = resolved.commands.get("show version")
    if command is None or "user" not in resolved.modes:
        pytest.skip(f"{platform}: no `show version` or no user mode")
    assert not command.modes or "user" in command.modes, (
        f"{platform}: `show version` is limited to {sorted(command.modes)} — add `user` to its `mode:`"
    )
