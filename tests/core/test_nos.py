"""
Test module for simnos.core.nos module.
This module can be found at simnos/core/nos.py
"""

import copy
import logging

from pydantic import ValidationError
import pytest
import yaml

from simnos.core.nos import Nos
from simnos.plugins.nos import nos_plugins
from tests.assets import module

_NOS_LOGGER = "simnos.core.nos"


def _normalized_commands(commands: dict) -> dict:
    """Expected runtime form of authored commands (#244 / D3).

    Every load path normalizes `prompt` str -> [str] on a deepcopied
    candidate, so equality assertions against authored dicts compare
    through this helper.
    """
    return Nos.normalize_command_prompts(copy.deepcopy(commands))


def _write_tmp_file(tmp_path, name: str, content: str) -> str:
    """Write a throwaway plugin file under ``tmp_path`` and return its path.

    ``tmp_path`` is pytest's per-test temp dir, so cleanup is automatic.
    """
    tmp_file = tmp_path / name
    tmp_file.write_text(content, encoding="utf-8")
    return str(tmp_file)


def _assert_module_static_commands_loaded(nos: Nos) -> None:
    """The test module's non-callable-output commands landed in ``nos``, normalized.

    Callable outputs are excluded from both sides (functions don't compare by
    value); the remaining static commands must match exactly (a dict `==` gives
    a readable diff and also catches stray/extra commands).
    """
    expected = _normalized_commands(module.commands)
    expected_static = {name: cmd for name, cmd in expected.items() if not callable(cmd["output"])}
    actual_static = {name: cmd for name, cmd in nos.commands.items() if not callable(cmd["output"])}
    assert actual_static == expected_static


def _nos_log_messages(caplog, level: int) -> list[str]:
    """Messages logged to the nos logger at ``level`` or above.

    Filtering by logger name + level keeps the assertLogs-style scope (the old
    `assertLogs(_NOS_LOGGER, level=...)` only saw that logger's records).
    """
    return [r.getMessage() for r in caplog.records if r.name == _NOS_LOGGER and r.levelno >= level]


@pytest.fixture(scope="module")
def commands() -> dict:
    """Authored commands loaded once from the shared yaml fixture.

    Read-only across tests: `Nos` normalizes on a deepcopied candidate, so
    callers never mutate this shared dict.
    """
    with open("tests/assets/yaml_nos.yaml", encoding="utf-8") as yml_file:
        return yaml.safe_load(yml_file)["commands"]


def test_init_without_arguments():
    """
    Test that the init method works when no arguments are provided.
    """
    nos = Nos()
    assert nos.name == "SimNOS"
    assert nos.initial_prompt == "SimNOS>"
    assert nos.commands == {}


def test_init_with_arguments(commands):
    """
    Test that the init method works when arguments are provided.
    """
    nos = Nos(name="MySimNOS", initial_prompt="MySimNOS>", commands=commands)
    assert nos.name == "MySimNOS"
    assert nos.initial_prompt == "MySimNOS>"
    assert nos.commands == _normalized_commands(commands)


def test_init_with_argument_name():
    """
    Test that the init method works when the name argument is provided.
    """
    nos = Nos(name="MySimNOS")
    assert nos.name == "MySimNOS"
    assert nos.initial_prompt == "SimNOS>"
    assert nos.commands == {}


def test_init_with_argument_initial_prompt():
    """
    Test that the init method works when
    the initial_prompt argument is provided.
    """
    nos = Nos(initial_prompt="MySimNOS>")
    assert nos.name == "SimNOS"
    assert nos.initial_prompt == "MySimNOS>"
    assert nos.commands == {}


def test_init_with_argument_commands(commands):
    """
    Test that the init method works when the commands argument is provided.
    """
    nos = Nos(commands=commands)
    assert nos.name == "SimNOS"
    assert nos.initial_prompt == "SimNOS>"
    assert nos.commands == _normalized_commands(commands)


def test_validate():
    """
    Test that the validate raises a ValidationError
    when the NOS attributes are invalid.
    """
    with pytest.raises(ValidationError, match=r"commands"):
        nos = Nos(commands="invalid_commands")
        nos.validate()


