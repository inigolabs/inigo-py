import ctypes
import json
import os
from django.http import JsonResponse
from django.utils.module_loading import import_string
from django.conf import settings
from . import ffi


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

        output_dict = {}

        if output_len.value:
            output_dict = json.loads(output_ptr.value[:output_len.value].decode("utf-8"))

        ffi.disposeMemory(ctypes.cast(output_ptr, ctypes.c_void_p))
        ffi.disposeHandle(self.handle)

        return output_dict


class DjangoMiddleware:
    def __init__(self, get_response):
        # save response processing fn
        self.get_response = get_response

        self.instance = 0

        if ffi.library is None:
            # library is not found, skip middleware initialization
            return

        # default values
        self.path = '/graphql'

        c = ffi.Config()

        inigo_settings = {}

        if hasattr(settings, 'INIGO'):
            inigo_settings = settings.INIGO

        if inigo_settings.get('ENABLE') is False:
            return

        # process Inigo settings
        if inigo_settings.get('DEBUG'):
            c.debug = inigo_settings.get('DEBUG')
        else:
            # use regular DEBUG setting if specific is not provided
            if hasattr(settings, 'DEBUG'):
                c.debug = settings.DEBUG

        if inigo_settings.get('TOKEN'):
            c.token = str.encode(inigo_settings.get('TOKEN'))

        schema = None
        if inigo_settings.get('GRAPHENE_SCHEMA'):
            schema = import_string(inigo_settings.get('GRAPHENE_SCHEMA'))
        elif inigo_settings.get('SCHEMA_PATH'):
            if os.path.isfile(inigo_settings.get('SCHEMA_PATH')):
                with open(inigo_settings.get('SCHEMA_PATH'), 'r') as f:
                    schema = f.read()
        elif hasattr(settings, 'GRAPHENE') and settings.GRAPHENE.get('SCHEMA'):
            schema = import_string(settings.GRAPHENE.get('SCHEMA'))

        if schema:
            c.schema = str.encode(str(schema))

        if inigo_settings.get('PATH'):
            self.path = inigo_settings.get('PATH')

        # create Inigo instance
        self.instance = ffi.create(ctypes.byref(c))

        error = ffi.check_lasterror()
        if error:
            print("INIGO: " + error.decode('utf-8'))

        if self.instance == 0:
            print("INIGO: error, instance can not be created")

    def __call__(self, request):
        # ignore execution if Inigo is not initialized
        if self.instance == 0:
            return self.get_response(request)

        # 'path' guard -> /graphql
        if request.path != self.path:
            return self.get_response(request)

        # graphiql request
        if request.method == 'GET' and ("text/html" in request.META.get("HTTP_ACCEPT", "*/*")):
            return self.get_response(request)

        # support only POST and GET requests
        if request.method != 'POST' and request.method != 'GET':
            return self.get_response(request)

        # parse request
        gReq: bytes = b''
        if request.method == "POST":
            # read request from body
            gReq = request.body
        elif request.method == "GET":
            # read request from query param
            gReq = str.encode(json.dumps({'query': request.GET.get('query')}))
        q = Query(self.instance, gReq)

        # create inigo context if not present. Should exist before 'headers' call
        if hasattr(request, 'inigo') is False:
            request.inigo = InigoContext()

        # inigo: process request
        resp, req = q.process_request(self.headers(request))

        # introspection query
        if resp:
            return self.respond(resp)

        # modify query if required
        if req:
            if request.method == 'POST':
                body = json.loads(request.body)
                body.update({
                    'query': req.get('query'),
                    'operationName': req.get('operationName'),
                    'variables': req.get('variables'),
                })

                request._body = str.encode(json.dumps(body))
            elif request.method == 'GET':
                params = request.GET.copy()
                params.update({
                    'query': req.get('query')
                })
                request.GET = params

        # forward to request handler
        response = self.get_response(request)

        # inigo: process response
        processed_response = q.process_response(response.content)
        if processed_response:
            return self.respond(processed_response)

        return response

    @staticmethod
    def headers(request):
        headers = {}
        for key, value in request.headers.items():
            headers[key] = value.split(", ")

        return str.encode(json.dumps(headers))

    @staticmethod
    def respond(data):
        response = {
            'data': data.get('data'),
        }

        if data.get('errors'):
            response['errors'] = data.get('errors')

        if data.get('extensions'):
            response['extensions'] = data.get('extensions')

        return JsonResponse(response, status=200)


class InigoContext:
    def __init__(self):
        self.__auth = None
        self.__blocked = False

    @property
    def auth(self):
        return self.__auth

    @auth.setter
    def auth(self, value):
        self.__auth = value

    @property
    def blocked(self):
        return self.__blocked

    def _block(self):
        self.__blocked = True
