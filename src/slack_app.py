# Dependency imports
import asyncio
import time
from dotenv import load_dotenv
from logging import getLogger, DEBUG, INFO, StreamHandler, basicConfig
from operator import itemgetter
from os import environ
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.errors import SlackApiError

# Local module imports
from utils import fmt_json
from db.mongo import save_messages

# Workspace specific variables:
bot_name_Barking_Owl = "U0622JFJ0ES"
bot_name_Triangle_Techsploration = "U05NV3E75S6"

# ENV vars
DEFAULT_ENV = {
    'ENV': 'development'
}
load_dotenv()
ENV, SLACK_BOT_TOKEN, SOCKET_TOKEN, DEV_BOT_TOKEN, DEV_SOCKET_TOKEN = itemgetter(
    'ENV', 'SLACK_BOT_TOKEN', 'SOCKET_TOKEN', 'DEV_BOT_TOKEN', 'DEV_SOCKET_TOKEN')({**DEFAULT_ENV, **dict(environ)})

# Initialize logger
debug_level = DEBUG if ENV == 'development' else INFO
# basicConfig(format='[%(filename)s:%(lineno)d] %(message)s',
            # datefmt='%Y-%m-%d:%H:%M:%S',
            # level=debug_level)
logger = getLogger(__name__)
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


@slack_app.event("app_mention")
async def event_mention(ack, say, event, client):
    try:
        await ack()
        team_name = await get_team_name()
        raw_text = event.get("text", '').strip()
        logger.info(raw_text)
        if raw_text == f"<@{bot_name_Triangle_Techsploration}>" or raw_text == f"<@{bot_name_Barking_Owl}>":
            user = event.get("user")
            await say(f"Hi <@{user}>, how can I help?")

        # Strip bot's ID
        text = raw_text.replace(f"<@{bot_name_Triangle_Techsploration}>", "")
        text = raw_text.replace(f"<@{bot_name_Barking_Owl}>", "")
        text = text.strip().lower()

        if text == "repost":
            await say("Reposting messages in this channel from 89 days ago:")
        # Args
        # elif text.startswith("repost"):
        #     args = text.replace("repost ", "")
        #     await repost(client, event, args, say)
        elif text.startswith("delete"):
            # args = text.replace("delete ", "")
            chan_id = event.get("channel")
            await say("Deleting my messages from the last hour! Sorry!")
            time.sleep(2)
            hist_resp = await get_channel_history(id=chan_id)
            msgs = hist_resp.get("messages")
            if msgs:
                timestamps = []
                for msg in msgs:
                    user = msg.get("user", "")
                    if user == bot_name_Triangle_Techsploration or user == bot_name_Barking_Owl:  # Select bot's own messages
                        timestamps.append(msg["ts"])
                now = time.time()
                hour = 1000 * 60 * 60
                for timestamp in timestamps:
                    if float(timestamp) > now - hour:  # Delete older than 1 hour
                        await del_msg(chan_id=chan_id, msg_ts=timestamp, client=client, say=say)  # noqa: E501
        elif text == "backup channel":
            chan_id = event.get("channel")
            chan_info_res = await client.conversations_info(channel=chan_id)
            if chan_info_res.get("ok"):
                chan_name = chan_info_res["channel"].get("name")
            else:
                chan_name = chan_id
            chan_backup_res = await backup_channel(chan_id, chan_name, team_name, say)
            if chan_backup_res:
                await say("Channel backed up successfully.")
            else:
                await say("Error backing up channel. Please try again.")
        elif text == "full backup":
            chans_backed_up = 0
            await say("Starting full backup of messages in all channels that I'm in...")
            channels_resp = await get_channels()
            err = channels_resp.get("err", None)
            if not err:
                channels = channels_resp.get("channels")
                await say(f"Found {len(channels)} channels, beginning backup...")
                for channel in channels:
                    backup_channel_res = await backup_channel(channel["id"], channel["name"], team_name, say)
                    if backup_channel_res:
                        chans_backed_up += 1
                await say(f"Full backup complete. History from {chans_backed_up} channels backed up.")
            else:
                logger.error(f"Error getting channels in workspace: {err}")

    except Exception as e:
        logger.error(e)
        await say("An error occurred.")


async def get_team_name():
    client = slack_app.client
    team_res = await client.team_info()
    if team_res.get("ok"):
        return team_res.get("team", {}).get("name", '')
    else:
        logger.error("Error occurred while fetching team name...")
        return ''


def filter_messages(m):
    logger.info("filter_messages")
    messages = []
    for message in m:
        text = message.get("text", '')
        sub = message.get("subtype", None)
        if not sub == "channel_join":
            if not sub == "channel_purpose":
                if not text.startswith(f"<@{bot_name_Triangle_Techsploration}>"):
                    if not text.startswith(f"<@{bot_name_Barking_Owl}>"):
                        if not message.get("bot_id", None):
                            messages.append(message)

    return messages


async def backup_channel(chan_id, chan_name, team_name, say):
    logger.info(f"Backing up messages for channel {chan_id}")
    msg_res = await get_channel_history(id=chan_id)
    msg_err = msg_res.get("err", None)
    if msg_err:
        logger.error(f"Error getting channel history: {msg_err}")
    else:
        msgs = msg_res.get("messages", [])
        clean_messages = filter_messages(msgs)
        logger.info("Calling save_messages...")
        save_msgs_res = await save_messages(clean_messages, chan_id, team_name, chan_name)

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


# async def repost(client, event, args, say):
#     # No args; repost all old msgsU05MXQPREJD
#     chan_id = event.get("channel")
#     logger.info("Re-posting old messages: ")
#     logger.info(f"args: {args}")
#     # await say(f"Reposting messages in this channel older than {args} days:")
#     msg_resp = await get_channel_history(id=chan_id)
#     err = msg_resp.get("err")
#     if not err:
#         msg_ids = []
#         msgs = msg_resp.get("messages")
#         logger.info(fmt_json(msgs))
#         for msg in msgs:
#             msg_ids.append(msg["id"])
#         logger.info(msg_ids)


# Functions for Cron
async def get_channels():
    client = slack_app.client
    try:
        # Docs: https://api.slack.com/methods/conversations.list
        res = await client.conversations_list(types=["public_channel", "private_channel"])
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
            meta = res.get("response_metadata", {})
            cursor = meta.get("next_cursor", None)
            while cursor:
                logger.info(f"\nCURSOR: {cursor} \n")
                logger.info(f"More messages? {more}")
                page_res = await client.conversations_history(channel=id, cursor=cursor)
                messages = messages + page_res["messages"]
                cursor = page_res.get("response_metada", {}).get("next_cursor", None)

            return {"err": None, "messages": messages}
        else:
            return {"err": res["error"], "messages": None}

    except SlackApiError as e:
        logger.error("Error fetching channel history: {}".format(e))
        return {"err": "{}".format(e), "messages": None}


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