def test_from_dict_correct(commands):
    """
    Test that the from_dict method works when the data is correct.
    """
    nos = Nos()
    nos.from_dict(
        {
            "name": "MySimNOS",
            "initial_prompt": "MySimNOS>",
            "commands": commands,
        }
    )
    assert nos.name == "MySimNOS"
    assert nos.initial_prompt == "MySimNOS>"
    assert nos.commands == _normalized_commands(commands)


@pytest.mark.parametrize(
    "override, match",
    [
        pytest.param({"name": 123}, r"\bname\b", id="name"),
        pytest.param({"initial_prompt": 123}, r"initial_prompt", id="initial_prompt"),
        pytest.param({"commands": "invalid_commands"}, r"commands", id="commands"),
    ],
)
def test_init_rejects_invalid_field(commands, override, match):
    """Nos() raises ValidationError when a single field has the wrong type.

    Each case keeps the other two fields valid (name/initial_prompt str,
    commands from the shared fixture) so the rejection is attributable to the
    overridden field alone.
    """
    kwargs = {"name": "MySimNOS", "initial_prompt": "MySimNOS>", "commands": commands}
    kwargs.update(override)
    with pytest.raises(ValidationError, match=match):
        Nos(**kwargs)


@pytest.mark.parametrize(
    "data, expected_name, expected_prompt",
    [
        pytest.param({"name": "MySimNOS"}, "MySimNOS", "SimNOS>", id="only_name"),
        pytest.param({"initial_prompt": "MySimNOS>"}, "SimNOS", "MySimNOS>", id="only_initial_prompt"),
        pytest.param({}, "SimNOS", "SimNOS>", id="no_data"),
    ],
)
def test_from_dict_partial_keeps_command_defaults(data, expected_name, expected_prompt):
    """from_dict with partial data keeps defaults for the omitted fields.

    Covers the name-only / initial_prompt-only / no-data cases; commands stays
    empty in all three. (`commands`-only is pinned separately because its
    expected value is the normalized fixture, not `{}`.)
    """
    nos = Nos()
    nos.from_dict(data)
    assert nos.name == expected_name
    assert nos.initial_prompt == expected_prompt
    assert nos.commands == {}


def test_from_dict_only_commands(commands):
    """
    Test that the from_dict method works
    when only the commands are provided.
    """
    nos = Nos()
    nos.from_dict({"commands": commands})
    assert nos.name == "SimNOS"
    assert nos.initial_prompt == "SimNOS>"
    assert nos.commands == _normalized_commands(commands)


def test_from_dict_unknown_top_level_key_raises():
    """A typo'd top-level key is rejected loudly, nothing is committed.

    Pins the D8 (#244) flip of the old lenient contract: `enable_promt`
    used to be dropped silently by the targeted `data.get()` reads.
    The allowed key set is `ModelNosAttributes.model_fields` (SSoT),
    and the check runs before any attribute commit (no-partial-state,
    #232).
    """
    nos = Nos()
    with pytest.raises(ValueError, match=r"unknown top-level field\(s\): \['enable_promt'\]"):
        nos.from_dict({"name": "polluted", "enable_promt": "{base_prompt}#"})
    assert nos.name == "SimNOS"


def test_from_file_schema_invalid_yaml_leaves_nos_untouched(tmp_path):
    """A schema-invalid yaml raises ValidationError before any commit.

    Pins the D8 (#244) merged-view validation on the `from_file` path:
    hot reload (`reload_commands`) calls `from_file` directly and never
    reaches `__init__`'s trailing `validate()`, so a yaml with e.g. an
    int `output` used to be committed silently into a running shell.
    """
    bad_yaml = _write_tmp_file(
        tmp_path,
        "schema_invalid_nos.yaml",
        "name: polluted\ncommands:\n  cmd:\n    output: 123\n    help: int output\n",
    )
    nos = Nos()
    with pytest.raises(ValidationError, match=r"output"):
        nos.from_file(bad_yaml)
    assert nos.name == "SimNOS"
    assert nos.commands == {}


def test_from_dict_unknown_command_field_raises():
    """A typo'd command field fails validation before any commit.

    Pins the D5 (#244) flip of the old lenient contract:
    `ModelNosCommand` is `extra="forbid"` now, so a typo'd field
    (`outptu`) raises ValidationError out of the pre-commit merged-view
    validation instead of being silently accepted.
    """
    nos = Nos()
    with pytest.raises(ValidationError, match=r"outptu"):
        nos.from_dict(
            {
                "name": "polluted",
                "commands": {"cmd": {"output": "x", "help": "x", "outptu": "typo"}},
            }
        )
    assert nos.name == "SimNOS"
    assert nos.commands == {}


