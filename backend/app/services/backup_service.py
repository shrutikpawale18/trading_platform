import os
import shutil
import sqlite3
import datetime
import logging
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class BackupService:
    def __init__(self, db_path: str, backup_dir: str = "backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self._ensure_backup_dir()

    def _ensure_backup_dir(self):
        """Ensure backup directory exists."""
        os.makedirs(self.backup_dir, exist_ok=True)

    def _get_backup_filename(self, timestamp: Optional[datetime.datetime] = None) -> str:
        """Generate backup filename with timestamp."""
        if timestamp is None:
            timestamp = datetime.datetime.now()
        return f"trading_db_{timestamp.strftime('%Y%m%d_%H%M%S')}.db"

    def create_backup(self) -> str:
        """Create a backup of the database."""
        try:
            # Generate backup filename with timestamp
            backup_filename = self._get_backup_filename()
            backup_path = os.path.join(self.backup_dir, backup_filename)

            # Create backup using SQLite backup API
            source = sqlite3.connect(self.db_path)
            destination = sqlite3.connect(backup_path)
            
            with destination:
                source.backup(destination)
            
            source.close()
            destination.close()

            logger.info(f"Database backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Error creating database backup: {str(e)}")
            raise

    def restore_backup(self, backup_path: str) -> None:
        """Restore database from a backup file."""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Create a temporary backup of current database
            temp_backup = self._get_backup_filename() + ".temp"
            temp_backup_path = os.path.join(self.backup_dir, temp_backup)
            
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, temp_backup_path)

            try:
                # Restore from backup
                source = sqlite3.connect(backup_path)
                destination = sqlite3.connect(self.db_path)
                
                with destination:
                    source.backup(destination)
                
                source.close()
                destination.close()

                logger.info(f"Database restored from backup: {backup_path}")
                
                # Remove temporary backup if restore was successful
                if os.path.exists(temp_backup_path):
                    os.remove(temp_backup_path)

            except Exception as e:
                # Restore from temporary backup if something went wrong
                if os.path.exists(temp_backup_path):
                    shutil.copy2(temp_backup_path, self.db_path)
                    os.remove(temp_backup_path)
                raise

        except Exception as e:
            logger.error(f"Error restoring database backup: {str(e)}")
            raise

    def list_backups(self) -> List[str]:
        """List all available backups."""
        try:
            backups = []
            for file in os.listdir(self.backup_dir):
                if file.startswith("trading_db_") and file.endswith(".db"):
                    file_path = os.path.join(self.backup_dir, file)
                    backups.append(file_path)
            return sorted(backups, reverse=True)
        except Exception as e:
            logger.error(f"Error listing backups: {str(e)}")
            raise

    def cleanup_old_backups(self, keep_last_n: int = 5) -> None:
        """Remove old backups, keeping only the specified number of most recent ones."""
        try:
            backups = self.list_backups()
            if len(backups) > keep_last_n:
                for backup in backups[keep_last_n:]:
                    os.remove(backup)
                    logger.info(f"Removed old backup: {backup}")
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {str(e)}")
            raise

    def get_backup_info(self, backup_path: str) -> dict:
        """Get information about a specific backup."""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Connect to backup database
            conn = sqlite3.connect(backup_path)
            cursor = conn.cursor()

            # Get database statistics
            cursor.execute("SELECT COUNT(*) FROM algorithms")
            algorithm_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM signals")
            signal_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM positions")
            position_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM trades")
            trade_count = cursor.fetchone()[0]

            conn.close()

            # Get file information
            file_stats = os.stat(backup_path)
            created_time = datetime.datetime.fromtimestamp(file_stats.st_ctime)

            return {
                "path": backup_path,
                "size": file_stats.st_size,
                "created_at": created_time,
                "algorithm_count": algorithm_count,
                "signal_count": signal_count,
                "position_count": position_count,
                "trade_count": trade_count
            }

        except Exception as e:
            logger.error(f"Error getting backup info: {str(e)}")
            raise 