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

"""
Modern Update Worker for PyQt6

Handles the complete update process in a background thread with proper
progress reporting and error handling.
"""

import logging
from typing import TYPE_CHECKING

from PyQt6 import QtCore

if TYPE_CHECKING:
    from gambitpairing.core.updater import ModernUpdater


class ModernUpdateWorker(QtCore.QObject):
    """
    Modern worker thread for handling the complete update process.

    Signals:
    - progress(int): Download progress (0-100)
    - status(str): Status message updates
    - finished(str): Update completed successfully with path to extracted files
    - error(str): Update failed with error message
    - done(bool, str): Final result - (success, message/path)
    """

    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(str)  # Returns extracted path
    error = QtCore.pyqtSignal(str)
    done = QtCore.pyqtSignal(bool, str)  # (success, message or extracted_path)

    def __init__(self, updater: "ModernUpdater"):
        super().__init__()
        self.updater = updater
        self._setup_callbacks()

    def _setup_callbacks(self):
        """Set up progress and status callbacks for the updater."""
        self.updater.set_callbacks(
            progress_callback=self._on_progress, status_callback=self._on_status
        )

    def _on_progress(self, progress: int):
        """Handle progress updates from updater."""
        self.progress.emit(progress)

    def _on_status(self, status: str):
        """Handle status updates from updater."""
        self.status.emit(status)

    def run(self):
        """Execute the complete update process."""
        try:
            # Step 1: Download
            self.status.emit("Starting download...")
            if not self.updater.download_update():
                self.error.emit("Failed to download update.")
                self.done.emit(False, "Failed to download update.")
                return

            # Step 2: Verify
            self.status.emit("Verifying download...")
            if not self.updater.verify_download():
                self.error.emit(
                    "Download verification failed. The file may be corrupted."
                )
                self.done.emit(False, "Download verification failed.")
                return

            # Step 3: Extract
            self.status.emit("Extracting update...")
            if not self.updater.extract_update():
                self.error.emit("Failed to extract update file.")
                self.done.emit(False, "Failed to extract update file.")
                return

            # Success - update is ready to be applied
            extracted_path = self.updater.get_pending_update_path()
            if extracted_path:
                self.status.emit("Update ready to install.")
                self.finished.emit(extracted_path)
                self.done.emit(True, extracted_path)
            else:
                self.error.emit("Update extraction completed but path not available.")
                self.done.emit(False, "Update extraction path not available.")

        except Exception as e:
            logging.error(f"Unexpected error in update worker: {e}", exc_info=True)
            self.error.emit(f"An unexpected error occurred: {e}")
            self.done.emit(False, f"An unexpected error occurred: {e}")


# Backward compatibility alias
UpdateWorker = ModernUpdateWorker
