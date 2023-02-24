import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from inigo_py import FlaskMiddleware
from middleware import LogBlockedInigoRequestsMiddleware, LogMiddleware, AuthMiddleware

app = Flask(__name__)

# Load the configuration variables from the .env file
load_dotenv()

config = {
    'DEBUG': True,
    'SECRET_KEY': 'mysecretkey',
    'ROOT_URLCONF': __name__,
    'STATIC_URL': 'static/',

    # configuration of the installed apps
    'GRAPHENE': {'SCHEMA': 'schema.schema'},
    'CORS_ALLOW_ALL_ORIGINS': True,  # Disable host header validation
    'INIGO': {
        'PATH': '/query',
        'TOKEN': os.environ.get('INIGO_SERVICE_TOKEN', ''),
        'SCHEMA_PATH': './schema.graphql'
    },
}

app.config.update(config)

# add the CORS middleware
CORS(app)

app.wsgi_app = AuthMiddleware(app.wsgi_app)
app.wsgi_app = FlaskMiddleware(app)
app.wsgi_app = LogMiddleware(app.wsgi_app)
app.wsgi_app = LogBlockedInigoRequestsMiddleware(app.wsgi_app)

# needs to be imported after Flask is configured as it's trying to access settings
from graphql_server.flask import GraphQLView
from schema import schema

app.add_url_rule(
    '/query',
    view_func=GraphQLView.as_view(
        'graphql',
        schema=schema,
        graphiql=True,
    )
)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80, use_reloader=False)