def test_from_dict_accepts_output_variants():
    """`output_variants` is a declared data-only field, not a typo.

    Pins the D5 (#244) declaration: 16 platform yamls carry alternate
    captures under this key (#234) and must keep loading under
    `extra="forbid"`.
    """
    nos = Nos(
        dict_args={
            "name": "synth",
            "initial_prompt": "{base_prompt}>",
            "commands": {
                "cmd": {
                    "output": "primary",
                    "help": "x",
                    "output_variants": ["alternate capture"],
                },
            },
        }
    )
    assert nos.commands["cmd"]["output_variants"] == ["alternate capture"]


def test_from_dict_does_not_mutate_caller_dict():
    """Caller-owned data must stay untouched by a load (#244 / D3).

    `from_dict` normalizes `prompt` str -> [str] on a deepcopied
    candidate, so the caller's dict (and, symmetrically, a py plugin's
    module-level `commands` constant) keeps its original authoring
    form — an accidental switch to in-place normalization turns into
    a test failure here.
    """
    caller_commands = {"cmd": {"output": "x", "help": "x", "prompt": "{base_prompt}>"}}
    nos = Nos()
    nos.from_dict({"name": "synth", "commands": caller_commands})
    assert caller_commands["cmd"]["prompt"] == "{base_prompt}>"
    assert isinstance(caller_commands["cmd"]["prompt"], str)


def test_from_dict_normalizes_str_prompt_to_list():
    """A bare-str `prompt` authoring form lands as a list at runtime.

    Pins the load-path normalization (#244 / D3): authoring keeps the
    str/list sugar, runtime consumers (cmd_shell dispatch + mismatch
    log) see lists only — the read-side isinstance branches are gone.
    """
    nos = Nos()
    nos.from_dict(
        {
            "name": "synth",
            "commands": {
                "str form": {"output": "x", "help": "x", "prompt": "{base_prompt}>"},
                "list form": {"output": "x", "help": "x", "prompt": ["{base_prompt}>"]},
                "no prompt": {"output": "x", "help": "x"},
            },
        }
    )
    assert nos.commands["str form"]["prompt"] == ["{base_prompt}>"]
    assert nos.commands["list form"]["prompt"] == ["{base_prompt}>"]
    assert "prompt" not in nos.commands["no prompt"]


def test_from_module_normalizes_str_prompt_to_list(tmp_path):
    """The py-plugin path normalizes prompts the same way as from_dict.

    Same #244 / D3 pin for `_from_module`, which commits through its
    own deepcopied candidate (module-level `commands` constants keep
    their authoring form).
    """
    plugin = _write_tmp_file(
        tmp_path,
        "str_prompt_module.py",
        'NAME = "str_prompt"\nINITIAL_PROMPT = "{base_prompt}>"\n'
        'commands = {"cmd": {"output": "x", "help": "x", "prompt": "{base_prompt}>"}}\n',
    )
    nos = Nos()
    nos.from_file(plugin)
    assert nos.commands["cmd"]["prompt"] == ["{base_prompt}>"]


def test_from_yaml_file(commands):
    """
    Test that the from_file method works .yaml.
    """
    nos = Nos()
    nos.from_file("tests/assets/yaml_nos.yaml")
    assert nos.name == "Custom Nos 0.1.0"
    assert nos.initial_prompt == "{base_prompt}>"
    assert nos.commands == _normalized_commands(commands)


def test_from_file_incorrect_yaml_file():
    """
    Test that the from_file method raises a
    FileNotFoundError when the file is incorrect.
    """
    with pytest.raises(FileNotFoundError, match=r"incorrect_file\.yaml"):
        nos = Nos()
        nos.from_file("tests/assets/incorrect_file.yaml")


def test_from_file_empty_yaml_file(tmp_path):
    """An empty yaml file raises ValueError instead of crashing later.

    Pins the `_from_yaml` mapping guard (#232): `yaml.safe_load` returns
    None for an empty file (e.g. a half-written file observed by hot
    reload mid-save) and `from_dict` used to crash on `data.get` with an
    opaque AttributeError out of the SSH shell thread.
    """
    empty_yaml = _write_tmp_file(tmp_path, "empty_nos.yaml", "")
    with pytest.raises(ValueError, match=r"does not contain a mapping \(got NoneType\)"):
        Nos().from_file(empty_yaml)


