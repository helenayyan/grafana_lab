from flask import Blueprint, Flask
from prometheus_client import make_wsgi_app, Counter
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

from flask_prometheus_metrics import register_metrics

#
# Constants
#

CONFIG = {"version": "v0.1.2", "config": "staging"}
MAIN = Blueprint("main", __name__)

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method'])

#
# Main app
#


@MAIN.route("/")
def index():
       REQUEST_COUNT.labels(method='GET').inc()
       return "This is the main page."


@MAIN.route("/banana")
def banana():
       REQUEST_COUNT.labels(method='GET').inc()
       return "A banana is an elongated, edible fruit – botanically a berry – produced by several kinds of large herbaceous flowering plants in the genus Musa."


@MAIN.route("/apple")
def apple():
       REQUEST_COUNT.labels(method='GET').inc()
       return "An apple is an edible fruit produced by an apple tree (Malus domestica). Apple trees are cultivated worldwide and are the most widely grown species in the genus Malus."


@MAIN.route("/dragonfruit")
def dragonfruit():
       REQUEST_COUNT.labels(method='GET').inc()
       return "A pitaya (/pɪˈtaɪ.ə/) or pitahaya (/ˌpɪtəˈhaɪ.ə/) is the fruit of several different cactus species indigenous to the Americas. Pitaya usually refers to fruit of the genus Stenocereus, while pitahaya or dragon fruit refers to fruit of the genus Hylocereus, both in the family Cactaceae."


def register_blueprints(app):
       """
       Register blueprints to the app
       """
       app.register_blueprint(MAIN)


def create_app(config):
       """
       Application factory
       """
       app = Flask(__name__)

       register_blueprints(app)
       register_metrics(app, app_version=config["version"], app_config=config["config"])
       return app


#
# Dispatcher
#


def create_dispatcher() -> DispatcherMiddleware:
       """
       App factory for dispatcher middleware managing multiple WSGI apps
       """
       main_app = create_app(config=CONFIG)
       return DispatcherMiddleware(main_app.wsgi_app, {"/metrics": make_wsgi_app()})


#
# Run
#

if __name__ == "__main__":
       run_simple(
       "0.0.0.0",
       8000,
       create_dispatcher(),
       use_reloader=True,
       use_debugger=True,
       use_evalex=True,
       )