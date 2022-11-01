import ctypes
import json
import jwt
from typing import Dict, Callable, Any
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.utils.module_loading import import_string
from django.conf import settings
from . import ffi


class Query:
    instance: int
    handle: int
    query: bytes

    def __init__(self, instance: int, query: str):
        self.instance = instance
        self.query = str.encode(query)

    def process_request(self, auth: str) -> (Dict, Dict):
        resp_input = ctypes.create_string_buffer(self.query)

        output_ptr = ctypes.c_char_p()
        output_len = ctypes.c_int()

        status_ptr = ctypes.c_char_p()
        status_len = ctypes.c_int()

        auth = ctypes.create_string_buffer(b'{"jwt":"%s"}' % str.encode(auth))

        self.handle = ffi.process_request(self.instance,
                                          auth, len(auth),
                                          resp_input, len(resp_input),
                                          ctypes.byref(output_ptr), ctypes.byref(output_len),
                                          ctypes.byref(status_ptr), ctypes.byref(status_len))

        output_dict: Dict = {}
        status_dict: Dict = {}

        if output_len.value:
            output_dict = json.loads(output_ptr.value[:output_len.value].decode("utf-8"))

        if status_len.value:
            status_dict = json.loads(status_ptr.value[:status_len.value].decode("utf-8"))

        ffi.disposeMemory(ctypes.cast(output_ptr, ctypes.c_void_p))
        ffi.disposeMemory(ctypes.cast(status_ptr, ctypes.c_void_p))

        return output_dict, status_dict

    def process_response(self, resp_body: bytes) -> Dict | None:
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

        output_dict: Dict[str:Any] = {}

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
    get_response: Callable
    path: str = '/graphql'      # default value
    jwt: str = 'authorization'  # authorization header name, jwt expected

    def __init__(self, get_response: Callable):
        # save response processing fn
        self.get_response = get_response

        c = ffi.Config()

        inigo_settings: Dict = {}

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
        else:
            if hasattr(settings, 'GRAPHENE') and settings.GRAPHENE.get('SCHEMA'):
                schema = import_string(settings.GRAPHENE.get('SCHEMA'))

        if schema:
            c.schema = str.encode(str(schema))
            c.introspection = b'{ "data": %s }' % str.encode(str(json.dumps(schema.introspect())))

        if inigo_settings.get('PATH'):
            self.path = inigo_settings.get('PATH')

        if inigo_settings.get('JWT'):
            self.jwt = inigo_settings.get('JWT')

        # create Inigo instance
        self.instance = ffi.create(ctypes.byref(c))
        if self.instance == 0:
            raise Exception('error, instance can not be created')

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # 'path' guard -> /graphql
        if request.path != self.path:
            return self.get_response(request)

        # read request from body
        query: str = ''

        if request.method == 'POST':
            query = json.loads(request.body).get('query')
        elif request.method == 'GET':
            query = request.GET.get('query')

        q = Query(self.instance, query)

        # create inigo context if not present. Should exist before 'get_auth_token' call
        if request.inigo is None:
            request.inigo = InigoContext()

        auth = self.get_auth_token(self.jwt, request)

        # inigo: process request
        output, status = q.process_request(auth)

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

        if response.headers.get('content-type') != 'application/json':
            q.ingest()

            return response

        # inigo: process response
        processed_response = q.process_response(response.content)
        if processed_response:
            return self.respond(processed_response)

        return response

    @staticmethod
    def get_auth_token(header: str, request: HttpRequest) -> str:
        if hasattr(request, 'inigo') and isinstance(request.inigo, InigoContext) is False:
            raise Exception("'inigo' attr is not InigoContext instance")

        # read from request object
        if hasattr(request, 'inigo') and isinstance(request.inigo, InigoContext) and request.inigo.auth:
            return jwt.encode(request.inigo.auth, key=None, algorithm=None)

        # read auth header
        if request.headers.get(header):
            return request.headers.get(header)

    @staticmethod
    def respond(data: Dict) -> JsonResponse:
        response = {
            'data': data.get('data'),
        }

        if data.get('errors'):
            response['errors'] = data.get('errors')

        if data.get('extensions'):
            response['extensions'] = data.get('extensions')

        return JsonResponse(response, status=200)


class InigoContext:
    __auth: Dict | None = None
    __blocked: bool = False

    @property
    def auth(self):
        return self.__auth

    @auth.setter
    def auth(self, value: Dict):
        self.__auth = value

    @property
    def blocked(self):
        return self.__blocked

    def _block(self):
        self.__blocked = True
