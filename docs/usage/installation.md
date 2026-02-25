# Installation

## PyPi (Recommended)
SIMNOS has been published in PyPi. To install it using `pip` just run the following command
```bash
python3 -m pip install simnos
```

## Git
The following methods are not recommended unless you are doing development. If this is the case, then we recommend following the `uv` method, as it has all the features and will make your development process easier.

### Using pip
Before installing this way, you need to download and install [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git). If you have already installed `git` just run the following command:
```bash
python3 -m pip install git+https://github.com/Route-Reflector/simnos
```

## Using uv (Recommended for dev)
SIMNOS uses [uv](https://docs.astral.sh/uv/) to manage dependencies and
virtual environments. Follow steps below to install SIMNOS using uv:

```{ .bash .annotate }
curl -LsSf https://astral.sh/uv/install.sh | sh      # (1)
git clone https://github.com/Route-Reflector/simnos   # (2)
cd simnos                                              # (3)
uv sync                                                # (4)
uv run pre-commit install                              # (5)
```

1.  Install uv
2.  Clone SIMNOS repository from GitHub master branch
3.  Navigate to simnos folder
4.  Run uv to create virtual environment and install dependencies
5.  Enable pre-commit hooks for automatic code checks on git commit
