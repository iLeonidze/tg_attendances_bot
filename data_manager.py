# data_manager.py
"""
Manages loading, saving, and accessing group and attendance data.
Uses Excel for group definitions and JSON for attendance records.
"""

import json
import logging
import os
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Set, Optional, Tuple

import pandas as pd

import config
import utils

logger = logging.getLogger(__name__)

# Type alias for attendance data: { 'YYYY-MM-DD': {'Group Name': {'Child1', 'Child2'}} }
AttendanceData = Dict[str, Dict[str, Set[str]]]
# Type alias for group data: { 'Group Name': ['Child1', 'Child2'] }
GroupData = Dict[str, List[str]]


class DataManager:
    """Handles all data operations for groups and attendance."""

    def __init__(self) -> None:
        """Initializes the DataManager, ensuring data directories exist."""
        self.groups: GroupData = {}
        self.attendance: AttendanceData = defaultdict(lambda: defaultdict(set))
        self._ensure_data_files_exist()
        self.load_groups_from_excel()
        self.load_attendance()

    def _ensure_data_files_exist(self) -> None:
        """Creates data directories and initial empty files if they don't exist."""
        utils.ensure_dir_exists(config.DATA_DIR)
        utils.ensure_dir_exists(config.REPORTS_DIR)
        # No need to create empty files explicitly for load methods;
        # they handle FileNotFoundError.

    def load_groups_from_excel(self, file_path: str = config.GROUPS_EXCEL_FILE) -> Tuple[bool, str]:
        """
        Loads group and child data from the specified Excel file.
        Expected columns: defined in config (e.g., "Группа", "Имя Ребенка").
        Overwrites existing group data.

        Args:
            file_path: Path to the Excel file. Defaults to config.GROUPS_EXCEL_FILE.

        Returns:
            Tuple[bool, str]: (success_status, message)
        """
        if not os.path.exists(file_path):
            logger.warning("Groups Excel file not found at %s. No groups loaded.", file_path)
            self.groups = {} # Ensure groups are empty if file is missing
            return True, "Файл с группами еще не загружен." # Not an error, just state

        try:
            df = pd.read_excel(file_path, engine='openpyxl')

            # Validate columns
            if config.EXCEL_GROUP_COLUMN not in df.columns or \
               config.EXCEL_CHILD_COLUMN not in df.columns:
                msg = (f"Ошибка: Excel файл должен содержать столбцы "
                       f"'{config.EXCEL_GROUP_COLUMN}' и '{config.EXCEL_CHILD_COLUMN}'.")
                logger.error(msg)
                return False, msg

            # Check for empty required columns
            if df[config.EXCEL_GROUP_COLUMN].isnull().any() or \
               df[config.EXCEL_CHILD_COLUMN].isnull().any():
                 msg = "Ошибка: В файле Excel есть пустые ячейки в столбцах групп или имен."
                 logger.error(msg)
                 return False, msg


            new_groups: GroupData = defaultdict(list)
            for _, row in df.iterrows():
                group_name = str(row[config.EXCEL_GROUP_COLUMN]).strip()
                child_name = str(row[config.EXCEL_CHILD_COLUMN]).strip()
                if group_name and child_name: # Ensure names are not empty after stripping
                    new_groups[group_name].append(child_name)

            # Sort children within each group alphabetically
            for group in new_groups:
                new_groups[group].sort()

            self.groups = dict(new_groups)
            logger.info("Successfully loaded groups from %s. Found %d groups.",
                        file_path, len(self.groups))
            return True, f"Группы успешно загружены/обновлены из файла. Найдено групп: {len(self.groups)}."

        except FileNotFoundError:
            logger.warning("Groups Excel file not found at %s during load attempt.", file_path)
            self.groups = {}
            return True, "Файл с группами еще не загружен."
        except ImportError:
            msg = "Ошибка: Необходима библиотека 'openpyxl'. Установите ее: pip install openpyxl"
            logger.exception(msg)
            return False, msg
        except Exception as e:
            logger.exception("Failed to load groups from Excel file %s.", file_path)
            return False, f"Не удалось прочитать Excel файл. Ошибка: {e}"

    def load_attendance(self) -> None:
        """Loads attendance data from the JSON file."""
        try:
            with open(config.ATTENDANCE_JSON_FILE, 'r', encoding='utf-8') as f:
                # Load and convert lists back to sets
                loaded_data = json.load(f)
                self.attendance = defaultdict(lambda: defaultdict(set))
                for date_str, groups_attendance in loaded_data.items():
                    for group_name, children_list in groups_attendance.items():
                        self.attendance[date_str][group_name] = set(children_list)
            logger.info("Attendance data loaded successfully from %s", config.ATTENDANCE_JSON_FILE)
        except FileNotFoundError:
            logger.warning("Attendance JSON file not found (%s). Starting with empty attendance.",
                           config.ATTENDANCE_JSON_FILE)
            self.attendance = defaultdict(lambda: defaultdict(set))
        except json.JSONDecodeError:
            logger.exception("Error decoding attendance JSON file %s. Data might be corrupted.",
                             config.ATTENDANCE_JSON_FILE)
            # Decide on recovery strategy: backup, start fresh, etc.
            # For now, start fresh to avoid crashing.
            self.attendance = defaultdict(lambda: defaultdict(set))
        except Exception as e:
            logger.exception("An unexpected error occurred while loading attendance data.")
            self.attendance = defaultdict(lambda: defaultdict(set)) # Start fresh on other errors

    def save_attendance(self) -> bool:
        """Saves the current attendance data to the JSON file."""
        try:
            # Convert sets to lists for JSON serialization
            serializable_attendance = defaultdict(lambda: defaultdict(list))
            for date_str, groups_attendance in self.attendance.items():
                for group_name, children_set in groups_attendance.items():
                    serializable_attendance[date_str][group_name] = sorted(list(children_set)) # Sort for consistency

            with open(config.ATTENDANCE_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(serializable_attendance, f, ensure_ascii=False, indent=4)
            logger.info("Attendance data saved successfully to %s", config.ATTENDANCE_JSON_FILE)
            return True
        except IOError as e:
            logger.exception("Error writing attendance data to %s", config.ATTENDANCE_JSON_FILE)
            return False
        except Exception as e:
            logger.exception("An unexpected error occurred while saving attendance data.")
            return False

    def get_groups(self) -> List[str]:
        """Returns a sorted list of group names."""
        return sorted(self.groups.keys())

    def get_children_for_group(self, group_name: str) -> List[str]:
        """Returns a list of children for a specific group."""
        return self.groups.get(group_name, [])

    def get_attendance_for_day_group(self, date_str: str, group_name: str) -> Set[str]:
        """
        Returns the set of present children for a specific group on a specific date.
        Returns an empty set if no data exists for that date/group.
        """
        return self.attendance.get(date_str, {}).get(group_name, set())

    def mark_attendance(self, date_str: str, group_name: str, child_name: str) -> None:
        """Marks a child as present for a specific group on a specific date."""
        if group_name not in self.groups or child_name not in self.groups[group_name]:
             logger.warning("Attempted to mark attendance for unknown group/child: %s / %s",
                            group_name, child_name)
             return # Or raise an error? Silently failing for now.

        # Ensure the date entry exists
        if date_str not in self.attendance:
            self.attendance[date_str] = defaultdict(set)
        # Ensure the group entry exists for the date
        if group_name not in self.attendance[date_str]:
             self.attendance[date_str][group_name] = set()

        self.attendance[date_str][group_name].add(child_name)
        logger.debug("Marked %s as present in %s on %s", child_name, group_name, date_str)

    def unmark_attendance(self, date_str: str, group_name: str, child_name: str) -> None:
        """Marks a child as absent (removes from the present set)."""
        if date_str in self.attendance and group_name in self.attendance[date_str]:
            self.attendance[date_str][group_name].discard(child_name)
            logger.debug("Marked %s as absent in %s on %s", child_name, group_name, date_str)
            # Optional: Clean up empty sets/dates if desired, but might complicate logic
            # if not self.attendance[date_str][group_name]:
            #     del self.attendance[date_str][group_name]
            # if not self.attendance[date_str]:
            #     del self.attendance[date_str]


    def generate_attendance_report(self, days: int) -> Optional[str]:
        """
        Generates an Excel report for attendance over the last N days.

        Args:
            days: The number of days back from today to include in the report.

        Returns:
            The file path to the generated Excel report, or None if an error occurs
            or no relevant attendance data exists.
        """
        if not self.groups:
            logger.warning("Cannot generate report: No groups loaded.")
            return None
        if days <= 0:
             logger.warning("Cannot generate report: Number of days must be positive.")
             return None

        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        date_range = [start_date + timedelta(days=i) for i in range(days)]
        date_str_range = [d.isoformat() for d in date_range]

        # Filter attendance data to include only the relevant date range and *recorded* days
        relevant_attendance: AttendanceData = {
            date_str: groups_data
            for date_str, groups_data in self.attendance.items()
            if date_str in date_str_range and any(groups_data.values()) # Only include days where *someone* was marked
        }

        if not relevant_attendance:
            logger.info("No attendance data found within the last %d days to generate a report.", days)
            return None # Indicate no report generated

        # Get all unique dates where attendance was actually recorded within the range
        recorded_dates_sorted = sorted(relevant_attendance.keys())

        report_data = []
        all_children = []
        for group_name, children in self.groups.items():
            for child_name in children:
                all_children.append((group_name, child_name))
                child_row = {"Группа": group_name, "Имя Ребенка": child_name}
                for report_date_str in recorded_dates_sorted:
                    present_today = child_name in relevant_attendance.get(report_date_str, {}).get(group_name, set())
                    child_row[report_date_str] = 1 if present_today else 0 # Use 1 for present, 0 for absent
                report_data.append(child_row)

        if not report_data:
             logger.info("No children found in groups to generate report.")
             return None # Should not happen if self.groups is populated, but safety check


        try:
            df = pd.DataFrame(report_data)
            # Set MultiIndex
            df = df.set_index(["Группа", "Имя Ребенка"])
            # Ensure date columns are sorted correctly
            df = df[recorded_dates_sorted]


            report_filename = f"attendance_report_{end_date.strftime('%Y%m%d')}_last_{days}d.xlsx"
            report_filepath = os.path.join(config.REPORTS_DIR, report_filename)

            df.to_excel(report_filepath, engine='openpyxl')
            logger.info("Attendance report generated successfully: %s", report_filepath)
            return report_filepath

        except ImportError:
            logger.exception("Error generating report: 'openpyxl' required.")
            # Maybe notify the user via Telegram as well?
            return None
        except Exception as e:
            logger.exception("Error generating attendance report.")
            return None