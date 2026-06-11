"""Shared, JSON-friendly projection for the A3 migration oracle (#264 / Decision 3).

Both the conversion script (``migrate_platform_yaml.py``, which freezes the
legacy adapter projection into ``tests/assets/oracle/<platform>.json``) and the
committed oracle (b) test (``test_migration_oracle_a3.py``, which compares the
A3 loader projection against that snapshot) project ``ResolvedCommand`` objects
through this one function, so the snapshot and the test can never drift apart.

The projection captures the client-observable behavior: rendered output as
``splitlines()`` (wire-equivalent — ``writeline`` absorbs trailing newlines),
the modes a command is visible in, the transition target, and exit / help /
variant count. ``_default_`` is the mode-agnostic fallback, so its mode
visibility / transition are excluded (Decision 3 / D5).
"""

from simnos.core.resolved_command import ResolvedCommand, ResolvedOutput

# Fixed device prompt for the projection (any value with distinct canonical
# renders works — Decision 3 "固定 base_prompt").
FIXED_BASE_PROMPT = "oracle"
# Sentinels kept out of the str/list value space so they compare by identity.
HANDLER = "<<handler>>"
ALL_MODES = "<<all-modes>>"


def _project_output(out: ResolvedOutput):
    if out.kind == "handler":
        return HANDLER
    if out.kind == "none":
        return None
    body = out.render(FIXED_BASE_PROMPT)
    return body.splitlines() if body is not None else None


def project_resolved(commands: dict[str, ResolvedCommand]) -> dict[str, dict]:
    """Project resolved commands into a JSON-serializable comparison shape."""
    projection: dict[str, dict] = {}
    for name, rc in commands.items():
        is_default = name == "_default_"
        projection[name] = {
            "output": _project_output(rc.output),
            "modes": None if is_default else (ALL_MODES if not rc.modes else sorted(rc.modes)),
            "new_mode": rc.new_mode,
            "exit": rc.exit,
            "help": rc.help,
            "variant_count": len(rc.variants),
        }
    return projection
