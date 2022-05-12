from flask import Flask,Response, redirect, url_for
from prometheus_client import Gauge,generate_latest
import boto3
from datetime import datetime, timedelta
import time, os
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging 
from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s: %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

AWS_SERVICES = [""]
logging.basicConfig()

QUERY_PERIOD = os.getenv('QUERY_PERIOD', "1800")
app = Flask(__name__)
app.url_map.strict_slashes = False # Allow for routes with and without trailing slashes
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")

DEBUG = os.getenv("DEBUG", None)
CONTENT_TYPE_LATEST = str('text/plain; version=0.0.4; charset=utf-8')
def __check_credentials(env_name, env_value, is_secret=False):
	if env_value is not None and env_value!="":
		if not is_secret:
			app.logger.info("Using '{}' as '{}'".format(env_value, env_name))
		else:
			app.logger.info("Using '<VALUE_HIDDEN>' as '{}'".format(env_name))

	else:
		app.logger.info("Error: Could not find '{}' in environment. Has it been set?".format(env_name))
		exit(1)
	return env_value

def set_credentials():
    env_keys = ['AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','REGION']
    for key in env_keys:
        value = os.getenv(key, None)
        globals()[key] = value
        __check_credentials(key, value, False)

    return AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,REGION


def get_flask_app():
    return app

@app.route('/')
def index():
    return redirect(url_for('metrics'))

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route('/health')
def health():
    return "Ready"

def initialize_scheduler(scheduler, aws_cost_exporter):
    scheduler.start()
    scheduler.add_job(
        func=aws_cost_exporter.aws_query,
        trigger=IntervalTrigger(seconds=int(QUERY_PERIOD),start_date=(datetime.now() + timedelta(seconds=5))),
        id='aws_query',
        name='Run AWS Query',
        replace_existing=True
        )  
    if DEBUG: 
        app.logger.info("DEBUG IS SET, so sleeping forever")
        while True: time.sleep(1)

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    # Check and set AWS credentials
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,REGION = set_credentials()

    # Setup AWS cost exporter
    aws_cost_exporter = None

    # Setup flask server
    app.run(host=HOST, port=PORT)
    # Initialize scheduler task
    #scheduler = BackgroundScheduler()
    #initialize_scheduler(scheduler, aws_cost_exporter)

