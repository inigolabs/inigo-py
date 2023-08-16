import ctypes
from . import ffi
import json


class Query:
    def __init__(self, instance, request):
        self.handle = 0
        self.instance = instance

        self.request = request

    def process_request(self, headers):
        resp_input = ctypes.create_string_buffer(self.request)

        output_ptr = ctypes.c_char_p()
        output_len = ctypes.c_int()

        status_ptr = ctypes.c_char_p()
        status_len = ctypes.c_int()

        self.handle = ffi.process_request(self.instance,
                                          ctypes.create_string_buffer(headers), len(headers),
                                          resp_input, len(self.request),
                                          ctypes.byref(output_ptr), ctypes.byref(output_len),
                                          ctypes.byref(status_ptr), ctypes.byref(status_len))

        resp_dict = {}
        req_dict = {}

        if output_len.value:
            resp_dict = json.loads(output_ptr.value[:output_len.value].decode("utf-8"))

        if status_len.value:
            req_dict = json.loads(status_ptr.value[:status_len.value].decode("utf-8"))

        ffi.disposeMemory(ctypes.cast(output_ptr, ctypes.c_void_p))
        ffi.disposeMemory(ctypes.cast(status_ptr, ctypes.c_void_p))

        return resp_dict, req_dict

    def process_response(self, resp_body):
        if self.handle == 0:
            return None

        output_ptr = ctypes.c_char_p()
        output_len = ctypes.c_int()

        ffi.process_response(
            self.instance,
            self.handle,
            resp_body, len(resp_body),
            ctypes.byref(output_ptr), ctypes.byref(output_len)
        )

        if output_len.value:
            resp_body = output_ptr.value[:output_len.value][:]

        ffi.disposeMemory(ctypes.cast(output_ptr, ctypes.c_void_p))
        ffi.disposeHandle(self.handle)

        return resp_body
