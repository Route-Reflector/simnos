"""
Test module for simnos.core.nos module.
This module can be found at simnos/core/nos.py

Since #317 P-4 `Nos` carries no legacy command surface (``commands`` dict /
scalar prompts / ``from_dict``): a py module supplies the device class + the
A3 ``handler:`` namespace only, and command data comes from the A3 platform
dir (covered by tests/plugins/test_cmd_shell_a3.py). These tests pin the py
module load path (`_from_module`) and the file dispatch (`from_file`).
"""

import logging
import os
import types

import pytest
import yaml

from simnos.core.nos import Nos
from simnos.plugins.nos import nos_plugins

_NOS_LOGGER = "simnos.core.nos"


def _write_tmp_file(tmp_path, name: str, content: str) -> str:
    """Write a throwaway plugin file under ``tmp_path`` and return its path.

    ``tmp_path`` is pytest's per-test temp dir, so cleanup is automatic.
    """
    tmp_file = tmp_path / name
    tmp_file.write_text(content, encoding="utf-8")
    return str(tmp_file)


def test_init_without_arguments():
    """
    Test that the init method works when no arguments are provided.
    """
    nos = Nos()
    assert nos.name == "SimNOS"
    assert nos.device is None
    assert nos.handlers == {}
    assert nos.resolved_platform is None


def test_init_with_argument_name():
    """
    Test that the init method works when the name argument is provided.
    """
    nos = Nos(name="MySimNOS")
    assert nos.name == "MySimNOS"


@pytest.mark.parametrize("ext", [".yaml", ".yml"])
def test_from_file_rejects_legacy_yaml(ext):
    """The legacy monolithic ``.yaml/.yml`` platform form was removed in v3 (#264).

    ``from_file`` now loads only A3 platform dirs and ``.py`` modules; a
    standalone yaml file is rejected at the extension guard (before the
    isfile check), so the breaking change surfaces loudly instead of silently
    doing nothing.
    """
    with pytest.raises(ValueError, match=r"Unsupported.*file extension"):
        Nos().from_file(f"tests/assets/whatever{ext}")


def test_from_py_file():
    """
    Test that the from_file method works with .py.

    The module supplies dynamic behavior only (#317 P-4): the device class is
    auto-detected and its non-`_` methods join the `handler:` namespace. The
    name stays at the constructor default — only an A3 dir load renames a Nos.
    """
    nos = Nos()
    nos.from_file("tests/assets/module.py")
    assert nos.name == "SimNOS"
    assert nos.device is not None
    assert nos.device.__class__.__name__ == "TestModule"
    assert {"make_show_clock", "make_show_version"} <= set(nos.handlers)


def test_from_file_incorrect_py_file():
    """
    Test that the from_file method raises a
    FileNotFoundError when the file is incorrect.
    """
    with pytest.raises(FileNotFoundError, match=r"incorrect_file\.py"):
        nos = Nos()
        nos.from_file("tests/assets/incorrect_file.py")


def test_from_module_commands_dict_is_rejected(tmp_path):
    """A module-level non-empty `commands` dict fails the load loudly (#317 P-4).

    The py dict authoring channel is gone; silently ignoring a leftover dict
    would hide the author's intent (the "loads but never merges" window), so
    `_from_module` rejects it at the load boundary — the successor of the P-3
    merge-time guard. Nothing is committed (no-partial-state, #232).
    """
    dict_py = _write_tmp_file(
        tmp_path,
        "dict_author_plugin.py",
        'commands = {"show x": {"output": "x", "help": "x"}}\n',
    )
    nos = Nos()
    with pytest.raises(ValueError, match="py dict authoring was removed"):
        nos.from_file(dict_py)
    assert nos.device is None
    assert nos.handlers == {}


def test_from_module_empty_commands_dict_is_ignored(tmp_path):
    """A vestigial *empty* `commands = {}` is contentless and stays ignored.

    Same contract as the P-3 merge guard: only a non-empty dict is an
    authoring attempt; an empty leftover must not brick the plugin.
    """
    empty_py = _write_tmp_file(
        tmp_path,
        "empty_commands_plugin.py",
        "from simnos.plugins.nos.base_device import BaseDevice\n"
        "class Dev(BaseDevice):\n"
        '    """Single local device class."""\n'
        "commands = {}\n",
    )
    nos = Nos()
    nos.from_file(empty_py)
    assert nos.device.__class__.__name__ == "Dev"


