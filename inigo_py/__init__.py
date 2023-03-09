import pathlib

from .ffi import get_version
from .query import Query

__all__ = [
    'get_version',
    'Query'
]

__version__ = (pathlib.Path(__file__).parent.resolve() / "VERSION").read_text(encoding="utf-8").strip()
