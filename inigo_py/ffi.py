import os
import platform
import ctypes


def get_arch(system_name):
    machine = platform.machine().lower()
    if system_name == 'darwin':
        if machine == 'x86_64':
            return 'amd64'
        elif machine == 'arm64':
            return 'arm64'

    arch, _ = platform.architecture()

    if system_name == 'linux':
        if machine == 'x86_64' and arch == '64bit':
            return 'amd64'
        elif machine == 'aarch64':
            return 'arm64'
        elif machine == 'x86_64' and arch == '32bit':
            return '386'
        elif machine.startswith('arm'):  # armv7l
            return 'arm'

    if system_name == 'windows':
        if arch == '64bit':
            return 'amd64'

    return machine


def get_ext(system_name):
    if system_name == 'windows':
        return '.dll'
    elif system_name == 'darwin':
        return '.dylib'

    return '.so'


system = platform.system().lower()  # linux, windows, darwin
filename = f'inigo-{ system }-{ get_arch(system) }{ get_ext(system) }'

try:
    library = ctypes.CDLL(os.path.join(os.path.dirname(__file__), 'lib', filename))

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


    check_lasterror = library.check_lasterror
    check_lasterror.argtypes = None
    check_lasterror.restype = ctypes.c_char_p
except Exception as err:
    # Unable to open libc dynamic library
    raise Exception(f"""
        
          Unable to open inigo shared library. 
          
          Please get in touch with us for support:
          email: support@inigo.io
          slack: https://slack.inigo.io
          
          Please share the below info with us:
          error:    { str(err) }
          uname:    { platform.uname().__str__() }
          arch:     { platform.architecture().__str__() }
          
        """)

