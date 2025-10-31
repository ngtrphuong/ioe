import os
import datetime
import shutil
import json
import glob
import logging
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class BackupService:
    """Database backup and restore services"""
    
    @staticmethod
    def get_backup_directory():
        """Get the backup directory, create it if it does not exist"""
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    @staticmethod
    def create_backup(backup_name=None, user=None):
        """
        Create a database backup
        :param backup_name: Backup name, defaults to current date/time if None
        :param user: The user performing the backup
        :return: Path to backup
        """
        if not backup_name:
            now = datetime.datetime.now()
            backup_name = f"backup_{now.strftime('%Y%m%d_%H%M%S')}"
        # Create backup directory
        backup_dir = BackupService.get_backup_directory()
        backup_path = os.path.join(backup_dir, backup_name)
        os.makedirs(backup_path, exist_ok=True)
        try:
            # Export database as JSON fixtures
            fixtures_path = os.path.join(backup_path, 'db.json')
            with open(fixtures_path, 'w', encoding='utf-8') as f:
                call_command('dumpdata', '--exclude', 'contenttypes', '--exclude', 'auth.Permission',
                            '--exclude', 'sessions.session', '--indent', '2', stdout=f)
            # Backup media files
            media_dir = os.path.join(settings.BASE_DIR, 'media')
            if os.path.exists(media_dir):
                media_backup_dir = os.path.join(backup_path, 'media')
                os.makedirs(media_backup_dir, exist_ok=True)
                for item in os.listdir(media_dir):
                    source = os.path.join(media_dir, item)
                    target = os.path.join(media_backup_dir, item)
                    if os.path.isdir(source):
                        shutil.copytree(source, target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(source, target)
            # Write backup metadata
            metadata = {
                'backup_name': backup_name,
                'created_at': datetime.datetime.now().isoformat(),
                'created_by': user.username if user else 'system',
                'django_version': settings.DJANGO_VERSION,
                'database_engine': settings.DATABASES['default']['ENGINE'],
            }
            with open(os.path.join(backup_path, 'metadata.json'), 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Backup created successfully: {backup_name}")
            return backup_path
        except Exception as e:
            # If backup fails, remove any partial backup
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            logger.error(f"Failed to create backup: {str(e)}")
            raise

    @staticmethod
    def restore_backup(backup_name, user=None):
        """
        Restore a database from backup
        :param backup_name: Backup name
        :param user: The user performing the restore
        :return: True if successful, False if failed
        """
        backup_dir = BackupService.get_backup_directory()
        backup_path = os.path.join(backup_dir, backup_name)
        if not os.path.exists(backup_path):
            logger.error(f"Backup does not exist: {backup_name}")
            return False
        try:
            # Restore database
            fixtures_path = os.path.join(backup_path, 'db.json')
            if os.path.exists(fixtures_path):
                # Clear database, keep superuser
                superusers = list(User.objects.filter(is_superuser=True).values_list('username', flat=True))
                call_command('flush', '--noinput')
                call_command('loaddata', fixtures_path)
                # Record restore operation
                with open(os.path.join(backup_path, 'restore_log.json'), 'w', encoding='utf-8') as f:
                    restore_log = {
                        'restored_at': datetime.datetime.now().isoformat(),
                        'restored_by': user.username if user else 'system',
                    }
                    json.dump(restore_log, f, indent=2)
                # Restore media files
                media_backup_dir = os.path.join(backup_path, 'media')
                if os.path.exists(media_backup_dir):
                    media_dir = os.path.join(settings.BASE_DIR, 'media')
                    if os.path.exists(media_dir):
                        # Backup current media files first
                        media_backup = os.path.join(settings.BASE_DIR, f"media_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
                        shutil.move(media_dir, media_backup)
                    # Copy backup media files
                    shutil.copytree(media_backup_dir, media_dir)
                logger.info(f"Backup restored successfully: {backup_name}")
                return True
            else:
                logger.error(f"Backup is incomplete, missing db.json: {backup_name}")
                return False
        except Exception as e:
            logger.error(f"Failed to restore backup: {str(e)}")
            return False
    
    @staticmethod
    def list_backups():
        """
        List all backups
        :return: List of backups, e.g. [{'name': name, 'created_at': datetime, 'size': size_in_mb, ...}, ...]
        """
        backup_dir = BackupService.get_backup_directory()
        if not os.path.exists(backup_dir):
            return []
        backups = []
        for backup_name in os.listdir(backup_dir):
            backup_path = os.path.join(backup_dir, backup_name)
            if os.path.isdir(backup_path):
                metadata_path = os.path.join(backup_path, 'metadata.json')
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        # Calculate backup size
                        size_bytes = sum(
                            os.path.getsize(os.path.join(dirpath, filename))
                            for dirpath, _, filenames in os.walk(backup_path)
                            for filename in filenames
                        )
                        size_mb = size_bytes / (1024 * 1024)
                        backups.append({
                            'name': backup_name,
                            'created_at': datetime.datetime.fromisoformat(metadata['created_at']),
                            'created_by': metadata.get('created_by', 'unknown'),
                            'size': f"{size_mb:.2f} MB",
                            'size_bytes': size_bytes,
                            'metadata': metadata
                        })
                    except Exception as e:
                        logger.warning(f"Failed to read backup metadata: {backup_name}, error: {str(e)}")
                        # Add a simple record without metadata
                        backups.append({
                            'name': backup_name,
                            'created_at': datetime.datetime.fromtimestamp(os.path.getctime(backup_path)),
                            'created_by': 'unknown',
                            'size': 'unknown',
                            'size_bytes': 0,
                            'metadata': {}
                        })
        # Sort descending by created_at
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return backups
    
    @staticmethod
    def delete_backup(backup_name):
        """
        Delete the specified backup
        :param backup_name: Backup name
        :return: True if successful, False otherwise
        """
        backup_dir = BackupService.get_backup_directory()
        backup_path = os.path.join(backup_dir, backup_name)
        if not os.path.exists(backup_path):
            logger.error(f"Backup does not exist: {backup_name}")
            return False
        try:
            shutil.rmtree(backup_path)
            logger.info(f"Backup deleted successfully: {backup_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete backup: {str(e)}")
            return False
    
    @staticmethod
    def auto_backup():
        """
        Run automatic backup and clean up backups older than 60 days
        """
        try:
            # Create new backup
            backup_name = f"auto_backup_{datetime.datetime.now().strftime('%Y%m%d')}"
            BackupService.create_backup(backup_name=backup_name)
            # Compute cut-off date
            days_to_keep = getattr(settings, 'BACKUP_DAYS_TO_KEEP', 60)
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
            # List all backups and delete old auto backups
            backups = BackupService.list_backups()
            for backup in backups:
                if backup['name'].startswith('auto_backup_') and backup['created_at'] < cutoff_date:
                    BackupService.delete_backup(backup['name'])
            return True
        except Exception as e:
            logger.error(f"Automatic backup failed: {str(e)}")
            return False 