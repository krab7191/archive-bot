# built in imports
from os import environ
from logging import getLogger, DEBUG, INFO, StreamHandler

# Dep imports
from dotenv import load_dotenv
from pymongo import MongoClient

# Local imports
from utils import fmt_json

# Env vars
load_dotenv()
ENV = environ.get("ENV", 'development')
MONGO_PASS = environ.get('MONGO_PASS', None)
mongo_uri = f"mongodb+srv://archive-bot:{MONGO_PASS}@archive-bot.jbpejzs.mongodb.net/?retryWrites=true&w=majority" if ENV == 'production' else 'mongodb://localhost:27017/archive-bot'

# Start logger
logger = getLogger("mongo")
debug_level = DEBUG if ENV == 'development' else INFO
logger.setLevel(debug_level)
logger.addHandler(StreamHandler())

logger.info('Starting mongo client...')
mongo_client = MongoClient(mongo_uri)
db = mongo_client["archive-bot"]
logger.info('Mongo DB connection initialized.')


async def save_messages(messages, chan_id):
    logger.info("save_messages...")
    msgs_inserted = 0
    try:
        for message in messages:
            # Save sub docs first
            user = message.get("user", '')
            team = message.get("team", '')

            logger.info("Setting user id")
            get_user_resp = db.User.find_one({"user_id": user})
            if not get_user_resp:
                user_insert = db.User.insert_one(
                    {"user_id": user}).inserted_id
                message["user"] = user_insert
            else:
                message["user"] = get_user_resp["_id"]

            logger.info("Setting team id")
            get_team_resp = db.Team.find_one({"team_id": team})
            if not get_team_resp:
                team_insert = db.Team.insert_one({"team_id": team}).inserted_id
                message["team"] = team_insert
            else:
                message["team"] = get_team_resp["_id"]

            logger.info("Setting channel id")
            get_channel_resp = db.Channel.find_one({"channel_id": chan_id})
            if not get_channel_resp:
                channel_insert = db.Channel.insert_one({"channel_id": chan_id}).inserted_id
                message["channel"] = channel_insert
            else:
                message["channel"] = get_channel_resp["_id"]

            message["ts"] = float(message["ts"])
            logger.info("Saving message")
            # Get messages with the same timestamp (existing message)
            find_msg_resp = db.Message.find_one({ "ts": message["ts"] })
            if not find_msg_resp:
                message_insert_resp = db.Message.insert_one(message).inserted_id
                logger.info(f"message_insert_resp: {message_insert_resp}")
                msgs_inserted += 1
            else:
                logger.info("Message already exists, skipping")
        logger.info(f"Inserted {msgs_inserted} messages.")
        return msgs_inserted
    except Exception as e:
        logger.error(f"save_messages ERROR: {e}")
        return False