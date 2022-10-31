from inigo_py import InigoContext


def auth(get_response):
    def middleware(request):

        # example on how to map info your project-specific auth header
        request.inigo = InigoContext()
        request.inigo.auth = {
            'user_name': 'me',
            'user_profile': 'guest',
            'user_roles': [],
        }

        return get_response(request)

    return middleware


def log_inigo_blocked_requests(get_response):
    def middleware(request):

        resp = get_response(request)

        # NOTE! accessing value from 'request' object
        print(f'request is blocked: { request.inigo.blocked }')

        return resp

    return middleware
