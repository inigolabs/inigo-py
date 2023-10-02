import ctypes
import json
import os
import platform
import re

from django.conf import settings
from django.http import JsonResponse
from django.http import HttpResponse
from django.utils.module_loading import import_string

from inigo_py import ffi, Query

class Middleware:
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
        c.disable_response_data = False
        c.name = str.encode('inigo-py : django')
        c.runtime = str.encode('python' + re.search(r'\d+\.\d+', platform.sys.version).group(0))

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
        return HttpResponse(q.process_response(response.content), status=200, content_type='application/json')

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
