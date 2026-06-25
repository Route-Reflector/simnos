"""Line sanitisation for shell output on its way to the network client.

``process_tap_line`` is the per-write normalisation the push-session wire
assembly applies (see :mod:`simnos.plugins.servers.tap_bridge`). The blocking
``TapIO`` stream that backed the old ``cmd.Cmd.cmdloop`` tap pair was retired
with the paramiko server in #297 Stage 4.
"""


def process_tap_line(line: str) -> str:
    """Sanitise a single line from shell stdout for the network client.

    - Strips NUL bytes.
    - Converts bare ``\\n`` to ``\\r\\n`` (leaves existing ``\\r\\n`` intact).
    """
    if "\x00" in line:
        line = line.replace("\x00", "")
    if "\r\n" not in line and "\n" in line:
        line = line.replace("\n", "\r\n")
    return line
