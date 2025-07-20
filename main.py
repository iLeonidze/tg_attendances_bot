"""
Main entry point for the Telegram Attendance Bot.
Initializes the bot, sets up logging, registers handlers, and starts polling.
"""

import logging

from telegram.ext import ApplicationBuilder
from telegram.warnings import PTBUserWarning
import warnings

import config
import handlers

# --- Logging Configuration ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  # Adjust level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
)
# Suppress PTBUserWarning about persistence (we handle persistence manually)
warnings.filterwarnings("ignore", category=PTBUserWarning, message=".*persistence.*")

# Set higher logging level for httpx to avoid verbose DEBUG messages
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main() -> None:
    """Starts the bot."""
    logger.info("Starting bot...")

    try:
        # Validate essential configuration before starting
        config.validate_config()
    except ValueError as e:
        logger.critical(f"Configuration error: {e}")
        return # Stop if config is invalid

    # --- Bot Initialization ---
    # Using ApplicationBuilder for modern PTB setup
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # --- Register Handlers ---
    handlers.register_handlers(application)
    logger.info("Handlers registered successfully.")

    # --- Start the Bot ---
    logger.info("Bot polling started...")
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

    logger.info("Bot stopped.")


if __name__ == '__main__':
    main()
