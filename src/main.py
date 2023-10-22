# built in imports
from os import environ
from logging import getLogger, DEBUG, INFO, StreamHandler
from concurrent import futures
from dotenv import load_dotenv


# Local imports
from slack_app import init_slack
from cron import init_cron

# Env vars
load_dotenv()
ENV = environ.get("ENV", 'development')

# Start logger
logger = getLogger("main")
debug_level = DEBUG if ENV == 'development' else INFO
logger.setLevel(debug_level)
logger.addHandler(StreamHandler())

try:
    import db.mongo
except Exception as e:
    logger.error(f"Error importing mongo connection: {e}")


def main():
    # Start 2 processes to run our cron and slack app in parallel
    with futures.ProcessPoolExecutor(2) as exec:
        # cron = exec.submit(init_cron)
        slack = exec.submit(init_slack)


if __name__ == "__main__":
    main()
