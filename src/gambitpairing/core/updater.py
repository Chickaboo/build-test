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
Advanced GitHub Releases-based Updater for Gambit Pairing

This updater follows industry best practices:
- Atomic updates with rollback capability
- Checksums for integrity verification
- Support for both single-file and directory installations
- Robust error handling and logging
- Automatic installation type detection
- Background downloads with progress reporting
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
from packaging.version import parse as parse_version

from gambitpairing.core.constants import UPDATE_URL
from gambitpairing.core.utils import setup_logger

logger = setup_logger(__name__)


class InstallationType(Enum):
    """Type of installation detected."""

    SINGLE_FILE = "single_file"  # Portable executable
    DIRECTORY = "directory"  # Directory-based installation
    SYSTEM_INSTALL = "system"  # MSI/system installation
    DEVELOPMENT = "development"  # Running from source


class UpdateStatus(Enum):
    """Update process status."""

    IDLE = "idle"
    CHECKING = "checking"
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    EXTRACTING = "extracting"
    READY = "ready"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"


class UpdateAsset:
    """Represents an update asset from GitHub releases."""

    def __init__(
        self, name: str, download_url: str, size: int, checksum: Optional[str] = None
    ):
        self.name = name
        self.download_url = download_url
        self.size = size
        self.checksum = checksum

    @property
    def is_portable(self) -> bool:
        """Check if this is a portable (single-file) asset."""
        return "portable" in self.name.lower()

    @property
    def is_directory(self) -> bool:
        """Check if this is a directory-based asset."""
        return "directory" in self.name.lower()

    @property
    def is_msi(self) -> bool:
        """Check if this is an MSI installer asset."""
        return self.name.lower().endswith(".msi")

    @property
    def is_windows(self) -> bool:
        """Check if this is a Windows asset."""
        return "win" in self.name.lower()


