import asyncio
from dotenv import load_dotenv
from logging import getLogger, DEBUG, INFO, StreamHandler
from operator import itemgetter
from os import environ
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

# ENV vars
DEFAULT_ENV = {
    'ENV': 'development'
}
load_dotenv()
ENV, SLACK_BOT_TOKEN, SOCKET_TOKEN = itemgetter(
    'ENV', 'SLACK_BOT_TOKEN', 'SOCKET_TOKEN')({**DEFAULT_ENV, **dict(environ)})


logger = getLogger("slack_app")
debug_level = DEBUG if ENV == 'development' else INFO
logger.setLevel(debug_level)
logger.addHandler(StreamHandler())

# Init slack app
slack_app = AsyncApp(token=SLACK_BOT_TOKEN)
logger.info(
    f"Starting slack app in {'DEV' if ENV=='development' else 'PROD'} mode.")


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


async def start_slack():
    handler = AsyncSocketModeHandler(slack_app, SOCKET_TOKEN)
    await handler.start_async()


# Start your app
if __name__ == "__main__":
    asyncio.run(start_slack())