def test_from_file_non_mapping_yaml_file(tmp_path):
    """A yaml file with a non-dict top level raises ValueError.

    Same `_from_yaml` guard as the empty-file case (#232), pinned for
    the other non-mapping shape `yaml.safe_load` can return.
    """
    list_yaml = _write_tmp_file(tmp_path, "list_nos.yaml", "- not\n- a\n- mapping\n")
    with pytest.raises(ValueError, match=r"does not contain a mapping \(got list\)"):
        Nos().from_file(list_yaml)


def test_from_dict_non_mapping_commands_leaves_nos_untouched(tmp_path):
    """A non-mapping 'commands' value raises before any mutation.

    Pins the validate-before-commit ordering of `from_dict` (#232):
    `name` used to be committed before `commands.update` raised on a
    malformed value, leaving partial state behind — the same hole
    `_from_module` had with DEVICE_NAME.
    """
    bad_yaml = _write_tmp_file(tmp_path, "bad_commands_nos.yaml", "name: polluted\ncommands: not-a-mapping\n")
    nos = Nos()
    with pytest.raises(ValueError, match=r"'commands' must be a mapping \(got str\)"):
        nos.from_file(bad_yaml)
    assert nos.name == "SimNOS"
    assert nos.commands == {}


def test_from_py_file():
    """
    Test that the from_file method works with .py.
    """
    nos = Nos()
    nos.from_file("tests/assets/module.py")
    assert nos.name == "test_module"
    assert nos.initial_prompt == "{base_prompt}>"
    assert nos.device.__class__.__name__ == "TestModule"
    _assert_module_static_commands_loaded(nos)


def test_from_file_incorrect_py_file():
    """
    Test that the from_file method raises a
    FileNotFoundError when the file is incorrect.
    """
    with pytest.raises(FileNotFoundError, match=r"incorrect_file\.py"):
        nos = Nos()
        nos.from_file("tests/assets/incorrect_file.py")


def test_from_module():
    """
    Test that the from_module method works.
    """
    nos = Nos()
    # pylint: disable=protected-access
    nos._from_module("tests/assets/module.py")
    assert nos.name == "test_module"
    assert nos.initial_prompt == "{base_prompt}>"
    _assert_module_static_commands_loaded(nos)


def test_from_module_incorrect_file():
    """
    Test that the from_module method raises a
    FileNotFoundError when the file is incorrect.
    """
    with pytest.raises(FileNotFoundError, match=r"incorrect_file\.py"):
        nos = Nos()
        # pylint: disable=protected-access
        nos._from_module("tests/assets/incorrect_file.py")


def test_from_module_non_mapping_commands_leaves_nos_untouched(tmp_path):
    """A plugin whose `commands` is not a mapping raises before mutation.

    Pins the `commands` type validation in `_from_module` (#232 cross
    review 2nd round): symmetric with `from_dict`, a malformed
    `commands` value raises ValueError without committing attrs first.
    """
    bad_py = _write_tmp_file(
        tmp_path,
        "bad_commands_plugin.py",
        'NAME = "polluted"\nINITIAL_PROMPT = "{base_prompt}$"\ncommands = "not-a-mapping"\n',
    )
    nos = Nos()
    with pytest.raises(ValueError, match=r"'commands' must be a mapping \(got str\)"):
        nos.from_file(bad_py)
    assert nos.name == "SimNOS"
    assert nos.initial_prompt == "SimNOS>"
    assert nos.commands == {}


def test_from_module_multiple_device_classes_leaves_nos_untouched():
    """A plugin with two local BaseDevice subclasses leaves Nos unchanged.

    Pins the build-before-commit ordering of `_from_module` (#232 cross
    review, failure mode swapped in #241/D5): the multiple-subclass
    ValueError fires in the build phase like the pre-#241 DEVICE_NAME
    AttributeError did, so a broken plugin raises out of `from_file`
    without polluting `nos.commands` / `nos.name` behind the caller's
    back.
    """
    nos = Nos()
    with pytest.raises(ValueError, match=r"multiple BaseDevice subclasses \(DeviceA, DeviceB\)"):
        nos.from_file("tests/assets/broken_multi_device_module.py")
    assert nos.name == "SimNOS"
    assert nos.initial_prompt == "SimNOS>"
    assert "polluting command" not in nos.commands
    assert nos.device is None


