import ctypes
import json
import os
import sys
import platform
import re

from importlib import import_module
from io import BytesIO
from urllib.parse import parse_qs

from werkzeug.datastructures import EnvironHeaders

from inigo_py import ffi, Query

class Middleware:
    def __init__(self, app):
        self.app = app.wsgi_app

        self.instance = 0

        if ffi.library is None:
            # library is not found, skip middleware initialization
            return

        # default values
        self.path = '/graphql'

        c = ffi.Config()
        c.disable_response_data = False
        c.name = str.encode('inigo-py : flask')
        c.runtime = str.encode('python' + re.search(r'\d+\.\d+', platform.sys.version).group(0))

        inigo_settings = {}
        if 'INIGO' in app.config:
            inigo_settings = app.config.get('INIGO')

        if inigo_settings.get('ENABLE') is False:
            return

        # process Inigo settings
        if inigo_settings.get('DEBUG'):
            c.debug = inigo_settings.get('DEBUG')
        else:
            # use regular DEBUG setting if specific is not provided
            if 'DEBUG' in app.config:
                c.debug = app.config.get('DEBUG')

        if inigo_settings.get('TOKEN'):
            c.token = str.encode(inigo_settings.get('TOKEN'))

        schema = None
        if inigo_settings.get('GRAPHENE_SCHEMA'):
            schema = import_string(inigo_settings.get('GRAPHENE_SCHEMA'))
        elif inigo_settings.get('SCHEMA_PATH'):
            if os.path.isfile(inigo_settings.get('SCHEMA_PATH')):
                with open(inigo_settings.get('SCHEMA_PATH'), 'r') as f:
                    schema = f.read()
        elif 'GRAPHENE' in app.config and app.config.get('GRAPHENE').get('SCHEMA'):
            schema = import_string(app.config.get('GRAPHENE').get('SCHEMA'))

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

    def __call__(self, environ, start_response):
        # ignore execution if Inigo is not initialized
        if self.instance == 0:
            return self.app(environ, start_response)

        # 'path' guard -> /graphql
        if environ['PATH_INFO'] != self.path:
            return self.app(environ, start_response)

        request_method = environ['REQUEST_METHOD']

        # graphiql request
        if request_method == 'GET' and ("text/html" in environ.get('HTTP_ACCEPT', '*/*')):
            return self.app(environ, start_response)

        # support only POST and GET requests
        if request_method != 'POST' and request_method != 'GET':
            return self.app(environ, start_response)

        # parse request
        g_req: bytes = b''
        if request_method == "POST":

            # Get the request body from the environ as reading from global request object caches it.
            if environ.get('wsgi.input'):
                content_length = environ.get('CONTENT_LENGTH')
                if content_length == '-1':
                    g_req = environ.get('wsgi.input').read(-1)
                else:
                    g_req = environ.get('wsgi.input').read(int(content_length))
                # reset request body for the nested app
                environ['wsgi.input'] = BytesIO(g_req)
        elif request_method == "GET":
            # Returns a dictionary in which the values are lists
            query_params = parse_qs(environ['QUERY_STRING'])
            data = {
                'query': query_params.get('query', [''])[0],
                'operationName': query_params.get('operationName', [''])[0],
                'variables': query_params.get('variables', [''])[0],
            }
            g_req = str.encode(json.dumps(data))

        q = Query(self.instance, g_req)

        headers = dict(EnvironHeaders(environ).to_wsgi_list())

        # inigo: process request
        resp, req = q.process_request(self.headers(headers))

        # introspection query
        if resp:
            return self.respond(resp, start_response)

        # modify query if required
        if req:
            if request_method == 'GET':
                query_params = parse_qs(environ['QUERY_STRING'])
                query_params['query'] = req.get('query')
                environ['QUERY_STRING'] = '&'.join([f"{k}={v[0]}" for k, v in query_params.items()])
            elif request_method == 'POST':
                content_length = int(environ.get('CONTENT_LENGTH', 0))
                body = environ['wsgi.input'].read(content_length)
                try:
                    payload = json.loads(body)
                except ValueError:
                    payload = {}
                payload.update({
                    'query': req.get('query'),
                    'operationName': req.get('operationName'),
                    'variables': req.get('variables'),
                })
                payload_str = json.dumps(payload).encode('utf-8')
                environ['wsgi.input'] = BytesIO(payload_str)
                environ['CONTENT_LENGTH'] = str(len(payload_str))

        inner_status = None
        inner_headers = []
        inner_exc_info = None

        def start_response_collector(status, headers, exc_info=None):
            # Just collects the inner response headers, to be modified before sending to client
            nonlocal inner_status, inner_headers, inner_exc_info
            inner_status = status
            inner_headers = headers
            inner_exc_info = exc_info
            # Not calling start_response(), as we will modify the headers first.
            return None

        # forward to request handler
        # populates the inner_* vars, as triggers inner call of the collector closure
        response = self.app(environ, start_response_collector)

        # inigo: process response
        response = [q.process_response(b"".join(response))]
        # removes Content-Length from original headers
        inner_headers = [(key, value) for key, value in inner_headers if key != 'Content-Length']
        start_response(inner_status, inner_headers, inner_exc_info)
        return response

    @staticmethod
    def headers(headers_dict):
        headers = {}
        for key, value in headers_dict.items():
            headers[key] = value.split(", ")

        return str.encode(json.dumps(headers))

    @staticmethod
    def respond(data, start_response):
        response = {
            'data': data.get('data'),
        }

        if data.get('errors'):
            response['errors'] = data.get('errors')

        if data.get('extensions'):
            response['extensions'] = data.get('extensions')

        status = "200 OK"
        headers = [("Content-type", "application/json")]
        start_response(status, headers)

        return [json.dumps(response).encode("utf-8")]


def cached_import(module_path, class_name):
    # Check whether module is loaded and fully initialized.
    if not (
            (module := sys.modules.get(module_path))
            and (spec := getattr(module, "__spec__", None))
            and getattr(spec, "_initializing", False) is False
    ):
        module = import_module(module_path)
    return getattr(module, class_name)


def import_string(dotted_path):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    try:
        return cached_import(module_path, class_name)
    except AttributeError as err:
        raise ImportError(
            'Module "%s" does not define a "%s" attribute/class'
            % (module_path, class_name)
        ) from err