class ModernUpdater:
    """
    Modern, robust updater for Gambit Pairing.

    Features:
    - Automatic installation type detection
    - Atomic updates with rollback
    - Checksum verification
    - Progress callbacks
    - Comprehensive error handling
    - Support for multiple asset types
    """

    def __init__(
        self,
        current_version: str,
        repo_owner: str = "gambit-devs",
        repo_name: str = "gambit-pairing",
    ):
        self.current_version = current_version.lstrip("v")
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_url = (
            f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        )

        # State
        self.status = UpdateStatus.IDLE
        self.latest_release: Optional[Dict[str, Any]] = None
        self.available_assets: List[UpdateAsset] = []
        self.selected_asset: Optional[UpdateAsset] = None
        self.download_path: Optional[Path] = None
        self.extract_path: Optional[Path] = None

        # Installation detection
        self.installation_type = self._detect_installation_type()
        self.app_path = self._get_app_path()

        # Callbacks
        self.progress_callback: Optional[Callable[[int], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None

        # Temp directories
        self.temp_dir = Path(tempfile.gettempdir()) / "gambit_pairing_update"
        self.backup_dir = Path(tempfile.gettempdir()) / "gambit_pairing_backup"

        logger.info(
            f"Initialized updater for {current_version} ({self.installation_type.value})"
        )

    def _detect_installation_type(self) -> InstallationType:
        """Detect the type of installation."""
        if not getattr(sys, "frozen", False):
            return InstallationType.DEVELOPMENT

        exe_path = Path(sys.executable)
        app_dir = exe_path.parent

        # Check if it's a single-file installation
        # Single-file executables typically have minimal files in their directory
        dir_contents = list(app_dir.iterdir())
        exe_files = [f for f in dir_contents if f.suffix.lower() == ".exe"]

        if len(dir_contents) <= 3 and len(exe_files) == 1:
            return InstallationType.SINGLE_FILE

        # Check for MSI installation markers
        if (app_dir / "Uninstall.exe").exists() or "Program Files" in str(app_dir):
            return InstallationType.SYSTEM_INSTALL

        return InstallationType.DIRECTORY

    def _get_app_path(self) -> Optional[Path]:
        """Get the application path based on installation type."""
        if not getattr(sys, "frozen", False):
            return None

        if self.installation_type == InstallationType.SINGLE_FILE:
            return Path(sys.executable)
        else:
            return Path(sys.executable).parent

    def check_for_updates(self) -> bool:
        """Check for available updates from GitHub releases."""
        self.status = UpdateStatus.CHECKING
        self._notify_status("Checking for updates...")

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(self.api_url)
                response.raise_for_status()
                self.latest_release = response.json()

            if not self.latest_release:
                self.status = UpdateStatus.FAILED
                return False

            latest_version = self.latest_release.get("tag_name", "0.0.0").lstrip("v")

            if parse_version(latest_version) <= parse_version(self.current_version):
                logger.info(
                    f"No update available. Current: {self.current_version}, Latest: {latest_version}"
                )
                self.status = UpdateStatus.IDLE
                return False

            # Parse available assets
            self.available_assets = self._parse_assets(
                self.latest_release.get("assets", [])
            )

            # Select the best asset for our installation type
            self.selected_asset = self._select_best_asset()

            if not self.selected_asset:
                logger.warning(
                    f"No suitable update asset found for {self.installation_type.value}"
                )
                self.status = UpdateStatus.FAILED
                return False

            self.status = UpdateStatus.AVAILABLE
            logger.info(
                f"Update available: {latest_version} -> {self.selected_asset.name}"
            )
            return True

        except httpx.RequestError as e:
            logger.error(f"Network error checking for updates: {e}")
            self.status = UpdateStatus.FAILED
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking for updates: {e}")
            self.status = UpdateStatus.FAILED
            return False

    def _parse_assets(self, assets_data: List[Dict[str, Any]]) -> List[UpdateAsset]:
        """Parse GitHub release assets."""
        assets = []
        checksums = {}

        # First pass: collect checksums
        for asset_data in assets_data:
            name = asset_data.get("name", "")
            if name.endswith((".sha256", ".checksum")):
                # Download checksum file
                try:
                    with httpx.Client(timeout=10.0) as client:
                        response = client.get(
                            asset_data.get("browser_download_url", "")
                        )
                        checksum_content = response.text.strip()
                        # Parse checksum file (format: "hash  filename")
                        lines = checksum_content.split("\n")
                        for line in lines:
                            parts = line.split()
                            if len(parts) >= 2:
                                hash_value = parts[0]
                                filename = parts[1]
                                checksums[filename] = hash_value
                except Exception as e:
                    logger.warning(f"Could not download checksum for {name}: {e}")

        # Second pass: create assets with checksums
        for asset_data in assets_data:
            name = asset_data.get("name", "")
            download_url = asset_data.get("browser_download_url", "")
            size = asset_data.get("size", 0)

            # Skip checksum files
            if name.endswith((".sha256", ".checksum")):
                continue

            # Only include Windows assets
            if not ("win" in name.lower() and name.endswith(".zip")):
                continue

            checksum = checksums.get(name)
            assets.append(UpdateAsset(name, download_url, size, checksum))

        return assets

    def _select_best_asset(self) -> Optional[UpdateAsset]:
        """Select the best asset for the current installation type."""
        if not self.available_assets:
            return None

        # For development, don't update
        if self.installation_type == InstallationType.DEVELOPMENT:
            return None

        # For system installs, prefer MSI but fallback to directory
        if self.installation_type == InstallationType.SYSTEM_INSTALL:
            msi_assets = [a for a in self.available_assets if a.is_msi]
            if msi_assets:
                return msi_assets[0]

        # Match installation type to asset type
        for asset in self.available_assets:
            if (
                self.installation_type == InstallationType.SINGLE_FILE
                and asset.is_portable
            ):
                return asset
            elif (
                self.installation_type == InstallationType.DIRECTORY
                and asset.is_directory
            ):
                return asset

        # Fallback: return any Windows asset
        windows_assets = [a for a in self.available_assets if a.is_windows]
        return windows_assets[0] if windows_assets else None

    def get_latest_version(self) -> Optional[str]:
        """Get the latest version string."""
        if not self.latest_release:
            return None
        return self.latest_release.get("tag_name", "").lstrip("v")

    def get_release_notes(self) -> Optional[str]:
        """Get the release notes."""
        if not self.latest_release:
            return None
        return self.latest_release.get("body", "No release notes available.")

    def download_update(
        self, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """Download the selected update asset."""
        if not self.selected_asset or self.status != UpdateStatus.AVAILABLE:
            return False

        self.status = UpdateStatus.DOWNLOADING
        self.progress_callback = progress_callback

        # Prepare temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.download_path = self.temp_dir / self.selected_asset.name

        try:
            self._notify_status(f"Downloading {self.selected_asset.name}...")

            with httpx.Client(timeout=120.0) as client:
                with client.stream("GET", self.selected_asset.download_url) as response:
                    response.raise_for_status()

                    total_size = int(
                        response.headers.get("content-length", self.selected_asset.size)
                    )
                    downloaded = 0

                    with open(self.download_path, "wb") as file:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            file.write(chunk)
                            downloaded += len(chunk)

                            if self.progress_callback and total_size > 0:
                                progress = int((downloaded / total_size) * 100)
                                self.progress_callback(progress)

            logger.info(f"Downloaded {self.selected_asset.name} ({downloaded} bytes)")
            return True

        except Exception as e:
            logger.error(f"Failed to download update: {e}")
            self.status = UpdateStatus.FAILED
            return False

    def verify_download(self) -> bool:
        """Verify the downloaded file integrity."""
        if (
            not self.download_path
            or not self.download_path.exists()
            or not self.selected_asset
        ):
            return False

        self.status = UpdateStatus.VERIFYING
        self._notify_status("Verifying download...")

        # Check file size
        actual_size = self.download_path.stat().st_size
        if (
            self.selected_asset.size > 0
            and abs(actual_size - self.selected_asset.size) > 1024
        ):
            logger.error(
                f"Size mismatch: expected {self.selected_asset.size}, got {actual_size}"
            )
            return False

        # Verify checksum if available
        if self.selected_asset.checksum:
            calculated_hash = self._calculate_sha256(self.download_path)
            if calculated_hash.lower() != self.selected_asset.checksum.lower():
                logger.error(
                    f"Checksum mismatch: expected {self.selected_asset.checksum}, got {calculated_hash}"
                )
                return False
            logger.info("Checksum verification passed")
        else:
            logger.warning("No checksum available for verification")

        return True

    def extract_update(self) -> bool:
        """Extract the downloaded update."""
        if not self.download_path or not self.download_path.exists():
            return False

        self.status = UpdateStatus.EXTRACTING
        self._notify_status("Extracting update...")

        self.extract_path = self.temp_dir / "extracted"
        if self.extract_path.exists():
            shutil.rmtree(self.extract_path)
        self.extract_path.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(self.download_path, "r") as zip_file:
                zip_file.extractall(self.extract_path)

            # Clean up download
            self.download_path.unlink()

            # Handle single directory extraction
            extracted_items = list(self.extract_path.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                # Move contents up one level
                single_dir = extracted_items[0]
                temp_extract = self.temp_dir / "temp_extract"
                single_dir.rename(temp_extract)
                shutil.rmtree(self.extract_path)
                temp_extract.rename(self.extract_path)

            self.status = UpdateStatus.READY
            logger.info(f"Update extracted to {self.extract_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to extract update: {e}")
            self.status = UpdateStatus.FAILED
            return False

    def apply_update(self) -> bool:
        """Apply the extracted update."""
        if (
            not self.extract_path
            or not self.extract_path.exists()
            or self.status != UpdateStatus.READY
        ):
            return False

        if self.installation_type == InstallationType.DEVELOPMENT:
            logger.warning("Cannot update development installation")
            return False

        self.status = UpdateStatus.APPLYING
        self._notify_status("Applying update...")

        try:
            if self.installation_type == InstallationType.SINGLE_FILE:
                return self._apply_single_file_update()
            elif self.installation_type == InstallationType.DIRECTORY:
                return self._apply_directory_update()
            elif self.installation_type == InstallationType.SYSTEM_INSTALL:
                return self._apply_system_update()
            else:
                logger.error(f"Unsupported installation type: {self.installation_type}")
                return False
        except Exception as e:
            logger.error(f"Failed to apply update: {e}")
            self.status = UpdateStatus.FAILED
            return False

    def _apply_single_file_update(self) -> bool:
        """Apply update for single-file installation."""
        if not self.app_path or not self.extract_path:
            return False

        # Find the new executable in the extracted files
        new_exe = None
        for file_path in self.extract_path.rglob("*.exe"):
            if file_path.name.lower().startswith("gambit"):
                new_exe = file_path
                break

        if not new_exe or not new_exe.exists():
            logger.error("Could not find new executable in update")
            return False

        # Create backup
        backup_path = self.backup_dir / self.app_path.name
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(self.app_path, backup_path)
            logger.info(f"Backed up current executable to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

        # Replace executable (will be completed after restart)
        self._schedule_file_replacement(str(new_exe), str(self.app_path))

        self.status = UpdateStatus.COMPLETED
        logger.info("Single-file update prepared successfully")
        return True

    def _apply_directory_update(self) -> bool:
        """Apply update for directory installation."""
        if not self.app_path or not self.extract_path:
            return False

        # Create backup
        backup_name = f"backup_{int(time.time())}"
        backup_path = self.backup_dir / backup_name
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copytree(self.app_path, backup_path)
            logger.info(f"Backed up current installation to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

        # Apply update by replacing files (skip running executable)
        try:
            current_exe = Path(sys.executable)
            errors: List[str] = []

            def copy_tree_selective(src: Path, dst: Path):
                """Copy tree but skip the currently running executable."""
                for item in src.iterdir():
                    src_item = src / item.name
                    dst_item = dst / item.name

                    if src_item.is_dir():
                        dst_item.mkdir(exist_ok=True)
                        copy_tree_selective(src_item, dst_item)
                    else:
                        # Skip the currently running executable
                        if dst_item.resolve() == current_exe.resolve():
                            # Schedule for replacement after restart
                            self._schedule_file_replacement(
                                str(src_item), str(dst_item)
                            )
                            continue

                        try:
                            shutil.copy2(src_item, dst_item)
                        except Exception as e:
                            errors.append(
                                f"Failed to copy {src_item} to {dst_item}: {e}"
                            )

            copy_tree_selective(self.extract_path, self.app_path)

            if errors:
                logger.warning(f"Some files could not be updated: {errors}")
            else:
                logger.info("Directory update applied successfully")

            self.status = UpdateStatus.COMPLETED
            return True

        except Exception as e:
            logger.error(f"Failed to apply directory update: {e}")
            # Attempt rollback
            self._rollback_from_backup(backup_path)
            return False

    def _apply_system_update(self) -> bool:
        """Apply update for system installation (MSI)."""
        if not self.extract_path:
            return False

        # For MSI installations, we should launch the new MSI
        logger.info("System installation update requires running the new MSI installer")

        # Find MSI in extracted files
        msi_file = None
        for file_path in self.extract_path.rglob("*.msi"):
            msi_file = file_path
            break

        if not msi_file:
            logger.error("No MSI installer found in update")
            return False

        # Copy MSI to a persistent location
        persistent_msi = Path(tempfile.gettempdir()) / "gambit_update.msi"
        shutil.copy2(msi_file, persistent_msi)

        # Schedule MSI execution
        self._schedule_msi_install(str(persistent_msi))

        self.status = UpdateStatus.COMPLETED
        logger.info("System update prepared successfully")
        return True

    def _schedule_file_replacement(self, source: str, destination: str):
        """Schedule a file replacement to happen after restart."""
        # Create a batch script for Windows to handle the replacement
        batch_script = self.temp_dir / "update_files.bat"

        batch_content = f"""@echo off
timeout /t 2 /nobreak >nul
copy /y "{source}" "{destination}"
del "{source}"
del "%~f0"
"""

        with open(batch_script, "w") as f:
            f.write(batch_content)

        # Schedule the batch script to run after application exit
        startup_script = self._get_startup_script_path()
        with open(startup_script, "w") as f:
            f.write(f'start /b "" "{batch_script}"\n')

    def _schedule_msi_install(self, msi_path: str):
        """Schedule MSI installation after application exit."""
        batch_script = self.temp_dir / "install_update.bat"

        batch_content = f"""@echo off
timeout /t 2 /nobreak >nul
msiexec /i "{msi_path}" /quiet /norestart
del "{msi_path}"
del "%~f0"
"""

        with open(batch_script, "w") as f:
            f.write(batch_content)

        startup_script = self._get_startup_script_path()
        with open(startup_script, "w") as f:
            f.write(f'start /b "" "{batch_script}"\n')

    def _get_startup_script_path(self) -> Path:
        """Get the path for the startup script."""
        return self.temp_dir / "run_on_startup.bat"

    def _rollback_from_backup(self, backup_path: Path):
        """Rollback from backup in case of update failure."""
        if not self.app_path:
            return

        try:
            if self.installation_type == InstallationType.SINGLE_FILE:
                shutil.copy2(backup_path, self.app_path)
            else:
                shutil.rmtree(self.app_path)
                shutil.copytree(backup_path, self.app_path)
            logger.info("Successfully rolled back from backup")
        except Exception as e:
            logger.error(f"Failed to rollback from backup: {e}")

    def cleanup(self):
        """Clean up temporary files and directories."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            # Keep backup for a while in case rollback is needed
            logger.info("Cleanup completed")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    def get_pending_update_path(self) -> Optional[str]:
        """Check if there's a pending update ready to be applied."""
        if (
            self.status == UpdateStatus.READY
            and self.extract_path
            and self.extract_path.exists()
        ):
            return str(self.extract_path)
        return None

    def cleanup_pending_update(self):
        """Clean up any pending update."""
        if self.extract_path and self.extract_path.exists():
            shutil.rmtree(self.extract_path)
        self.status = UpdateStatus.IDLE

    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _notify_status(self, message: str):
        """Notify about status changes."""
        logger.info(message)
        if self.status_callback:
            self.status_callback(message)

    def set_callbacks(
        self,
        progress_callback: Optional[Callable[[int], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        """Set progress and status callbacks."""
        self.progress_callback = progress_callback
        self.status_callback = status_callback

    def get_installation_info(self) -> Dict[str, Any]:
        """Get information about the current installation."""
        return {
            "type": self.installation_type.value,
            "path": str(self.app_path) if self.app_path else None,
            "current_version": self.current_version,
            "executable": sys.executable if getattr(sys, "frozen", False) else None,
            "is_frozen": getattr(sys, "frozen", False),
        }


# Backward compatibility alias
Updater = ModernUpdater