def test_from_module_local_class_alias_is_not_a_second_subclass(tmp_path):
    """An alias to the local device class is one definition, not two.

    Pins the dedupe in `_find_device_classes` (3rd code review 🦊 #1):
    `Device = LocalDevice` puts the same class object into
    `vars(module)` twice — without dedupe the loader rejected a
    perfectly valid plugin with the multiple-subclass ValueError.
    """
    alias_py = _write_tmp_file(
        tmp_path,
        "alias_device_plugin.py",
        "from simnos.plugins.nos.platforms_py._templates.base_template import BaseDevice\n"
        'NAME = "alias_plugin"\n'
        'INITIAL_PROMPT = "{base_prompt}>"\n'
        "class LocalDevice(BaseDevice):\n"
        '    """The single local device class."""\n'
        "Device = LocalDevice\n"
        "commands = {}\n",
    )
    nos = Nos()
    nos.from_file(alias_py)
    assert nos.device.__class__.__name__ == "LocalDevice"


def test_from_module_imported_subclass_not_detected():
    """An import-mixin plugin detects only its locally-defined class.

    Pins the `__module__` guard of `_find_device_classes` (#241/D5):
    the imported `CiscoIOS` keeps its origin module name and must not
    trip the multiple-subclass ValueError nor steal the device slot.
    """
    nos = Nos()
    nos.from_file("tests/assets/importing_device_module.py")
    assert nos.device.__class__.__name__ == "LocalDevice"


def test_from_module_device_name_leftover_warns_and_is_ignored(tmp_path, caplog):
    """A leftover DEVICE_NAME constant warns; detection still works.

    Pins the #241/D5 migration warning: DEVICE_NAME is deprecated and
    ignored — the device comes from auto-detection, and the author is
    nudged to delete the constant.
    """
    legacy_py = _write_tmp_file(
        tmp_path,
        "legacy_device_name_plugin.py",
        "from simnos.plugins.nos.platforms_py._templates.base_template import BaseDevice\n"
        'NAME = "legacy"\n'
        'INITIAL_PROMPT = "{base_prompt}>"\n'
        'DEVICE_NAME = "LegacyDevice"\n'
        "class LegacyDevice(BaseDevice):\n"
        '    """Local device class, auto-detected regardless of DEVICE_NAME."""\n'
        "commands = {}\n",
    )
    nos = Nos()
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=_NOS_LOGGER):
        nos.from_file(legacy_py)
    warnings = _nos_log_messages(caplog, logging.WARNING)
    assert any("DEVICE_NAME" in msg and "deprecated and ignored" in msg for msg in warnings)
    assert nos.device.__class__.__name__ == "LegacyDevice"


def test_from_module_no_device_class_keeps_existing_device(tmp_path):
    """A no-device module does not clear a previously set device.

    Pins the #241/D5 commit semantics (2nd design review 🦊 #3): only
    a detected class updates `self.device` — same "existing device
    survives" behavior as the pre-#241 `if classname is not None`
    commit, relevant for filename-list loads and hot reload.
    """
    nos = Nos()
    nos.from_file("tests/assets/module.py")
    device_before = nos.device
    assert device_before is not None
    no_device_py = _write_tmp_file(
        tmp_path,
        "no_device_plugin.py",
        'NAME = "no_device"\nINITIAL_PROMPT = "{base_prompt}>"\ncommands = {}\n',
    )
    nos.from_file(no_device_py)
    assert nos.device is device_before


def test_from_module_override_logs_debug(caplog):
    """A py module overriding already-loaded commands logs at debug (#241 / P-7).

    Pins the observable yaml-vs-py precedence: same-named commands
    are replaced wholesale (per-command full replacement, no deep
    merge) and the override is logged so a plugin author can see
    which already-loaded commands the py module shadows.
    """
    nos = Nos()
    nos.from_dict({"commands": {"show clock": {"output": "from yaml", "help": "static"}}})
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger=_NOS_LOGGER):
        nos.from_file("tests/assets/module.py")
    debug_msgs = _nos_log_messages(caplog, logging.DEBUG)
    assert any("overrides 1 already-loaded command(s)" in msg and "show clock" in msg for msg in debug_msgs)
    # Full replacement: the module's callable output wins over the yaml str.
    assert callable(nos.commands["show clock"]["output"])


