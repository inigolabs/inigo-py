import sys
import environ

from django.conf import settings
from django.urls import path

# Initialise environment variables
env = environ.Env()
environ.Env.read_env()

settings.configure(
    DEBUG=True,
    SECRET_KEY='not-a-real-secret',
    ROOT_URLCONF=__name__,
    INSTALLED_APPS=[
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'corsheaders',
        'graphene_django'
    ],

    # configuration of the installed apps
    CORS_ALLOW_ALL_ORIGINS=True,  # Disable host header validation
    GRAPHENE={'SCHEMA': 'schema.schema'},
    INIGO={
        'PATH': '/query',  # default value: /graphql
        'JWT': 'authorization',  # default value: authorization
        'TOKEN': env('INIGO_SERVICE_TOKEN'),
    },

    MIDDLEWARE=[
        'corsheaders.middleware.CorsMiddleware',

        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',

        'middleware.auth',
        'middleware.log_inigo_blocked_requests',
        'inigo_py.DjangoMiddleware',
    ]
)

# needs to be imported after Django is configured as it's trying to access settings
from graphene_django.views import GraphQLView

urlpatterns = [
    path('query', GraphQLView.as_view(graphiql=False)),
]

if __name__ == '__main__':
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
