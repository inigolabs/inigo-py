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
    STATIC_URL = 'static/',
    INSTALLED_APPS=[
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.staticfiles',
        'corsheaders',
        'graphene_django'
    ],

    TEMPLATES=[
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        },
    ],

    # configuration of the installed apps
    CORS_ALLOW_ALL_ORIGINS=True,  # Disable host header validation
    GRAPHENE={'SCHEMA': 'schema.schema'},
    INIGO={
        'PATH': '/query',
        'JWT': 'authorization',
        'TOKEN': env('INIGO_SERVICE_TOKEN'),
        'SCHEMA_PATH': './schema.graphql'
    },

    MIDDLEWARE=[
        'corsheaders.middleware.CorsMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',

        # custom middlewares
        'middleware.log_request',
        'middleware.set_random_user_and_client_middleware',

        # make sure inigo middleware is run after any auth middleware
        'inigo_py.django.Middleware',
    ]
)

# needs to be imported after Django is configured as it's trying to access settings
from graphene_django.views import GraphQLView

urlpatterns = [
    path('query', GraphQLView.as_view(graphiql=True)),
]

if __name__ == '__main__':
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
