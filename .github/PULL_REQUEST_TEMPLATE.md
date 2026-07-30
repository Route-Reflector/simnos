<!-- Thank you for contributing! Please explain *why*, not just *what* —
     PRs without context are hard to review (see CONTRIBUTING.md). -->

## Summary

<!-- What does this PR do, and why? -->

## Related issue

<!-- Larger changes should be discussed in an issue first (CONTRIBUTING.md).
     Small fixes (typos, minor bugs) may open an issue and PR together. -->

Closes #

## Changes

-

## Testing

<!-- How did you verify this? e.g. `pytest -n auto`, `invoke ruff`,
     `invoke yamllint`, `invoke lint-platform-data`, a manual SSH session. -->

## AI disclosure

<!-- Per CONTRIBUTING.md "AI Transparency": if AI tools were used, name them and
     confirm you reviewed the output yourself. Write "None" if no AI was used. -->

## Checklist

- [ ] Tests pass locally (`pytest -n auto`)
- [ ] Lint passes (`invoke ruff` / `invoke yamllint`; for platform data also `invoke lint-platform-data`)
- [ ] The byte-parity goldens are untouched (re-recording them requires maintainer approval)
- [ ] Docs updated where behaviour changed (for platform data: `invoke gen-docs-platform-commands`)
