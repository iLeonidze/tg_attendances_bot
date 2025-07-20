"""
Functions to generate Inline Keyboards for the bot interactions.
"""

from typing import List, Set

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import config


def generate_group_selection_keyboard(groups: List[str]) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for selecting a group."""
    keyboard = [
        [InlineKeyboardButton(group_name, callback_data=f"group_select:{group_name}")]
        for group_name in groups
    ]
    return InlineKeyboardMarkup(keyboard)


def generate_attendance_keyboard(
    group_name: str,
    children: List[str],
    present_children: Set[str]
) -> InlineKeyboardMarkup:
    """
    Generates an inline keyboard for marking attendance for a specific group.

    Args:
        group_name: The name of the group.
        children: A list of all children in the group.
        present_children: A set of children currently marked as present today.
    """
    keyboard = []
    for child_name in children:
        is_present = child_name in present_children
        button_text = f"{config.CHECK_MARK_ICON} {child_name}" if is_present else child_name
        callback_data = f"attendance_toggle:{group_name}:{child_name}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    # Add Save and Back buttons
    keyboard.append([
        InlineKeyboardButton("💾 Сохранить", callback_data=f"attendance_save:{group_name}"),
        # InlineKeyboardButton("⬅️ Назад", callback_data="back_to_group_select") # Optional Back button
    ])

    return InlineKeyboardMarkup(keyboard)
