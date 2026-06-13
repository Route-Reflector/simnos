In order to make it easier the development, several small tasks have been develop. Please
feel free to add more. All those tasks can be found in the `tasks.py`. In order to run them,
you can use the following command:
```bash
invoke <task_name>
```

The available tasks are:

-  `gen-docs-platform-commands`: Generate automatically the documentation for a platform. It was originally intended to document all the commands in the first version of the project, but it can be used to document any platform. It also regenerates the Platforms section of the `mkdocs.yml` nav from the platform list, so a new platform never ships with an unreachable docs page.

-  `netmiko-check`: Netmiko is a core library in Network Automation. SIMNOS intends to be a testing library for it, and as such, it is important to ensure that the available platforms are compatible with Netmiko. This task generates a script that can be used to test the compatibility of a platform with Netmiko. If it goes well, it will say `Everything is OK! ✅`.

-  `lint-platform-data`: Check the A3 platform data directories against the authoring conventions (#264): output files (`.txt` / `.j2`) must be UTF-8, LF-only, and end with a trailing newline; each output file is referenced by exactly one command yaml (no orphan / shared / missing references); literal channels use `.txt` and `output_template` uses `.j2`; a stray `.yml` command file is flagged. It also enforces the authoring ratchet (#276): every new platform defines a `_default_` command, no new auto-generated stub help, no heritage wording. Existing drift is frozen in `platform_data_lint_baseline.yaml` (repo root), which only ever shrinks — fixing a violation requires removing its baseline entry in the same PR. It also prints non-blocking warnings (a filename not matching the sanitized command name, a `type: ntc` command missing its `source` block). Runs in CI and as a pre-commit hook.