def test_from_module_multiple_device_classes_leaves_nos_untouched():
    """A plugin with two local BaseDevice subclasses leaves Nos unchanged.

    Pins the build-before-commit ordering of `_from_module` (#232 cross
    review, failure mode swapped in #241/D5): the multiple-subclass
    ValueError fires in the build phase, so a broken plugin raises out of
    `from_file` without polluting `nos.device` / `nos.handlers` behind the
    caller's back.
    """
    nos = Nos()
    with pytest.raises(ValueError, match=r"multiple BaseDevice subclasses \(DeviceA, DeviceB\)"):
        nos.from_file("tests/assets/broken_multi_device_module.py")
    assert nos.name == "SimNOS"
    assert nos.device is None
    assert nos.handlers == {}


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
        "from simnos.plugins.nos.base_device import BaseDevice\n"
        "class LocalDevice(BaseDevice):\n"
        '    """The single local device class."""\n'
        "Device = LocalDevice\n",
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
    no_device_py = _write_tmp_file(tmp_path, "no_device_plugin.py", "# no BaseDevice subclass here\n")
    nos.from_file(no_device_py)
    assert nos.device is device_before


class TestHandlerNamespace:
    """`Nos._from_module` builds the A3 `handler:` namespace (#317 / P-1, 案D)."""

    def test_collects_methods_and_module_functions(self, tmp_path):
        py = _write_tmp_file(
            tmp_path,
            "handlers_plugin.py",
            "from simnos.plugins.nos.base_device import BaseDevice\n"
            "class Dev(BaseDevice):\n"
            "    def make_a(self, device=None, **kw):\n"
            '        return "a"\n'
            "    @staticmethod\n"
            "    def make_b(device=None, **kw):\n"
            '        return "b"\n'
            "    def _private(self):\n"  # underscore -> excluded
            '        return "x"\n'
            "def make_c(device=None, **kw):\n"  # module-level function
            '    return "c"\n',
        )
        nos = Nos()
        nos.from_file(py)
        # method + staticmethod + module-level function collected; `_private` excluded.
        assert set(nos.handlers) == {"make_a", "make_b", "make_c"}

    def test_rejects_classmethod_handler(self, tmp_path):
        py = _write_tmp_file(
            tmp_path,
            "classmethod_plugin.py",
            "from simnos.plugins.nos.base_device import BaseDevice\n"
            "class Dev(BaseDevice):\n"
            "    @classmethod\n"
            "    def make_a(cls, device=None, **kw):\n"
            '        return "a"\n',
        )
        nos = Nos()
        with pytest.raises(ValueError, match="classmethod"):
            nos.from_file(py)

    def test_rejects_class_module_name_collision(self, tmp_path):
        py = _write_tmp_file(
            tmp_path,
            "collision_plugin.py",
            "from simnos.plugins.nos.base_device import BaseDevice\n"
            "class Dev(BaseDevice):\n"
            "    def make_a(self, device=None, **kw):\n"
            '        return "method"\n'
            "def make_a(device=None, **kw):\n"  # same name at module level -> loud
            '    return "func"\n',
        )
        nos = Nos()
        with pytest.raises(ValueError, match="unambiguous"):
            nos.from_file(py)

    def test_mro_override_and_inherited_base(self):
        # The MRO walk (#317 / P-1) tested directly on `_build_handler_namespace`:
        # `_from_module` allows only ONE local BaseDevice subclass, so a custom
        # intermediate base is realistically an *imported* class (different
        # `__module__`); here we build the class hierarchy in-process and hand it
        # to the namespace builder. A derived override wins (normal method
        # resolution, not a collision, 3rd round codex#3); a handler defined only
        # on the intermediate base is still collected (gemini#1).
        from simnos.core.nos import _build_handler_namespace
        from simnos.plugins.nos.base_device import BaseDevice

        class Mid(BaseDevice):
            def make_shared(self, device=None, **kw):
                return "shared"

            def make_a(self, device=None, **kw):
                return "base"

        class Dev(Mid):
            def make_own(self, device=None, **kw):
                return "own"

            def make_a(self, device=None, **kw):  # override
                return "derived"

        module = types.ModuleType("m")  # no module-level functions
        ns = _build_handler_namespace(module, [Dev])
        assert {"make_shared", "make_a", "make_own"} == set(ns)
        # Derived version wins (getattr on the leaf class resolves the override).
        assert ns["make_a"](None, base_prompt="R1", current_mode="user", current_prompt="R1>", command="x") == "derived"

    def test_sources_dedup_and_fresh_list(self, tmp_path):
        """`sources` records each loaded path once, via a fresh list (#317 P-4).

        Hot reload re-runs `from_file` on the same target per change, so the
        diagnostic list must not grow into a reload history (2nd round 🐳#1);
        and like `handlers`, the fresh-list commit is what makes the
        `_NOS_RELOAD_ATTRS` reference snapshot rollback-safe (2nd round 🦊#1).
        """
        py = _write_tmp_file(tmp_path, "src_plugin.py", 'def make_a(device, **kw):\n    return "a"\n')
        nos = Nos()
        nos.from_file(py)
        first = nos.sources
        assert first == [py]
        nos.from_file(py)  # hot-reload shape: same target again
        assert nos.sources == [py]  # deduplicated, not a history
        py_b = _write_tmp_file(tmp_path, "src_plugin_b.py", 'def make_b(device, **kw):\n    return "b"\n')
        nos.from_file(py_b)
        assert nos.sources == [py, py_b]
        assert nos.sources is not first  # fresh list — the snapshotted one is untouched
        assert first == [py]

    def test_handlers_accumulate_across_multi_file_load_as_fresh_dict(self, tmp_path):
        """A multi-file load merges handler namespaces later-wins, via a fresh dict.

        The fresh-dict commit is what makes the `_NOS_RELOAD_ATTRS` reference
        snapshot rollback-safe under hot reload (#317 / P-1) — an in-place
        `.update` would mutate the snapshotted dict.
        """
        py_a = _write_tmp_file(tmp_path, "a_plugin.py", 'def make_a(device, **kw):\n    return "a"\n')
        py_b = _write_tmp_file(tmp_path, "b_plugin.py", 'def make_b(device, **kw):\n    return "b"\n')
        nos = Nos()
        nos.from_file(py_a)
        first = nos.handlers
        nos.from_file(py_b)
        assert set(nos.handlers) == {"make_a", "make_b"}
        assert nos.handlers is not first  # fresh dict, not in-place update
        assert set(first) == {"make_a"}  # the snapshotted dict is untouched


