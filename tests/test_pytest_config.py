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
