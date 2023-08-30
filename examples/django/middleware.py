import json
import random

def log_request(get_response):
    def middleware(request):
        if request.method == 'POST':
            print(json.loads(request.body).get('query'))
        elif request.method == 'GET':
            print(request.GET.get('query'))

        return get_response(request)
    return middleware

def set_random_user_and_client_middleware(get_response):
    def middleware(request):
        request.META['HTTP_User-Id'] = random.choice(["adam", "bob", "carl", "david"])
        request.META['HTTP_Client'] = random.choice(["web", "ios", "android"])

        return get_response(request)

    return middleware