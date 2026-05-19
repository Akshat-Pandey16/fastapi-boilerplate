"""FastAPI boilerplate application package."""

from importlib import metadata

try:
    __version__ = metadata.version("fastapi-boilerplate")
except metadata.PackageNotFoundError:
    __version__ = "0.0.0+local"

__all__ = ["__version__"]
