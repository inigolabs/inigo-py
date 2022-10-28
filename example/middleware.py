def auth(get_response):
    def middleware(request):

        # example on how to map info your project-specific auth header
        request.inigo = {
            'user_name': 'me',
            'user_profile': 'guest',
            'user_roles': [],
        }

        return get_response(request)

    return middleware
