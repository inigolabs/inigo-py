import ctypes
import json
import jwt
import os
import orjson
from django.http import JsonResponse
from django.utils.module_loading import import_string
from django.conf import settings
from . import ffi


class Query:
    def __init__(self, instance, query):
        self.handle = 0
        self.instance = instance

        self.query = b''
        if query:
            self.query = str.encode(query)

    def process_request(self, token):
        resp_input = ctypes.create_string_buffer(self.query)

        output_ptr = ctypes.c_char_p()
        output_len = ctypes.c_int()

        status_ptr = ctypes.c_char_p()
        status_len = ctypes.c_int()

        auth = b''
        if token:
            auth = b'{"jwt":"%s"}' % str.encode(token)

        self.handle = ffi.process_request(self.instance,
                                          ctypes.create_string_buffer(auth), len(auth),
                                          resp_input, len(self.query),
                                          ctypes.byref(output_ptr), ctypes.byref(output_len),
                                          ctypes.byref(status_ptr), ctypes.byref(status_len))

        output_dict = {}
        status_dict = {}

        if output_len.value:
            output_dict = json.loads(output_ptr.value[:output_len.value].decode("utf-8"))

        if status_len.value:
            status_dict = json.loads(status_ptr.value[:status_len.value].decode("utf-8"))

        ffi.disposeMemory(ctypes.cast(output_ptr, ctypes.c_void_p))
        ffi.disposeMemory(ctypes.cast(status_ptr, ctypes.c_void_p))

        return output_dict, status_dict

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

    def ingest(self):
        if self.handle == 0:
            return

        # auto disposes of request handle
        ffi.ingest_query_data(self.instance, self.handle)
        self.handle = 0


class DjangoMiddleware:
    def __init__(self, get_response):
        # save response processing fn
        self.get_response = get_response

        if ffi.library is None:
            # library is not found, skip middleware initialization
            return

        # default values
        self.path = '/graphql'
        self.jwt = 'authorization'  # authorization header name, jwt expected

        c = ffi.Config()

        inigo_settings = {}

        if hasattr(settings, 'INIGO'):
            inigo_settings = settings.INIGO

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

        if inigo_settings.get('JWT'):
            self.jwt = inigo_settings.get('JWT')

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
        query: str = ''
        if request.method == "POST":
            # read request from body
            query = json.loads(request.body).get('query')
        elif request.method == "GET":
            # read request from query param
            query = request.GET.get('query')
        q = Query(self.instance, query)

        # create inigo context if not present. Should exist before 'get_auth_token' call
        if hasattr(request, 'inigo') is False:
            request.inigo = InigoContext()

        token = self.get_auth_token(self.jwt, request)

        # inigo: process request
        output, status = q.process_request(token)

        # introspection query
        if output and output.get('data') and output.get('data').get('__schema'):
            q.ingest()

            return self.respond(output)

        if status and status.get('status') == 'BLOCKED':
            q.ingest()

            request.inigo._block()

            return self.respond(status)

        # modify query if required
        if status and status.get('errors') is not None:
            if request.method == 'POST':
                body = json.loads(request.body)
                body.update({
                    'query': output.get('query')
                })

                request._body = str.encode(json.dumps(body))
            elif request.method == 'GET':
                params = request.GET.copy()
                params.update({
                    'query': output.get('query')
                })
                request.GET = params

        # forward to request handler
        response = self.get_response(request)

        # return if response is not json
        try:
            _ = orjson.loads(response.content)
        except ValueError:  # includes simplejson.decoder.JSONDecodeError
            # cannot parse json
            q.ingest()

            return response

        # inigo: process response
        processed_response = q.process_response(response.content)
        if processed_response:
            return self.respond(processed_response)

        return response

    @staticmethod
    def get_auth_token(header, request):
        if hasattr(request, 'inigo') and isinstance(request.inigo, InigoContext) is False:
            raise Warning("'inigo' attr is not InigoContext instance")

        # read from request object
        if hasattr(request, 'inigo') and isinstance(request.inigo, InigoContext) and request.inigo.auth:
            return jwt.encode(request.inigo.auth, key=None, algorithm=None)

        # read auth header
        if request.headers.get(header):
            return request.headers.get(header)

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
