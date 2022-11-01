import os
import platform
import ctypes


def get_arch() -> str:
    arch, _ = platform.architecture()
    match arch:
        case '32bit':
            return 'i386'
        case '64bit':
            return 'amd64'
    return arch


def get_ext(system_name: str) -> str:
    match system_name:
        case 'windows':
            return '.dll'
        case 'darwin':
            return '.dylib'
    return '.so'


system = platform.system().lower()  # linux, windows, darwin

library = ctypes.CDLL(os.path.join(
    os.path.dirname(__file__), 'lib', f'inigo-{ system }-{ get_arch() }{ get_ext(system) }'
))


class Config(ctypes.Structure):
    _fields_ = [
        ('debug', ctypes.c_bool),
        ('ingest', ctypes.c_char_p),
        ('service', ctypes.c_char_p),
        ('token', ctypes.c_char_p),
        ('schema', ctypes.c_char_p),
        ('introspection', ctypes.c_char_p)
    ]


create = library.create
create.argtypes = [ctypes.POINTER(Config)]
create.restype = ctypes.c_uint64


process_request = library.process_request
process_request.argtypes = [
    ctypes.c_uint64,  # instance
    ctypes.c_char_p, ctypes.c_int,  # header
    ctypes.c_char_p, ctypes.c_int,  # input
    ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_int),  # output
    ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_int),  # status
]
process_request.restype = ctypes.c_uint64


process_response = library.process_response
process_response.argtypes = [
    ctypes.c_uint64,  # instance
    ctypes.c_uint64,  # request handler
    ctypes.POINTER(ctypes.c_char), ctypes.c_int,  # input
    ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_int),  # output
]
process_response.restype = None


ingest_query_data = library.ingest_query_data
ingest_query_data.argtypes = [
    ctypes.c_uint64,  # instance
    ctypes.c_uint64  # request handler
]
ingest_query_data.restype = None


update_schema = library.update_schema
update_schema.argtypes = [
    ctypes.c_uint64,  # instance
    ctypes.c_char_p  # input
]
update_schema.restype = ctypes.c_bool


get_version = library.get_version
get_version.argtypes = None
get_version.restype = ctypes.c_char_p  # version


disposeHandle = library.disposeHandle
disposeHandle.argtypes = [
    ctypes.c_uint64  # request handler
]
disposeHandle.restype = None


disposeMemory = library.disposeMemory
disposeMemory.argtypes = [
    ctypes.c_void_p
]
disposeMemory.restype = None
