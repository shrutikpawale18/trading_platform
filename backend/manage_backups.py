import argparse
import sys
from app.services.backup_service import BackupService

def main():
    parser = argparse.ArgumentParser(description="Manage database backups")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create backup command
    create_parser = subparsers.add_parser("create", help="Create a new backup")
    create_parser.set_defaults(func=lambda args: create_backup(args))

    # Restore backup command
    restore_parser = subparsers.add_parser("restore", help="Restore from a backup")
    restore_parser.add_argument("backup_path", help="Path to the backup file")
    restore_parser.set_defaults(func=lambda args: restore_backup(args))

    # List backups command
    list_parser = subparsers.add_parser("list", help="List available backups")
    list_parser.set_defaults(func=lambda args: list_backups(args))

    # Cleanup backups command
    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup old backups")
    cleanup_parser.add_argument("--keep", type=int, default=5, help="Number of backups to keep")
    cleanup_parser.set_defaults(func=lambda args: cleanup_backups(args))

    # Info command
    info_parser = subparsers.add_parser("info", help="Get information about a backup")
    info_parser.add_argument("backup_path", help="Path to the backup file")
    info_parser.set_defaults(func=lambda args: get_backup_info(args))

    args = parser.parse_args()
    
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    
    args.func(args)

def create_backup(args):
    backup_service = BackupService("trading.db")
    backup_path = backup_service.create_backup()
    print(f"Backup created successfully: {backup_path}")

def restore_backup(args):
    backup_service = BackupService("trading.db")
    backup_service.restore_backup(args.backup_path)
    print(f"Database restored from backup: {args.backup_path}")

def list_backups(args):
    backup_service = BackupService("trading.db")
    backups = backup_service.list_backups()
    
    if not backups:
        print("No backups found")
        return
    
    print("Available backups:")
    for i, backup in enumerate(backups, 1):
        info = backup_service.get_backup_info(backup)
        print(f"{i}. {backup}")
        print(f"   Created: {info['created_at']}")
        print(f"   Size: {info['size'] / 1024:.2f} KB")
        print(f"   Records: {info['algorithm_count']} algorithms, {info['signal_count']} signals, "
              f"{info['position_count']} positions, {info['trade_count']} trades")
        print()

def cleanup_backups(args):
    backup_service = BackupService("trading.db")
    backup_service.cleanup_old_backups(args.keep)
    print(f"Cleanup completed. Kept the {args.keep} most recent backups.")

def get_backup_info(args):
    backup_service = BackupService("trading.db")
    info = backup_service.get_backup_info(args.backup_path)
    
    print(f"Backup Information for {args.backup_path}:")
    print(f"Created: {info['created_at']}")
    print(f"Size: {info['size'] / 1024:.2f} KB")
    print(f"Records:")
    print(f"  - Algorithms: {info['algorithm_count']}")
    print(f"  - Signals: {info['signal_count']}")
    print(f"  - Positions: {info['position_count']}")
    print(f"  - Trades: {info['trade_count']}")

if __name__ == "__main__":
    main() 