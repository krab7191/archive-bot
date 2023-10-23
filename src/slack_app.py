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
from db.mongo import save_messages

# Barking owl bot name: <@U0622JFJ0ES>

# ENV vars
DEFAULT_ENV = {
    'ENV': 'development'
}
load_dotenv()
ENV, SLACK_BOT_TOKEN, SOCKET_TOKEN, DEV_BOT_TOKEN, DEV_SOCKET_TOKEN = itemgetter(
    'ENV', 'SLACK_BOT_TOKEN', 'SOCKET_TOKEN', 'DEV_BOT_TOKEN', 'DEV_SOCKET_TOKEN')({**DEFAULT_ENV, **dict(environ)})

# Initialize logger
logger = getLogger("slack_app")
debug_level = DEBUG if ENV == 'development' else INFO
logger.setLevel(debug_level)
logger.addHandler(StreamHandler())

token = DEV_BOT_TOKEN if ENV == 'production' else SLACK_BOT_TOKEN

# Init slack app
slack_app = AsyncApp(token=token)

# Subscribe to events


@slack_app.event("message")
async def event_message(event, ack, say):
    # text = event.get('text', '')
    try:
        await ack()
        # logger.info(f"Message received: {text or ''}")
        # if text:
        #     await say(text)

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
        logger.info(raw_text)
        if raw_text == "<@U05NV3E75S6>" or raw_text == "<@U0622JFJ0ES>":
            # TODO: No commands, display help message
            user = event.get("user")
            await say(f"Hi <@{user}>, how can I help?")

        # Strip <@U05NV3E75S6> which is bot's ID
        text = raw_text.replace("<@U05NV3E75S6>", "")
        text = raw_text.replace("<@U0622JFJ0ES>", "")
        text = text.strip().lower()

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
                    if user == "U05NV3E75S6" or user == "U0622JFJ0ES":  # Select bot's own messages
                        timestamps.append(msg["ts"])
                now = time.time()
                hour = 1000 * 60 * 60
                for timestamp in timestamps:
                    if float(timestamp) > now - hour:  # Delete older than 1 hour
                        await del_msg(chan_id=chan_id, msg_ts=timestamp, client=client, say=say)  # noqa: E501
        elif text == "backup channel":
            chan_id = event.get("channel")
            chan_backup_res = await backup_channel(chan_id, say)
            if chan_backup_res:
                await say("Channel backed up successfully.")
            else:
                await say("Error backing up channel. Please try again.")
        elif text == "full backup":
            chans_backed_up = 0
            await say("Starting full backup of messages in all channels that I'm in...")
            channels_resp = await get_channels()
            logger.info(fmt_json(channels_resp))
            err = channels_resp.get("err", None)
            if not err:
                channels = channels_resp.get("channels")
                await say(f"Found {len(channels)} channels, beginning backup...")
                for channel in channels:
                    backup_channel_res = await backup_channel(channel["id"], channel["name"], say)
                    if backup_channel_res:
                        chans_backed_up += 1
                await say(f"Full backup complete. History from {chans_backed_up} channels backed up.")
            else:
                logger.error(f"Error getting channels in workspace: {err}")

    except Exception as e:
        logger.error(e)
        await say("An error occurred.")


def filter_messages(m):
    logger.info("filter_messages")
    messages = []
    for message in m:
        if not message.get("subtype", None) == "channel_join":
            if not message.get("subtype", None) == "channel_purpose":
                if not message.get("text", '').startswith("<@U05NV3E75S6>"):
                    if not message.get("text", '').startswith("<@U0622JFJ0ES>"):
                        if not message.get("bot_id", None):
                            messages.append(message)

    return messages


async def backup_channel(chan_id, chan_name, say):
    logger.info(f"Backing up messages for channel {chan_id}")
    msg_res = await get_channel_history(chan_id)
    msg_err = msg_res.get("err", None)
    if msg_err:
        logger.error(f"Error getting channel history: {msg_err}")
    else:
        msgs = msg_res.get("messages", None)
        clean_messages = filter_messages(msgs)
        logger.info("Calling save_messages...")
        save_msgs_res = await save_messages(clean_messages, chan_id, chan_name)

        if save_msgs_res == 0:
            await say(f'Channel history for "{chan_name}" already exists in database. 0 messages saved.')
            return True
        elif not save_msgs_res:
            await say("There was an error backing up channel history. Please try again.")
            return False
        else:
            await say(f"Messages backed up successfully for channel: {chan_name}.")
            return True

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
        res = await client.conversations_list(types=["public_channel","private_channel"])
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

    socket_token = DEV_SOCKET_TOKEN if ENV == 'production' else SOCKET_TOKEN
    handler = AsyncSocketModeHandler(slack_app, socket_token)
    await handler.start_async()

# Run app in asyncio thread


def init_slack():
    asyncio.run(start_slack())
