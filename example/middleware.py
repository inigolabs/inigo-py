import json


def log_request(get_response):
    def middleware(request):

        if request.method == 'POST':
            print(json.loads(request.body).get('query'))
        elif request.method == 'GET':
            print(request.GET.get('query'))

        return get_response(request)
    return middleware
