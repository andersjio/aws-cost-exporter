from flask import Flask,Response
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
logging.getLogger('apscheduler').setLevel(logging.INFO)
QUERY_PERIOD = os.getenv('QUERY_PERIOD', "1800")

app = Flask(__name__)
DEBUG = os.getenv("DEBUG", None)
CONTENT_TYPE_LATEST = str('text/plain; version=0.0.4; charset=utf-8')
def check_credentials(env_name, env_value, is_secret=False):
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
	key_name = 'AWS_ACCESS_KEY_ID'
	AWS_ACCESS_KEY_ID = os.getenv(key_name, None)
	check_credentials(key_name, AWS_ACCESS_KEY_ID, False)

	key_name = 'AWS_SECRET_ACCESS_KEY'
	AWS_SECRET_ACCESS_KEY = os.getenv(key_name, None)
	check_credentials(key_name, AWS_SECRET_ACCESS_KEY, True)

	key_name = 'REGION'
	REGION = os.getenv(key_name, None)
	check_credentials(key_name, REGION, False)

	return AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,REGION


if os.environ.get('METRIC_TODAY_DAILY_COSTS') is not None:
    g_cost = Gauge('aws_today_daily_costs', 'Today daily costs from AWS')
if os.environ.get('METRIC_YESTERDAY_DAILY_COSTS') is not None:
    g_yesterday = Gauge('aws_yesterday_daily_costs', 'Yesterday daily costs from AWS')
if os.environ.get('METRIC_TODAY_DAILY_USAGE') is not None:
    g_usage = Gauge('aws_today_daily_usage', 'Today daily usage from AWS')
if os.environ.get('METRIC_TODAY_DAILY_USAGE_NORM') is not None:
    g_usage_norm = Gauge('aws_today_daily_usage_norm', 'Today daily usage normalized from AWS')

scheduler = BackgroundScheduler()
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,REGION = set_credentials()
client = boto3.client('ce', 
                aws_access_key_id=AWS_ACCESS_KEY_ID, 
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY, 
                region_name=REGION
                )

def aws_query():
    app.logger.info("Calculating costs...")
    now = datetime.now()
    yesterday = datetime.today() - timedelta(days=1)
    two_days_ago = datetime.today() - timedelta(days=2)
    if os.environ.get('METRIC_TODAY_DAILY_COSTS') is not None:

        r = client.get_cost_and_usage(
            TimePeriod={
                'Start': yesterday.strftime("%Y-%m-%d"),
                'End':  now.strftime("%Y-%m-%d")
            },
            Granularity="DAILY",
            Metrics=["BlendedCost"]
        )
        cost = r["ResultsByTime"][0]["Total"]["BlendedCost"]["Amount"]
        app.logger.info("Updated AWS Daily costs: %s" %(cost))
        g_cost.set(float(cost))

    if os.environ.get('METRIC_YESTERDAY_DAILY_COSTS') is not None:
        r = client.get_cost_and_usage(
            TimePeriod={
                'Start': two_days_ago.strftime("%Y-%m-%d"),
                'End':  yesterday.strftime("%Y-%m-%d")
            },
            Granularity="DAILY",
            Metrics=["BlendedCost"],
            Filter={
                "And": [{
                    "Dimensions": {
                        "Key": "SERVICE",
                        "Values": [
                            "Amazon Elastic Compute Cloud - Compute"
                        ]
                    }
                }, {
                    "Not": {
                        "Dimensions": {
                            "Key": "RECORD_TYPE",
                            "Values": ["Refund", "Credit"]
                        }
                    }
                }]
            }
        )
        cost_yesterday = r["ResultsByTime"][0]["Total"]["BlendedCost"]["Amount"]
        app.logger.info("Yesterday's AWS Daily costs: %s" %(cost_yesterday))
        g_yesterday.set(float(cost_yesterday))


    if os.environ.get('METRIC_TODAY_DAILY_USAGE') is not None:
        r = client.get_cost_and_usage(
            TimePeriod={
                'Start': yesterday.strftime("%Y-%m-%d"),
                'End':  now.strftime("%Y-%m-%d")
            },
            Granularity="DAILY",
            Metrics=["UsageQuantity"]
        )
        usage = r["ResultsByTime"][0]["Total"]["UsageQuantity"]["Amount"]
        app.logger.info("Updated AWS Daily Usage: %s" %(usage))
        g_usage.set(float(usage))

    if os.environ.get('METRIC_TODAY_DAILY_USAGE_NORM') is not None:

        r = client.get_cost_and_usage(
            TimePeriod={
                'Start': yesterday.strftime("%Y-%m-%d"),
                'End':  now.strftime("%Y-%m-%d")
            },
            Granularity="DAILY",
            Metrics=["NormalizedUsageAmount"]
        )
        usage_norm = r["ResultsByTime"][0]["Total"]["NormalizedUsageAmount"]["Amount"]
        app.logger.info("Updated AWS Daily Usage Norm: %s" %(usage_norm))
        g_usage_norm.set(float(usage_norm))

    app.logger.info("Finished calculating costs")

    return 0


@app.route('/metrics/')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route('/health')
def health():
    return "Ready"


scheduler.start()
scheduler.add_job(
    func=aws_query,
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