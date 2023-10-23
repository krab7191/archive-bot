# Dependency imports
import aiocron
import asyncio
from dotenv import load_dotenv
from logging import getLogger, DEBUG, INFO, StreamHandler
from os import environ
# from slack_app import checker

# Load env vars
load_dotenv()
ENV = environ.get('ENV')

# Start logger
logger = getLogger("cron")
debug_level = DEBUG if ENV == 'development' else INFO
logger.setLevel(debug_level)
logger.addHandler(StreamHandler())

# Cron that runs every 15 seconds
# @aiocron.crontab('* * * * * 0,15,30,45')
# async def cron():
#     await checker()

# Start event loop that runs cron job
def init_cron():
    asyncio.get_event_loop().run_forever()
