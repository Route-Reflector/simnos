"""
Pins for the pytest suite configuration itself (pyproject.toml
``[tool.pytest.ini_options]``) — guards safety-net settings that no
functional test would catch if they were silently removed.
"""


def test_global_timeout_configured(request):
    """The suite-wide hang safety net stays armed (#233).

    A hung loop/SSH test must fail in minutes instead of sitting silent
    until the CI job timeout. Per-test `@pytest.mark.timeout(...)` marks
    may override the default, but the global default itself must not
    silently disappear from pyproject.toml.
    """
    assert float(request.config.getini("timeout")) == 300.0


def test_timeout_method_left_to_auto(request):
    """`timeout_method` stays unset on purpose (#233).

    Pinning a method would break portability: POSIX uses `signal` (the
    worker survives the failure) while Windows — covered by the weekly
    full-matrix — has no SIGALRM and needs the `thread` fallback. An
    explicit method appearing in pyproject.toml should be a conscious,
    reviewed decision, not a drive-by edit.
    """
    assert not request.config.getini("timeout_method")