def test_register_nos_plugin_directly():
    """
    Test that we can register a nos model directly.
    """
    commands = {
        "terminal width 511": {"output": "", "help": "Set terminal width to 511"},
        "terminal length 0": {"output": "", "help": "Set terminal length to 0"},
        "show clock": {"output": "MySimNOSPlugin system time is 00:00:00"},
    }
    nos = Nos(
        name="MySimNOSPlugin",
        initial_prompt="{base_prompt}>",
        commands=commands,
    )

    assert nos.name == "MySimNOSPlugin"
    assert nos.initial_prompt == "{base_prompt}>"
    assert nos.commands == commands


def test_register_nos_plugin_from_dict():
    """
    Test that we can register a nos model from a dict.
    """
    nos_dict = {
        "name": "MySimNOSPlugin",
        "initial_prompt": "{base_prompt}>",
        "commands": {
            "terminal width 511": {
                "output": "",
                "help": "Set terminal width to 511",
            },
            "terminal length 0": {"output": "", "help": "Set terminal length to 0"},
            "show clock": {"output": "MySimNOSPlugin system time is 00:00:00"},
        },
    }

    nos = Nos(**nos_dict)

    assert nos_dict["name"] == nos.name
    assert nos_dict["initial_prompt"] == nos.initial_prompt
    assert nos_dict["commands"] == nos.commands


def test_register_nos_plugin_from_yaml_file(commands):
    """
    Test that we can register a nos model from a yaml file.
    """
    nos = Nos(filename="tests/assets/yaml_nos.yaml")

    assert nos.name == "Custom Nos 0.1.0"
    assert nos.initial_prompt == "{base_prompt}>"
    assert nos.commands == _normalized_commands(commands)


def test_register_nos_plugin_incorrect_commands():
    """
    Test that we can register a nos model from a dict.
    """
    with pytest.raises(ValidationError, match=r"output"):
        Nos(
            name="MySimNOSPlugin",
            initial_prompt="{base_prompt}>",
            commands={
                "show clock": {"output": 37},
            },
        )


def test_register_nos_plugin_incorrect_name():
    """
    Test that we can register a nos model from a dict.
    """
    with pytest.raises(ValidationError, match=r"\bname\b"):
        Nos(
            name=123,
            initial_prompt="{base_prompt}>",
            commands={
                "show clock": {"output": ""},
            },
        )


def test_register_nos_plugin_incorrect_output():
    """
    Test that we can register a nos model from a dict.
    """
    with pytest.raises(ValidationError, match=r"output"):
        Nos(commands={"show clock": {"output": 42}})


def test_yaml_file_command_is_overwritten_by_corresponding_module():
    """
    Test that when a command in a platform is defined
    both in YAML and Python module, the Python module
    is the one being used.
    """
    nos_yaml = Nos(filename="tests/assets/yaml_nos.yaml")
    nos_py = Nos(filename="tests/assets/module.py")
    nos_combined = Nos(filename="tests/assets/yaml_nos.yaml")
    nos_combined.from_file("tests/assets/module.py")

    combined_dict = dict(nos_yaml.commands)
    combined_dict.update(nos_py.commands)

    assert callable(nos_combined.commands["show clock"]["output"])
    assert callable(combined_dict["show clock"]["output"])
    assert len(combined_dict) == len(nos_combined.commands)


def test_yaml_file_command_is_overwritten_by_corresponding_module_in_init():
    """
    Test that when a command in a platform is defined
    both in YAML and Python module, the Python module
    is the one being used in the init.
    """
    # pylint: disable=duplicate-code
    for filenames in nos_plugins.values():
        for filename in filenames:
            assert isinstance(filename, str)
            assert filename.endswith((".yaml", ".py"))
        assert len(filenames) <= 2
        if len(filenames) == 2:
            assert filenames[0].endswith(".yaml")
            assert filenames[1].endswith(".py")


def test_configuration_file_is_loaded():
    """
    Test that the configuration file is loaded.
    """
    configuration_file = "tests/assets/test_module.yaml.j2"
    with open(configuration_file, encoding="utf-8") as file:
        data = file.read()
    nos = Nos(filename="tests/assets/module.py", configuration_file=configuration_file)
    assert nos.configuration_file == configuration_file
    assert nos.device.configurations == yaml.safe_load(data)
