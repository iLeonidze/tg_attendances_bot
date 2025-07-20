"""
Configuration settings for the Telegram bot.
Store sensitive information like BOT_TOKEN and ALLOWED_USER_ID here.
For production, consider using environment variables instead of hardcoding.
"""

import os

# --- Basic Configuration ---

# You can get this from BotFather on Telegram
BOT_TOKEN: str = os.getenv("BOT_TOKEN")

env_user_ids = os.getenv("ALLOWED_USER_IDS")
if env_user_ids:
    # Parse comma-separated string from environment variable
    try:
        ALLOWED_USER_IDS: list[int] = [int(uid.strip()) for uid in env_user_ids.split(',')]
    except ValueError:
        raise ValueError("Invalid format for ALLOWED_USER_IDS in environment. Must be comma-separated integers.")
else:
    # Default value if not set in environment
    ALLOWED_USER_IDS: list[int] = []

# --- File Paths ---
# Ensure these paths are relative to the project root or use absolute paths
# The 'data' directory will store persistent data.
DATA_DIR: str = "data"
GROUPS_EXCEL_FILE: str = os.path.join(DATA_DIR, "groups.xlsx")
ATTENDANCE_JSON_FILE: str = os.path.join(DATA_DIR, "attendance.json")
REPORTS_DIR: str = os.path.join(DATA_DIR, "reports") # Directory for generated reports

# --- Error Handling ---
# Message sent to unauthorized users
UNAUTHORIZED_MESSAGE: str = "Извините, этот бот предназначен только для авторизованных пользователей."

# --- Input Validation ---
MAX_REPORT_DAYS: int = 365 # Maximum number of days for the report

# --- Excel Structure ---
# Define the expected column names in the uploaded Excel file
EXCEL_GROUP_COLUMN: str = "Группа"
EXCEL_CHILD_COLUMN: str = "Имя Ребенка"

# --- Emojis ---
CHECK_MARK_ICON: str = "✅"


def validate_config() -> None:
    """Validates the essential configuration settings."""
    if BOT_TOKEN == "YOUR_BOT_TOKEN":
        raise ValueError("Bot token is not set in config.py or environment variables.")
    if not ALLOWED_USER_IDS:
        raise ValueError("Allowed user IDs list is empty in config.py or environment variables.")
    print(f"Configuration loaded. Allowed user IDs: {ALLOWED_USER_IDS}")
