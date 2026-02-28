# Documentation

## Multi-language support
SIMNOS uses the [mkdocs-static-i18n](https://github.com/ultrabug/mkdocs-static-i18n) plugin for multi-language documentation. The plugin uses a suffix-based approach to identify language-specific files. For example, to write documentation in Japanese, create a file with the suffix `.ja.md` and the plugin will automatically use it for the Japanese version of the site. If a translated file does not exist, the default language (English) is used as a fallback.
