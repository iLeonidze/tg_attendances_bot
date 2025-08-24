"""
Functions to generate Inline Keyboards for the bot interactions.
"""

from typing import List, Set

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import config


def generate_group_selection_keyboard(groups: List[str]) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for selecting a group.

    The callback data uses the group's index instead of its name to
    keep the payload short (Telegram limits callback data to 64 bytes).
    """
    keyboard = [
        [InlineKeyboardButton(group_name, callback_data=f"group_select:{idx}")]
        for idx, group_name in enumerate(groups)
    ]
    return InlineKeyboardMarkup(keyboard)


def generate_attendance_keyboard(
    group_index: int,
    group_name: str,
    children: List[str],
    present_children: Set[str]
) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for marking attendance for a specific group.

    Args:
        group_index: Index of the group in the sorted list of groups.
        group_name: The name of the group.
        children: A list of all children in the group.
        present_children: A set of children currently marked as present today.
    """
    keyboard = []
    for child_index, child_name in enumerate(children):
        is_present = child_name in present_children
        button_text = f"{config.CHECK_MARK_ICON} {child_name}" if is_present else child_name
        # Use indices for callback data to avoid exceeding Telegram's 64-byte limit
        callback_data = f"attendance_toggle:{group_index}:{child_index}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    # Add Save button
    keyboard.append([
        InlineKeyboardButton("💾 Сохранить", callback_data=f"attendance_save:{group_index}"),
        # InlineKeyboardButton("⬅️ Назад", callback_data="back_to_group_select") # Optional Back button
    ])

    return InlineKeyboardMarkup(keyboard)
