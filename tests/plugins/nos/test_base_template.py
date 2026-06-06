"""Unit tests for the BaseDevice authoring template (#241 / D6).

Pins the `_normalize_configurations` contract on both load paths
(yaml / j2): an empty configuration file means "no configuration"
(`{}`), a non-mapping one is a loud authoring error — symmetric with
the `Nos._from_yaml` non-mapping guard (#232).
"""

import os
import tempfile

import pytest

from simnos.plugins.nos.platforms_py._templates.base_template import BaseDevice


class TestLoadConfigurations:
    """Pins for `BaseDevice.load_configurations` normalization (#241 / D6)."""

    @staticmethod
    def _write_tmp_file(suffix: str, content: str) -> str:
        with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as file:
            file.write(content)
        return file.name

    def _load(self, suffix: str, content: str) -> dict:
        path = self._write_tmp_file(suffix, content)
        try:
            return BaseDevice(configuration_file=path).configurations
        finally:
            os.unlink(path)

    def test_no_configuration_file_is_empty_dict(self):
        """No configuration file at all means an empty dict (existing contract)."""
        assert BaseDevice(configuration_file=None).configurations == {}

    def test_empty_yaml_normalized_to_empty_dict(self):
        """An empty yaml file means "no configuration", not None.

        `yaml.safe_load("")` returns None, which used to land in
        `self.configurations` and crash handlers with
        `TypeError: 'NoneType' object is not subscriptable` (#232 defer).
        """
        assert self._load(".yaml", "") == {}

    def test_non_mapping_yaml_raises(self):
        """A yaml file with a non-dict top level is a loud authoring error."""
        with pytest.raises(ValueError, match=r"must contain a mapping \(got list\)"):
            self._load(".yaml", "- not\n- a\n- mapping\n")

    def test_empty_j2_render_normalized_to_empty_dict(self):
        """A j2 template rendering to nothing follows the same None -> {} rule.

        The j2 path has its own early return in `load_configurations`;
        this pins that the normalization covers it too (#241 design
        1st round 🐙 #5).
        """
        assert self._load(".j2", "{# renders to nothing #}\n") == {}

    def test_non_mapping_j2_render_raises(self):
        """A j2 template rendering to a non-dict yaml is a loud error too."""
        with pytest.raises(ValueError, match=r"must contain a mapping \(got list\)"):
            self._load(".j2", "- rendered\n- list\n")
