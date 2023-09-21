# Dependency imports
import asyncio
import time
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

# Example event from app_mention
# {
#   "client_msg_id": "b9cd5c0b-0d2f-4b08-9faa-fa76c80408a6",
#   "type": "app_mention",
#   "text": "<@U05NV3E75S6> repost 90",
#   "user": "U05MXQPREJD",
#   "ts": "1693007756.663679",
#   "blocks": [
#     {
#       "type": "rich_text",
#       "block_id": "+FMW=",
#       "elements": [
#         {
#           "type": "rich_text_section",
#           "elements": [
#             {
#               "type": "user",
#               "user_id": "U05NV3E75S6"
#             },
#             {
#               "type": "text",
#               "text": " repost 90"
#             }
#           ]
#         }
#       ]
#     }
#   ],
#   "team": "T05MK5U6CFL",
#   "channel": "C05NNEZV4P8",
#   "event_ts": "1693007756.663679"
# }


@slack_app.event("app_mention")
async def event_mention(ack, say, event, client):
    try:
        await ack()
        raw_text = event.get("text", "<@U05NV3E75S6>").strip()
        if raw_text == "<@U05NV3E75S6>":
            # TODO: No commands, display help message
            user = event.get("user")
            await say(f"Hi <@{user}>, how can I help?")

        # Strip <@U05NV3E75S6> which is bot's ID
        text = raw_text.replace("<@U05NV3E75S6>", "").strip().lower()
        logger.info(text)
        if text == "repost":
            await say("Reposting messages in this channel from 89 days ago:")
        # Args
        elif text.startswith("repost"):
            args = text.replace("repost ", "")
            await repost(client, event, args, say)
        elif text.startswith("delete"):
            args = text.replace("delete ", "")
            chan_id = event.get("channel")
            await say("Deleting my messages from the last hour! Sorry!")
            time.sleep(2)
            hist_resp = await get_channel_history(chan_id)
            msgs = hist_resp.get("messages")
            if msgs:
                timestamps = []
                for msg in msgs:
                    user = msg.get("user", "")
                    if user == "U05NV3E75S6":  # Select bot's own messages
                        timestamps.append(msg["ts"])
                now = time.time()
                hour = 1000 * 60 * 60
                for timestamp in timestamps:
                    if float(timestamp) > now - hour:  # Delete older than 1 hour
                        await del_msg(chan_id=chan_id, msg_ts=timestamp, client=client, say=say)  # noqa: E501

    except Exception as e:
        logger.error(e)
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

# Repost function
async def repost(client, event, args, say):
    # No args; repost all old msgsU05MXQPREJD
    chan_id = event.get("channel")
    logger.info("Re-posting old messages: ")
    logger.info(f"args: {args}")
    # await say(f"Reposting messages in this channel older than {args} days:")
    msg_resp = await get_channel_history(id=chan_id)
    err = msg_resp.get("err")
    if not err:
        msg_ids = []
        msgs = msg_resp.get("messages")
        logger.info(fmt_json(msgs))
        for msg in msgs:
            msg_ids.append(msg["id"])
        logger.info(msg_ids)


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

# Delete messages... Useful for testing + debugging to not clutter space
async def del_msg(chan_id, msg_ts, client, say):
    try:
        logger.info(f"Deleting message with TS: {msg_ts}")
        await client.chat_delete(channel=chan_id, ts=msg_ts)

    except Exception as e:
        logger.error(e)


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
