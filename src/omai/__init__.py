"""omai — install, log in, update and equip coding-agent harnesses in one go."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("omai")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0.0.0"
