"""
Unified printing utilities for tournament management.
This module provides shared functionality for generating print content across different tabs.
"""

# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import re
from typing import Tuple

from PyQt6 import QtWidgets
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog


class TournamentPrintUtils:
    """Utility class for unified tournament printing functionality."""

    @staticmethod
    def get_round_info(tournament_tab) -> str:
        """
        Get unified round information from tournament tab.

        Args:
            tournament_tab: Reference to the tournament tab widget

        Returns:
            Clean round information string for display
        """
        if not tournament_tab or not hasattr(tournament_tab, "lbl_round_title"):
            return ""

        round_title = tournament_tab.lbl_round_title.text()
        if not round_title or round_title == "No Tournament Loaded":
            return ""

        # Extract round information and clean it
        if "Round" in round_title:
            match = re.search(r"Round (\d+)", round_title)
            if match:
                round_num = int(match.group(1))
                # Check completion status
                if "Results" in round_title and hasattr(
                    tournament_tab, "current_round_index"
                ):
                    completed_rounds = tournament_tab.current_round_index
                    if round_num <= completed_rounds:
                        return f"After Round {round_num}"
                    else:
                        return f"During Round {round_num}"
                else:
                    return f"After Round {round_num}"

        return ""

    @staticmethod
    def get_clean_print_title(round_title: str) -> str:
        """
        Clean round title for print display.

        Args:
            round_title: Raw round title string

        Returns:
            Cleaned title suitable for printing
        """
        if not round_title:
            return ""

        # Remove common UI elements that shouldn't appear in print
        clean_title = round_title.replace(" Pairings & Results", " Pairings")
        clean_title = clean_title.replace(" (Re-entry)", "")
        return clean_title

    @staticmethod
    def create_print_preview_dialog(
        parent, title: str
    ) -> Tuple[QPrinter, QPrintPreviewDialog]:
        """
        Create a print preview dialog with standard settings.

        Args:
            parent: Parent widget
            title: Window title for the preview dialog

        Returns:
            Tuple of (printer, preview_dialog)
        """
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        preview = QPrintPreviewDialog(printer, parent)
        preview.setWindowTitle(title)
        return printer, preview


class PrintOptionsDialog(QtWidgets.QDialog):
    """Custom dialog for print options including tournament name inclusion."""

    def __init__(
        self, parent=None, tournament_name: str = "", print_type: str = "Document"
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Print Options - {print_type}")
        self.setModal(True)
        self.setMinimumWidth(300)
        layout = QtWidgets.QVBoxLayout(self)
        # No checkbox, just info label
        if tournament_name:
            info_label = QtWidgets.QLabel(
                f"Tournament name '{tournament_name}' will be included in the printout."
            )
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
        layout.addSpacing(10)
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #f8f9fa;
            }
            QLabel {
                font-size: 11pt;
                padding: 5px;
            }
            QPushButton {
                font-size: 11pt;
                padding: 6px 12px;
                min-width: 70px;
            }
        """
        )

    def get_options(self) -> dict:
        return {"include_tournament_name": True}
