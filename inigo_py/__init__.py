import pathlib

from .ffi import get_version
from .middleware import DjangoMiddleware, InigoContext

__all__ = [
    'get_version',
    'DjangoMiddleware',
    'InigoContext'
]

__version__ = (pathlib.Path(__file__).parent.resolve() / "VERSION").read_text(encoding="utf-8").strip()
