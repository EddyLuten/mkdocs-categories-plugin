# Contributing

If you find a bug or wish to request a feature, feel free to open a [new issue](https://codeberg.org/luten/mkdocs-categories-plugin/issues/new).

PRs are welcome and appreciated, but please _open an issue first_ to discuss the change you'd like to make first. PRs that haven't been discussed, or that fall outside the intended scope of this project, may be closed without merging.

## Local Development

Upgrade pip and install the dependencies:

```zsh
python -m pip install --upgrade pip
pip install pylint mkdocs natsort setuptools
```

Installing a local copy of the plugin (potentially from your MkDoc's venv location):

```zsh
pip install -e /path/to/mkdocs-alias-plugin/
```

Run the linter:

```zsh
pylint $(git ls-files '*.py')
```
