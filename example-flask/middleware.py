import json
from io import BytesIO
from urllib.parse import parse_qs

from inigo_py import InigoContext


class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if environ.get('inigo') is None:
            environ['inigo'] = InigoContext()
            environ['inigo'].auth = {
                'user_name': 'me',
                'user_profile': 'guest',
                'user_roles': ['guest'],
            }

        return self.app(environ, start_response)


class LogMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        request_method = environ['REQUEST_METHOD']
        if request_method == "GET":
            print(parse_qs(environ['QUERY_STRING']).get('query'))
        elif request_method == "POST":
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            body = environ['wsgi.input'].read(content_length)
            payload = json.loads(body)
            if payload and "query" in payload:
                print(payload["query"])
            # reset request body for the nested app
            environ['wsgi.input'] = BytesIO(body)

        return self.app(environ, start_response)


class LogBlockedInigoRequestsMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        response = self.app(environ, start_response)

        if environ.get('inigo') is not None:
            inigo = environ.get('inigo')
            print(f'request is blocked: {inigo.blocked}')

        return response
