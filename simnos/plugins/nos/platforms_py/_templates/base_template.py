"""
This module is intended to be used as a template
for creating new module devices for SIMNOS.
It has certain attributes and methods which are
generally common to all devices.
"""

from jinja2 import Environment, PackageLoader, Template
import yaml


class BaseDevice:
    """Interface for all devices."""

    def __init__(self, configuration_file: str | None = None) -> None:
        self.configurations = self.load_configurations(configuration_file)
        self.env = Environment(
            loader=PackageLoader("simnos.plugins.nos.platforms_py", "templates"),
            autoescape=False,  # noqa: S701 — output is CLI text, not HTML
        )

    @staticmethod
    def _normalize_configurations(data, configuration_file: str) -> dict:
        """Normalize a loaded configuration: None -> {}, non-dict -> ValueError.

        An empty file (or a Jinja2 template rendering to nothing) means
        "no configuration" — `yaml.safe_load` returns None for it, which
        used to land in `self.configurations` and crash handlers with
        `TypeError: 'NoneType'` on item access (#241 / #232 defer). The
        order matters: `data or {}` would also coerce an empty list /
        empty str to {} and contradict the non-mapping guard below (#232).
        """
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError(
                f"Configuration file '{configuration_file}' must contain a mapping (got {type(data).__name__})"
            )
        return data

    def load_configurations(self, configuration_file: str | None) -> dict:
        """
        Load configurations from a file.
        The file can be either a YAML file or a Jinja2 template.
        """
        if not configuration_file:
            return {}
        # `.yml` accepted to match the inventory loader (#345); it takes the
        # plain-YAML branch below.
        if not configuration_file.endswith((".yaml", ".yml", ".j2")):
            raise ValueError("Configuration file must be a YAML file (.yaml/.yml) or a Jinja2 template (.j2).")
        if configuration_file.endswith(".j2"):
            data: str = ""
            with open(configuration_file, encoding="utf-8") as file:
                data = file.read()
            data_j2 = Template(data, autoescape=False, trim_blocks=True, lstrip_blocks=True).render()
            data = yaml.safe_load(data_j2)
            return self._normalize_configurations(data, configuration_file)

        with open(configuration_file, encoding="utf-8") as file:
            data = yaml.safe_load(file)
        return self._normalize_configurations(data, configuration_file)

    def render(self, template: str, **kwargs) -> str:
        """Render a template."""
        tmpl = self.env.get_template(template)
        return tmpl.render(**kwargs)
