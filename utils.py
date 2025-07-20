"""
Utility functions for the Telegram bot.
"""

import datetime
import os
from typing import Optional

import config


def get_current_date_str() -> str:
    """Returns the current date as a string in YYYY-MM-DD format."""
    return datetime.date.today().isoformat()


def ensure_dir_exists(dir_path: str) -> None:
    """Ensures that a directory exists, creating it if necessary."""
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            print(f"Created directory: {dir_path}")
        except OSError as e:
            print(f"Error creating directory {dir_path}: {e}")
            raise # Re-raise the exception if directory creation fails


def check_user_authorization(user_id: Optional[int]) -> bool:
    """Checks if the user ID matches the allowed user ID."""
    if not user_id:
        return False
    return user_id in config.ALLOWED_USER_IDS
