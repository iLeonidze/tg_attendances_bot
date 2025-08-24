"""
Telegram bot command and callback query handlers.
"""

import logging
import os
from typing import cast, Dict

from telegram import Update, InputFile
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

import config
import utils
from data_manager import DataManager
import keyboards

logger = logging.getLogger(__name__)

# State for ConversationHandler (for report generation)
ASKING_FOR_DAYS = 1

# --- Initialization ---
# Create a single instance of DataManager to be used across handlers
data_manager = DataManager()

# --- Helper Function ---
async def check_authorization(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Checks if the user is authorized. Sends a message if not."""
    if not utils.check_user_authorization(update.effective_user.id):
        logger.warning("Unauthorized access attempt by user ID: %s", update.effective_user.id)
        if update.effective_message:
            await update.effective_message.reply_text(config.UNAUTHORIZED_MESSAGE)
        return False
    return True

# --- Command Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    if not await check_authorization(update, context):
        return

    user_name = escape_markdown(update.effective_user.first_name)
    welcome_message = (
        f"👋 Привет, {user_name}!\n\n"
        "Я помогу тебе вести учет посещаемости детей.\n\n"
        "*Основные команды:*\n"
        "`/start` - Показать это приветствие\n"
        "`/upload` - Загрузить новый файл Excel с группами и детьми\n"
        "`/mark` - Отметить посещаемость на сегодня\n"
        "`/report` - Выгрузить отчет о посещаемости\n"
        "`/purge_stale` - Удалить данные об отсутствующих группах и детях"
    )
    if update.effective_message:
        await update.effective_message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

async def upload_excel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /upload command, prompting for the file."""
    if not await check_authorization(update, context):
        return
    if update.effective_message:
        await update.effective_message.reply_text(
            "Пожалуйста, отправь мне файл `.xlsx` с данными.\n"
            f"Ожидаемые столбцы: `{config.EXCEL_GROUP_COLUMN}`, `{config.EXCEL_CHILD_COLUMN}`.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_excel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the actual Excel file upload."""
    if not await check_authorization(update, context) or not update.message or not update.message.document:
        return

    document = update.message.document
    if not document.file_name or not document.file_name.lower().endswith('.xlsx'):
        await update.message.reply_text("Пожалуйста, отправь файл в формате `.xlsx`.")
        return

    try:
        file = await context.bot.get_file(document.file_id)
        # Ensure data directory exists before downloading
        utils.ensure_dir_exists(config.DATA_DIR)
        file_path = config.GROUPS_EXCEL_FILE
        await file.download_to_drive(file_path)
        logger.info("Excel file downloaded to %s", file_path)

        # Reload data using DataManager
        success, message = data_manager.load_groups_from_excel(file_path)
        await update.message.reply_text(message)

    except Exception as e:
        logger.exception("Error handling Excel file upload.")
        await update.message.reply_text(f"Произошла ошибка при обработке файла: {e}")


async def mark_attendance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /mark command to start attendance marking."""
    if not await check_authorization(update, context):
        return

    groups = data_manager.get_groups()
    if not groups:
        if update.effective_message:
            await update.effective_message.reply_text(
                "Сначала нужно загрузить список групп. Используй команду /upload."
            )
        return

    keyboard = keyboards.generate_group_selection_keyboard(groups)
    if update.effective_message:
        await update.effective_message.reply_text("Выбери группу для отметки посещаемости сегодня:", reply_markup=keyboard)


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the /report command, starts the conversation for getting N days."""
    if not await check_authorization(update, context):
        return ConversationHandler.END # End conversation if unauthorized

    if not data_manager.groups:
         if update.effective_message:
            await update.effective_message.reply_text(
                "Нет данных о группах для создания отчета. Загрузите Excel файл."
            )
         return ConversationHandler.END

    if not data_manager.attendance:
        if update.effective_message:
            await update.effective_message.reply_text(
                "Нет данных о посещаемости для создания отчета."
            )
        return ConversationHandler.END


    if update.effective_message:
        await update.effective_message.reply_text(
            f"За сколько последних дней нужно сделать отчет? (Максимум {config.MAX_REPORT_DAYS})"
        )
    return ASKING_FOR_DAYS # Transition to the state where we expect the number of days


async def receive_report_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the number of days for the report and generates it."""
    if not await check_authorization(update, context) or not update.message or not update.message.text:
        return ConversationHandler.END # Should not happen in conversation, but safety check

    try:
        days = int(update.message.text.strip())
        if not 0 < days <= config.MAX_REPORT_DAYS:
            await update.message.reply_text(
                f"Пожалуйста, введи число от 1 до {config.MAX_REPORT_DAYS}."
            )
            return ASKING_FOR_DAYS # Stay in the same state to ask again
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи корректное число дней.")
        return ASKING_FOR_DAYS # Stay in the same state

    await update.message.reply_text("Генерирую отчет...")

    report_path = data_manager.generate_attendance_report(days)

    if report_path and os.path.exists(report_path):
        try:
            with open(report_path, 'rb') as report_file:
                 # Use InputFile to send the document correctly
                input_file = InputFile(report_file, filename=os.path.basename(report_path))
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=input_file,
                    caption=f"Отчет о посещаемости за последние {days} дней."
                )
            # Optionally remove the file after sending, or keep it in reports dir
            # os.remove(report_path)
        except FileNotFoundError:
             logger.error("Generated report file not found at %s", report_path)
             await update.message.reply_text("Не удалось найти созданный файл отчета.")
        except Exception as e:
             logger.exception("Failed to send the report file.")
             await update.message.reply_text(f"Не удалось отправить файл отчета. Ошибка: {e}")

    elif report_path is None and data_manager.groups: # Check if report gen failed vs no data
        await update.message.reply_text("Не удалось сгенерировать отчет. Проверь логи.")
    else: # No relevant attendance data was found
         await update.message.reply_text(f"Нет данных о посещаемости за последние {days} дней для генерации отчета.")


    return ConversationHandler.END # End the conversation


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the current operation (like report generation)."""
    if not await check_authorization(update, context):
        return ConversationHandler.END

    if update.effective_message:
        await update.effective_message.reply_text("Операция отменена.")
    return ConversationHandler.END


async def purge_stale_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deletes attendance data for groups/children missing from the current Excel."""
    if not await check_authorization(update, context):
        return

    removed_groups, removed_children = data_manager.purge_stale_entries()
    if update.effective_message:
        if removed_groups or removed_children:
            await update.effective_message.reply_text(
                f"Удалено групп: {removed_groups}, детей: {removed_children}.")
        else:
            await update.effective_message.reply_text("Нет устаревших записей для удаления.")


# --- Callback Query Handlers ---

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles all inline button presses."""
    if not await check_authorization(update, context):
        # Answer callback query to remove the "loading" state on the button
        if update.callback_query:
            await update.callback_query.answer(text=config.UNAUTHORIZED_MESSAGE, show_alert=True)
        return

    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer() # Acknowledge callback

    # --- Callback Data Routing ---
    current_date_str = utils.get_current_date_str()
    parts = query.data.split(":")
    prefix = parts[0]

    try:
        if prefix == "group_select":
            group_index = int(parts[1])
            await handle_group_selection(update, context, group_index, current_date_str)

        elif prefix == "attendance_toggle":
            # Unpack group and child indices safely
            if len(parts) < 3:
                logger.error("Invalid callback data for toggle: %s", query.data)
                return
            group_index = int(parts[1])
            child_index = int(parts[2])
            await handle_toggle_attendance(update, context, group_index, child_index,
                                           current_date_str)

        elif prefix == "attendance_save":
            group_index = int(parts[1])
            await handle_save_attendance(update, context, group_index, current_date_str)

        else:
            logger.warning("Unhandled callback prefix: %s", prefix)
            if query.message:
                await query.edit_message_text(text=f"Неизвестное действие: {query.data}")

    except Exception as e:
        logger.exception("Error processing callback query: %s", query.data)
        if query.message:
            await query.edit_message_text(text=f"Произошла ошибка при обработке запроса: {e}")


async def handle_group_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE, group_index: int, date_str: str
) -> None:
    """Handles selection of a group to mark attendance."""
    query = update.callback_query
    groups = data_manager.get_groups()
    if group_index >= len(groups):
        logger.error("Invalid group index %s", group_index)
        return
    group_name = groups[group_index]

    children = data_manager.get_children_for_group(group_name)
    if not children:
        if query and query.message:
            await query.edit_message_text(text=f"В группе '{group_name}' нет детей согласно последнему файлу Excel.")
        return

    present_children = data_manager.get_attendance_for_day_group(date_str, group_name)
    keyboard = keyboards.generate_attendance_keyboard(group_index, group_name, children, present_children)

    if query and query.message:
        await query.edit_message_text(
            text=f"Отметь присутствующих в группе '{group_name}' на {date_str}:",
            reply_markup=keyboard
        )


async def handle_toggle_attendance(
    update: Update, context: ContextTypes.DEFAULT_TYPE, group_index: int, child_index: int, date_str: str
) -> None:
    """Handles toggling the attendance status of a child."""
    query = update.callback_query

    groups = data_manager.get_groups()
    if group_index >= len(groups):
        logger.error("Invalid group index %s", group_index)
        return
    group_name = groups[group_index]

    children = data_manager.get_children_for_group(group_name)
    if child_index >= len(children):
        logger.error("Invalid child index %s for group %s", child_index, group_name)
        return
    child_name = children[child_index]

    present_children = data_manager.get_attendance_for_day_group(date_str, group_name)

    if child_name in present_children:
        data_manager.unmark_attendance(date_str, group_name, child_name)
        logger.info("User unmarked %s in %s for %s", child_name, group_name, date_str)
    else:
        data_manager.mark_attendance(date_str, group_name, child_name)
        logger.info("User marked %s in %s for %s", child_name, group_name, date_str)

    # Important: Refresh the keyboard with the updated state
    updated_present_children = data_manager.get_attendance_for_day_group(date_str, group_name)
    keyboard = keyboards.generate_attendance_keyboard(group_index, group_name, children, updated_present_children)

    if query and query.message:
        # Avoid errors if the message content hasn't actually changed
        # (though it should have due to the checkmark)
        try:
            await query.edit_message_reply_markup(reply_markup=keyboard)
        except Exception as e:
            logger.warning("Could not edit reply markup (maybe unchanged?): %s", e)


async def handle_save_attendance(
    update: Update, context: ContextTypes.DEFAULT_TYPE, group_index: int, date_str: str
) -> None:
    """Handles saving the attendance for the day."""
    query = update.callback_query
    groups = data_manager.get_groups()
    if group_index >= len(groups):
        logger.error("Invalid group index %s", group_index)
        return
    group_name = groups[group_index]

    if data_manager.save_attendance():
        logger.info("Attendance saved successfully for %s.", date_str)
        if query and query.message:
            # Optionally, provide a way back to group selection or just confirm
            keyboard = keyboards.generate_group_selection_keyboard(groups) # Show groups again
            await query.edit_message_text(
                text=f"✅ Посещаемость для группы '{group_name}' на {date_str} сохранена.\n"
                     f"Можешь выбрать другую группу или использовать /mark снова.",
                reply_markup=keyboard # Or reply_markup=None if you want to end interaction here
            )
    else:
        logger.error("Failed to save attendance for %s.", date_str)
        if query and query.message:
            await query.edit_message_text(text="⚠️ Не удалось сохранить данные о посещаемости.")


# async def handle_back_to_group_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Handles the 'Back' button press to return to group selection."""
#     query = update.callback_query
#     groups = data_manager.get_groups()
#     if not groups:
#         if query and query.message:
#              await query.edit_message_text("Нет доступных групп.")
#         return

#     keyboard = keyboards.generate_group_selection_keyboard(groups)
#     if query and query.message:
#         await query.edit_message_text("Выбери группу для отметки посещаемости сегодня:", reply_markup=keyboard)


# --- Setup Handlers ---

def register_handlers(application) -> None:
    """Registers all handlers with the application."""
    # Basic commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("upload", upload_excel_command))
    application.add_handler(CommandHandler("mark", mark_attendance_command))
    application.add_handler(CommandHandler("purge_stale", purge_stale_command))

    # Conversation handler for report generation
    report_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("report", report_command)],
        states={
            ASKING_FOR_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_days)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    application.add_handler(report_conv_handler)

    # File upload handler (specifically for .xlsx)
    application.add_handler(MessageHandler(filters.Document.FileExtension("xlsx"), handle_excel_upload))

    # Callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Add a handler for unknown commands or text, if desired
    # application.add_handler(MessageHandler(filters.COMMAND | filters.TEXT, unknown_command))
    logger.info("All handlers registered.")
