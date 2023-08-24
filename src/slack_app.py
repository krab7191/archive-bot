# Dependency imports
import asyncio
from dotenv import load_dotenv
from logging import getLogger, DEBUG, INFO, StreamHandler
from operator import itemgetter
from os import environ
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.errors import SlackApiError

# Local module imports
from utils import fmt_json

# ENV vars
DEFAULT_ENV = {
    'ENV': 'development'
}
load_dotenv()
ENV, SLACK_BOT_TOKEN, SOCKET_TOKEN = itemgetter(
    'ENV', 'SLACK_BOT_TOKEN', 'SOCKET_TOKEN')({**DEFAULT_ENV, **dict(environ)})

# Initialize logger
logger = getLogger("slack_app")
debug_level = DEBUG if ENV == 'development' else INFO
logger.setLevel(debug_level)
logger.addHandler(StreamHandler())

# Init slack app
slack_app = AsyncApp(token=SLACK_BOT_TOKEN)

# Subscribe to events


@slack_app.event("message")
async def event_message(event, ack, say):
    text = event.get('text', '')
    try:
        await ack()
        logger.info(f"Message received: {text or ''}")
        if text:
            await say(text)

    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await say("An error occurred.")


@slack_app.event("app_home_opened")
async def event_home_opened(client, event):
    logger.info("Home opened")
    await client.views_publish(
        user_id=event["user"],
        view={
            "type": "home",
            "callback_id": "home_view",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Welcome to the Archive Bot homepage!"
                    }
                }
            ]
        }
    )


# Functions for Cron
async def get_channels():
    client = slack_app.client
    try:
        # Docs: https://api.slack.com/methods/conversations.list
        res = await client.conversations_list()
        ok = res["ok"]
        if ok:
            channels = res["channels"]
            stripped_channels = []
            for channel in channels:
                stripped_channels.append(
                    {"name": channel["name"], "id": channel["id"]})
            return {"err": None, "channels": stripped_channels}
        else:
            return {"err": res["error"], "channels": None}

    except SlackApiError as e:
        logger.error("Error fetching conversations: {}".format(e))
        return {"err": "{}".format(e), "channels": None}
    
async def get_channel_history(id: str):
    logger.info(id)
    client = slack_app.client
    try:
        # Docs: https://api.slack.com/methods/conversations.history
        res = await client.conversations_history(channel=id)
        ok = res["ok"]
        if ok:
            messages = res["messages"]
            more = res["has_more"]
            logger.info(f"More messages? {more}")
            return {"err": None, "messages": messages}
        else:
            return {"err": res["error"], "messages": None}

    except SlackApiError as e:
        logger.error("Error fetching channel history: {}".format(e))
        return {"err": "{}".format(e), "messages": None}


async def checker():
    res = await get_channels()
    channels = res.get("channels")
    err = res.get("err")
    if not err:
        logger.info(fmt_json(channels))
        first_id = channels[0].get("id", '')
        logger.info(first_id)
        msg_res = await get_channel_history(first_id)
        msg_err = msg_res.get("err")
        if msg_err:
            logger.error(f" -- Error: {msg_err}")
        else:
            logger.info(fmt_json(msg_res))
    else:
        logger.error(err)


# Start the async app
async def start_slack():
    logger.info(
        f"Starting slack app in {'DEV' if ENV=='development' else 'PROD'} mode.")

    handler = AsyncSocketModeHandler(slack_app, SOCKET_TOKEN)
    await handler.start_async()

# Run app in asyncio thread


def init_slack():
    asyncio.run(start_slack())
