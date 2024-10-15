import os
import logging
from telegram.ext import ApplicationBuilder
from handlers import setup_handlers
from dotenv import load_dotenv
import pymongo
from datetime import datetime

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Load environment variables from the .env file, if it exists
load_dotenv()

# Get environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')

# Check if the necessary variables are defined
if not all([TELEGRAM_BOT_TOKEN, MONGO_URI]):
    raise Exception("Please set the environment variables TELEGRAM_BOT_TOKEN and MONGO_URI.")

# Connecting to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client['bot_database']
users_collection = db['users']
settings_collection = db['settings']

async def send_restart_message(application):
    """Sends the message 'Restart completed' if necessary."""
    stored_data = settings_collection.find_one({'key': 'restart_chat_id'})
    if stored_data and 'value' in stored_data:
        restart_chat_id = stored_data['value']
        await application.bot.send_message(chat_id=restart_chat_id, text="Restart has been completed. \nTo continue where you left off, please use the command: /start")
        settings_collection.delete_one({'key': 'restart_chat_id'})  # Removes the record to prevent resending

def main():
    # Create the bot application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(send_restart_message).build()

    # Store the start time in bot_data
    application.bot_data['start_time'] = datetime.now()

    # Set up the handlers
    setup_handlers(application, users_collection, settings_collection)

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