def test_registry_data_source_is_a3_dir_plus_optional_py_module():
    """Every registry entry is an A3 platform dir, optionally + a co-named py module.

    The legacy ``platforms_yaml/<p>.yaml`` data source was removed in v3 (#264)
    and the py-only registration branch in #317 P-4: a platform's static
    command data lives in an A3 ``platforms/<p>/`` directory (always the first
    entry), and a ``platforms_py/<p>.py`` handler module may be appended last.
    """
    # pylint: disable=duplicate-code
    for filenames in nos_plugins.values():
        for filename in filenames:
            assert isinstance(filename, str)
        assert 1 <= len(filenames) <= 2
        # The first entry is always the A3 dir; a py module can only append.
        assert os.path.isdir(filenames[0])
        if len(filenames) == 2:
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
    assert nos.device is not None
    assert nos.device.configurations == yaml.safe_load(data)


def test_from_module_no_device_class_warns(tmp_path, caplog):
    """A module without a BaseDevice subclass loads with a warning, not an error.

    A handler module normally ships a device class; a bare module-functions-only
    one is legal (module-level handlers) but the missing device is worth a nudge.
    """
    py = _write_tmp_file(tmp_path, "bare_functions_plugin.py", 'def make_x(device, **kw):\n    return "x"\n')
    nos = Nos()
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=_NOS_LOGGER):
        nos.from_file(py)
    assert any("defines no BaseDevice subclass" in r.getMessage() for r in caplog.records)
    assert nos.device is None
    assert set(nos.handlers) == {"make_x"}
