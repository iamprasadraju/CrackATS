"""Cross-platform path utilities for user data management."""

import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def get_user_data_dir() -> Path:
    """Get cross-platform user data directory for CrackATS.

    Returns:
        Path to user data directory (creates if doesn't exist)

    Platform locations:
        - Windows: %APPDATA%/CrackATS
        - macOS: ~/Library/Application Support/CrackATS
        - Linux: ~/.local/share/CrackATS
    """
    if sys.platform == "win32":
        # Windows: %APPDATA%/CrackATS
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/CrackATS
        base = Path.home() / "Library/Application Support"
    else:
        # Linux: ~/.local/share/CrackATS
        base = Path.home() / ".local/share"

    data_dir = base / "CrackATS"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_path() -> Path:
    """Get database path in user data directory."""
    return get_user_data_dir() / "applications.db"


def get_backups_dir() -> Path:
    """Get backups directory."""
    backup_dir = get_user_data_dir() / "backups"
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def backup_database() -> Path | None:
    """Create timestamped backup of current database.

    Returns:
        Path to backup file or None if no database exists
    """
    db_path = get_db_path()
    if not db_path.exists():
        return None

    backup_dir = get_backups_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"applications_{timestamp}.db"

    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")

        # Keep only last 10 backups
        cleanup_old_backups(backup_dir, keep=10)

        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return None


def cleanup_old_backups(backup_dir: Path, keep: int = 10) -> None:
    """Remove old backups, keeping only the most recent.

    Args:
        backup_dir: Directory containing backups
        keep: Number of backups to retain
    """
    try:
        backups = sorted(backup_dir.glob("applications_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old_backup in backups[keep:]:
            old_backup.unlink()
            logger.debug(f"Removed old backup: {old_backup}")
    except Exception as e:
        logger.warning(f"Failed to cleanup old backups: {e}")


def migrate_legacy_database() -> bool:
    """Migrate database from legacy location (project root) to user data directory.

    Returns:
        True if migration occurred, False otherwise
    """
    # Legacy location (project root)
    legacy_db = Path(__file__).parent / "applications.db"
    new_db = get_db_path()

    # If new location already exists, no migration needed
    if new_db.exists():
        return False

    # If legacy doesn't exist, nothing to migrate
    if not legacy_db.exists():
        return False

    try:
        # Copy to new location
        shutil.copy2(legacy_db, new_db)
        logger.info(f"Migrated database from {legacy_db} to {new_db}")

        # Rename legacy to backup (don't delete for safety)
        legacy_backup = legacy_db.with_suffix(".db.backup")
        legacy_db.rename(legacy_backup)
        logger.info(f"Renamed legacy database to: {legacy_backup}")

        return True
    except Exception as e:
        logger.error(f"Failed to migrate database: {e}")
        # If migration fails, continue with legacy location as fallback
        return False


def ensure_database_location() -> Path:
    """Ensure database is in the correct location, migrating if necessary.

    Returns:
        Path to the database (either new or legacy location)
    """
    # Try to migrate legacy database
    migrated = migrate_legacy_database()

    if migrated:
        logger.info("Database migration completed successfully")

    # Return the appropriate path
    new_db = get_db_path()
    if new_db.exists():
        return new_db

    # Fallback to legacy location if migration failed
    legacy_db = Path(__file__).parent / "applications.db"
    if legacy_db.exists():
        logger.warning(f"Using legacy database location: {legacy_db}")
        return legacy_db

    # Return new location (will be created)
    return new_db
