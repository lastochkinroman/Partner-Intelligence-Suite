import asyncio
import re
import os
from datetime import datetime
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.constants import ParseMode

from app.config import settings, logger
from app.database import db_manager
from app.mistral_analyzer import mistral_analyzer
from app.document_generator import document_generator
from app.utils import format_number, validate_inn
from app.commands import start_command, help_command, search_command, stats_command, health_command
from app.handlers import handle_inn_input, handle_callback

INN_INPUT, = range(1)

class BusinessIntelligenceBot:
    def __init__(self):
        self.application = None
        self.setup_handlers()

    def setup_handlers(self):
        self.application = Application.builder().token(settings.telegram_bot_token).build()

        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("stats", stats_command))
        self.application.add_handler(CommandHandler("search", search_command))
        self.application.add_handler(CommandHandler("health", health_command))

        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_inn_input
        ))

        self.application.add_handler(CallbackQueryHandler(handle_callback))

    def run(self):
        logger.info("🤖 Starting Business Intelligence Bot...")

        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

def main():
    try:
        bot = BusinessIntelligenceBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        raise

if __name__ == "__main__":
    main()
