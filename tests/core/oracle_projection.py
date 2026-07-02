"""Shared, JSON-friendly projection for the A3 migration oracle (#264 / Decision 3).

Both the snapshot re-baseliner (``regen_oracle_snapshots.py``, which freezes the
A3 loader projection into ``tests/assets/oracle/<platform>.json``) and the
committed oracle (b) test (``test_migration_oracle_a3.py``, which compares the
A3 loader projection against that snapshot) project ``ResolvedCommand`` objects
through this one function, so the snapshot and the test can never drift apart.
(The original snapshots were frozen from the legacy adapter by the one-shot
``migrate_platform_yaml.py``, removed once every platform was migrated — git
history + design D7 hold the conversion record.)

The merged-view oracle (#317 P-2: ``regen_merged_oracle_snapshots.py`` +
``test_merged_oracle.py``) projects through the same function, so a handler
projects to its *name* (bound ``__qualname__``, or the unbound A3
``handler_ref``) rather than an anonymous sentinel — handler identity is part
of the migration contract. ``transitions`` (#317 P-1) is emitted only when the
command authored one, so the pre-#317 snapshots stay byte-stable.

The projection captures the client-observable behavior: rendered output as
``splitlines()`` (wire-equivalent — the driver's ``_render_response`` joins each
body line with ``newline``, absorbing trailing newlines),
the modes a command is visible in, the transition target(s), exit / help,
``disables_paging`` (True-only emit — the #320 bug class was this flag being
shadowed out of the merged view), and the
full multi-capture variant list (each variant's name + rendered body, not just
the count — so a variant-body conversion error is caught, not only a missing
variant; PR-3 oracle hardening). For ``_default_`` (the mode-agnostic fallback)
the ``modes`` axis is excluded (set to None); its ``new_mode`` stays in the
projection but is always None, since the fallback never transitions
(Decision 3 / D5).
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
        # Handler identity: the bound callable's qualname (merged view) or the
        # A3 `handler_ref` (loader view, unbound). The same function reached
        # through either path projects to a comparable name — the merged
        # oracle relies on this to pin "the migration kept the same handler"
        # (#317 P-2). The bare sentinel survives only for a nameless legacy
        # handler (no shipped case).
        # `getattr` keeps the type checker happy (the `CommandHandler` Protocol
        # declares no `__qualname__`) and degrades to the ref for an exotic
        # callable object without one.
        name = getattr(out.handler, "__qualname__", None) or out.handler_ref
        return f"<<handler:{name}>>" if name else HANDLER
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
            "variants": [[vname, _project_output(vout)] for vname, vout in rc.variants],
        }
        if rc.transitions is not None:
            # Mode-conditional transition map (#317 P-1). Emitted only when
            # authored, so the many pre-#317 snapshots need no re-baseline.
            projection[name]["transitions"] = {
                mode: {"new_mode": t.new_mode, "exit": t.exit} for mode, t in sorted(rc.transitions.items())
            }
        if rc.disables_paging:
            # The #320 bug class was exactly this flag being shadowed out of the
            # merged view, so the oracle must see it (1st round claude#2).
            # True-only emit, same rationale as `transitions` above.
            projection[name]["disables_paging"] = True
    return projection
