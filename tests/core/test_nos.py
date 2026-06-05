"""
Test module for simnos.core.nos module.
This module can be found at simnos/core/nos.py
"""

import pathlib
import tempfile
import unittest

from pydantic import ValidationError
import pytest
import yaml

from simnos.core.nos import Nos
from simnos.plugins.nos import nos_plugins
from tests.assets import module


# pylint: disable=too-many-public-methods
class NosTest(unittest.TestCase):
    """
    Test class for Nos.
    """

    commands: dict = {}

    @classmethod
    def setup_class(cls):
        """
        Setup class for NosTest.
        """
        with open("tests/assets/yaml_nos.yaml", encoding="utf-8") as yml_file:
            cls.commands = yaml.safe_load(yml_file)["commands"]

    def test_init_without_arguments(self):
        """
        Test that the init method works when no arguments are provided.
        """
        nos = Nos()
        assert nos.name == "SimNOS"
        assert nos.initial_prompt == "SimNOS>"
        assert nos.commands == {}

    def test_init_with_arguments(self):
        """
        Test that the init method works when arguments are provided.
        """
        nos = Nos(name="MySimNOS", initial_prompt="MySimNOS>", commands=self.commands)
        assert nos.name == "MySimNOS"
        assert nos.initial_prompt == "MySimNOS>"
        assert nos.commands == self.commands

    def test_init_with_argument_name(self):
        """
        Test that the init method works when the name argument is provided.
        """
        nos = Nos(name="MySimNOS")
        assert nos.name == "MySimNOS"
        assert nos.initial_prompt == "SimNOS>"
        assert nos.commands == {}

    def test_init_with_argument_initial_prompt(self):
        """
        Test that the init method works when
        the initial_prompt argument is provided.
        """
        nos = Nos(initial_prompt="MySimNOS>")
        assert nos.name == "SimNOS"
        assert nos.initial_prompt == "MySimNOS>"
        assert nos.commands == {}

    def test_init_with_argument_commands(self):
        """
        Test that the init method works when the commands argument is provided.
        """
        nos = Nos(commands=self.commands)
        assert nos.name == "SimNOS"
        assert nos.initial_prompt == "SimNOS>"
        assert nos.commands == self.commands

    def test_validate(self):
        """
        Test that the validate raises a ValidationError
        when the NOS attributes are invalid.
        """
        with pytest.raises(ValidationError, match=r"commands"):
            nos = Nos(commands="invalid_commands")
            nos.validate()

    def test_from_dict_correct(self):
        """
        Test that the from_dict method works when the data is correct.
        """
        nos = Nos()
        nos.from_dict(
            {
                "name": "MySimNOS",
                "initial_prompt": "MySimNOS>",
                "commands": self.commands,
            }
        )
        assert nos.name == "MySimNOS"
        assert nos.initial_prompt == "MySimNOS>"
        assert nos.commands == self.commands

    def test_from_dict_incorrect_name(self):
        """
        Test that Nos raises a ValidationError when the name is incorrect.
        """
        with pytest.raises(ValidationError, match=r"\bname\b"):
            Nos(name=123, initial_prompt="MySimNOS>", commands=self.commands)

    def test_from_dict_incorrect_initial_prompt(self):
        """
        Test that Nos raises a ValidationError when the initial_prompt is incorrect.
        """
        with pytest.raises(ValidationError, match=r"initial_prompt"):
            Nos(name="MySimNOS", initial_prompt=123, commands=self.commands)

    def test_from_dict_incorrect_commands(self):
        """
        Test that Nos raises a ValidationError when the commands are incorrect.
        """
        with pytest.raises(ValidationError, match=r"commands"):
            Nos(name="MySimNOS", initial_prompt="MySimNOS>", commands="invalid_commands")

    def test_from_dict_only_name(self):
        """
        Test that the from_dict method works when only the name is provided.
        """
        nos = Nos()
        nos.from_dict({"name": "MySimNOS"})
        assert nos.name == "MySimNOS"
        assert nos.initial_prompt == "SimNOS>"
        assert nos.commands == {}

    def test_from_dict_only_initial_prompt(self):
        """
        Test that the from_dict method works
        when only the initial_prompt is provided.
        """
        nos = Nos()
        nos.from_dict({"initial_prompt": "MySimNOS>"})
        assert nos.name == "SimNOS"
        assert nos.initial_prompt == "MySimNOS>"
        assert nos.commands == {}

    def test_from_dict_only_commands(self):
        """
        Test that the from_dict method works
        when only the commands are provided.
        """
        nos = Nos()
        nos.from_dict({"commands": self.commands})
        assert nos.name == "SimNOS"
        assert nos.initial_prompt == "SimNOS>"
        assert nos.commands == self.commands

    def test_from_dict_no_data(self):
        """
        Test that the from_dict method works when no data is provided.
        """
        nos = Nos()
        nos.from_dict({})
        assert nos.name == "SimNOS"
        assert nos.initial_prompt == "SimNOS>"
        assert nos.commands == {}

    def test_from_yaml_file(self):
        """
        Test that the from_file method works .yaml.
        """
        nos = Nos()
        nos.from_file("tests/assets/yaml_nos.yaml")
        assert nos.name == "Custom Nos 0.1.0"
        assert nos.initial_prompt == "{base_prompt}>"
        assert nos.commands == self.commands

    def test_from_file_incorrect_yaml_file(self):
        """
        Test that the from_file method raises a
        FileNotFoundError when the file is incorrect.
        """
        with pytest.raises(FileNotFoundError, match=r"incorrect_file\.yaml"):
            nos = Nos()
            nos.from_file("tests/assets/incorrect_file.yaml")

    def _write_tmp_file(self, name: str, content: str) -> str:
        """Write a throwaway plugin file and return its path (auto-cleaned)."""
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        tmp_file = pathlib.Path(tmp_dir.name) / name
        tmp_file.write_text(content, encoding="utf-8")
        return str(tmp_file)

    def test_from_file_empty_yaml_file(self):
        """An empty yaml file raises ValueError instead of crashing later.

        Pins the `_from_yaml` mapping guard (#232): `yaml.safe_load` returns
        None for an empty file (e.g. a half-written file observed by hot
        reload mid-save) and `from_dict` used to crash on `data.get` with an
        opaque AttributeError out of the SSH shell thread.
        """
        empty_yaml = self._write_tmp_file("empty_nos.yaml", "")
        with pytest.raises(ValueError, match=r"does not contain a mapping \(got NoneType\)"):
            Nos().from_file(empty_yaml)

    def test_from_file_non_mapping_yaml_file(self):
        """A yaml file with a non-dict top level raises ValueError.

        Same `_from_yaml` guard as the empty-file case (#232), pinned for
        the other non-mapping shape `yaml.safe_load` can return.
        """
        list_yaml = self._write_tmp_file("list_nos.yaml", "- not\n- a\n- mapping\n")
        with pytest.raises(ValueError, match=r"does not contain a mapping \(got list\)"):
            Nos().from_file(list_yaml)

    def test_from_dict_non_mapping_commands_leaves_nos_untouched(self):
        """A non-mapping 'commands' value raises before any mutation.

        Pins the validate-before-commit ordering of `from_dict` (#232):
        `name` used to be committed before `commands.update` raised on a
        malformed value, leaving partial state behind — the same hole
        `_from_module` had with DEVICE_NAME.
        """
        bad_yaml = self._write_tmp_file("bad_commands_nos.yaml", "name: polluted\ncommands: not-a-mapping\n")
        nos = Nos()
        with pytest.raises(ValueError, match=r"'commands' must be a mapping \(got str\)"):
            nos.from_file(bad_yaml)
        assert nos.name == "SimNOS"
        assert nos.commands == {}

    def test_from_py_file(self):
        """
        Test that the from_file method works with .py.
        """
        nos = Nos()
        nos.from_file("tests/assets/module.py")
        assert nos.name == "test_module"
        assert nos.initial_prompt == "{base_prompt}>"
        assert nos.device.__class__.__name__ == "TestModule"
        self.assertTrue(
            all(item in nos.commands.items() for item in module.commands.items() if not callable(item[1]["output"]))
        )

    def test_from_file_incorrect_py_file(self):
        """
        Test that the from_file method raises a
        FileNotFoundError when the file is incorrect.
        """
        with pytest.raises(FileNotFoundError, match=r"incorrect_file\.py"):
            nos = Nos()
            nos.from_file("tests/assets/incorrect_file.py")

    def test_from_module(self):
        """
        Test that the from_module method works.
        """
        nos = Nos()
        # pylint: disable=protected-access
        nos._from_module("tests/assets/module.py")
        assert nos.name == "test_module"
        assert nos.initial_prompt == "{base_prompt}>"
        self.assertTrue(
            all(item in nos.commands.items() for item in module.commands.items() if not callable(item[1]["output"]))
        )

    def test_from_module_incorrect_file(self):
        """
        Test that the from_module method raises a
        FileNotFoundError when the file is incorrect.
        """
        with pytest.raises(FileNotFoundError, match=r"incorrect_file\.py"):
            nos = Nos()
            # pylint: disable=protected-access
            nos._from_module("tests/assets/incorrect_file.py")

    def test_from_module_broken_device_name_leaves_nos_untouched(self):
        """A plugin whose DEVICE_NAME class is missing leaves Nos unchanged.

        Pins the build-before-commit ordering of `_from_module` (#232 cross
        review): attrs/commands used to be committed before the DEVICE_NAME
        validation, so a broken plugin raised out of `from_file` but still
        polluted `nos.commands` / `nos.name` behind the caller's back.
        """
        nos = Nos()
        with pytest.raises(AttributeError, match=r"DEVICE_NAME='MissingClass'"):
            nos.from_file("tests/assets/broken_device_name_module.py")
        assert nos.name == "SimNOS"
        assert nos.initial_prompt == "SimNOS>"
        assert "polluting command" not in nos.commands
        assert nos.device is None

    def test_register_nos_plugin_directly(self):
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

    def test_register_nos_plugin_from_dict(self):
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

    def test_register_nos_plugin_from_yaml_file(self):
        """
        Test that we can register a nos model from a yaml file.
        """
        nos = Nos(filename="tests/assets/yaml_nos.yaml")

        assert nos.name == "Custom Nos 0.1.0"
        assert nos.initial_prompt == "{base_prompt}>"
        assert nos.commands == self.commands

    def test_register_nos_plugin_incorrect_commands(self):
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

    def test_register_nos_plugin_incorrect_name(self):
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

    def test_register_nos_plugin_incorrect_output(self):
        """
        Test that we can register a nos model from a dict.
        """
        with pytest.raises(ValidationError, match=r"output"):
            Nos(commands={"show clock": {"output": 42}})

    def test_yaml_file_command_is_overwritten_by_corresponding_module(self):
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

    def test_yaml_file_command_is_overwritten_by_corresponding_module_in_init(self):
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

    def test_configuration_file_is_loaded(self):
        """
        Test that the configuration file is loaded.
        """
        configuration_file = "tests/assets/test_module.yaml.j2"
        with open(configuration_file, encoding="utf-8") as file:
            data = file.read()
        nos = Nos(filename="tests/assets/module.py", configuration_file=configuration_file)
        assert nos.configuration_file == configuration_file
        assert nos.device.configurations == yaml.safe_load(data)
