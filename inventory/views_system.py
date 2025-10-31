from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
import os
import json
import time
import shutil
import logging
import re
import zipfile
from datetime import datetime
from django.contrib.admin.models import LogEntry
from django.core import management
from django.http import HttpResponse
from django.utils.text import slugify

from .permissions.decorators import permission_required
from .utils.logging import log_view_access
from .services.backup_service import BackupService

# Get logger
logger = logging.getLogger(__name__)

def get_dir_size_display(dir_path):
    """Get user-friendly directory size display"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(dir_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    # Convert to appropriate unit
    size_bytes = total_size
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def system_settings(request):
    """
    System settings view
    """
    context = {
        "tab": "settings",
        "media_root": settings.MEDIA_ROOT,
        "static_root": settings.STATIC_ROOT,
        # ...
    }
    return render(request, "inventory/system/settings.html", context)

@login_required
@permission_required('inventory.can_manage_backup')
def backup_list(request):
    """Backup list view"""
    # Check if backup directory exists
    if not os.path.exists(settings.BACKUP_ROOT):
        os.makedirs(settings.BACKUP_ROOT, exist_ok=True)
    # Get all backups
    backups = []
    for backup_name in os.listdir(settings.BACKUP_ROOT):
        backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
        if os.path.isdir(backup_dir):
            # Read backup info
            backup_info_file = os.path.join(backup_dir, 'backup_info.json')
            try:
                with open(backup_info_file, 'r', encoding='utf-8') as f:
                    backup_info = json.load(f)
                backups.append({
                    'name': backup_name,
                    'created_at': datetime.fromisoformat(backup_info.get('created_at', '')),
                    'created_by': backup_info.get('created_by', 'unknown'),
                    'size': get_dir_size_display(backup_dir)
                })
            except Exception as e:
                logger.error(f"Failed to read backup info: {str(e)}")
    # Sort by creation time descending
    backups.sort(key=lambda x: x['created_at'], reverse=True)
    return render(request, "inventory/system/backup_list.html", {"backups": backups})

@login_required
@permission_required('inventory.can_manage_backup')
def create_backup(request):
    """Create backup view"""
    # Generate a suggested backup name
    now = datetime.now()
    suggested_name = f"backup_{now.strftime('%Y%m%d_%H%M%S')}"
    if request.method == 'POST':
        # Get form data
        backup_name = request.POST.get('backup_name', '').strip()
        if not backup_name:
            backup_name = suggested_name
        # Validate backup name
        if not re.match(r'^[a-zA-Z0-9_\-]+$', backup_name):
            messages.error(request, "Backup name can only contain letters, numbers, underscores and hyphens")
            return render(request, 'inventory/system/create_backup.html', {'suggested_name': suggested_name})
        # Check if backup already exists
        backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
        if os.path.exists(backup_dir):
            messages.error(request, f"Backup {backup_name} already exists")
            return render(request, 'inventory/system/create_backup.html', {'suggested_name': suggested_name})
        # Create backup dir
        os.makedirs(backup_dir, exist_ok=True)
        try:
            # Backup database
            db_file = os.path.join(backup_dir, 'db.json')
            management.call_command('dumpdata', '--exclude', 'auth.permission', '--exclude', 'contenttypes', '--output', db_file)
            # Backup media files
            backup_media = request.POST.get('backup_media') == 'on'
            if backup_media and os.path.exists(settings.MEDIA_ROOT):
                media_dir = os.path.join(backup_dir, 'media')
                os.makedirs(media_dir, exist_ok=True)
                # Copy media files
                for item in os.listdir(settings.MEDIA_ROOT):
                    src_path = os.path.join(settings.MEDIA_ROOT, item)
                    dst_path = os.path.join(media_dir, item)
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
            # Backup description
            backup_description = request.POST.get('backup_description', '').strip()
            # ... rest of backup logic ...
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            messages.error(request, f"Backup failed: {str(e)}")
        return redirect('backup_list')
    return render(request, 'inventory/system/create_backup.html', {'suggested_name': suggested_name})

@login_required
@permission_required('inventory.can_manage_backup')
def restore_backup(request, backup_name):
    """Restore backup view"""
    # Check if backup exists
    backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
    if not os.path.exists(backup_dir):
        messages.error(request, f"Backup {backup_name} does not exist")
        return redirect('backup_list')
    
    # Get backup information
    backup_info_file = os.path.join(backup_dir, 'backup_info.json')
    try:
        with open(backup_info_file, 'r', encoding='utf-8') as f:
            backup_info = json.load(f)
    except Exception as e:
        messages.error(request, f"Failed to read backup info: {str(e)}")
        return redirect('backup_list')
    
    # Package backup object
    backup = {
        'name': backup_name,
        'created_at': datetime.fromisoformat(backup_info.get('created_at', '')),
        'created_by': backup_info.get('created_by', 'unknown'),
        'size': get_dir_size_display(backup_dir),
    }
    
    if request.method == 'POST':
        # Confirm restore
        if not request.POST.get('confirm_restore'):
            messages.error(request, "Please confirm the restore operation")
            return render(request, 'inventory/system/restore_backup.html', {'backup': backup})
        
        # If to restore media files
        restore_media = request.POST.get('restore_media') == 'on'
        
        # Execute restore
        try:
            # Create temp directory
            temp_dir = os.path.join(settings.TEMP_DIR, f"restore_{backup_name}_{int(time.time())}")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Restore database
            db_file = os.path.join(backup_dir, 'db.json')
            if not os.path.exists(db_file):
                messages.error(request, "Database file not found in backup")
                return redirect('backup_list')
            
            # Execute database restore
            management.call_command('flush', '--noinput')  # Clear current database
            management.call_command('loaddata', db_file)  # Load backup data
            
            # Restore media files
            if restore_media:
                media_backup = os.path.join(backup_dir, 'media')
                if os.path.exists(media_backup):
                    # Backup current media files
                    if os.path.exists(settings.MEDIA_ROOT):
                        current_media_backup = os.path.join(temp_dir, 'media_backup')
                        shutil.copytree(settings.MEDIA_ROOT, current_media_backup)
                    
                    # Remove all files in current media dir (keep structure)
                    for item in os.listdir(settings.MEDIA_ROOT):
                        item_path = os.path.join(settings.MEDIA_ROOT, item)
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.remove(item_path)
                    
                    # Copy backup media files to media dir
                    for item in os.listdir(media_backup):
                        src_path = os.path.join(media_backup, item)
                        dst_path = os.path.join(settings.MEDIA_ROOT, item)
                        if os.path.isdir(src_path):
                            shutil.copytree(src_path, dst_path)
                        else:
                            shutil.copy2(src_path, dst_path)
            
            # Log record
            LogEntry.objects.create(
                user=request.user,
                action_type='RESTORE',
                object_id=backup_name,
                object_repr=f'Backup: {backup_name}',
                change_message=f'Restored system data from backup {backup_name}' + (' and media files' if restore_media else '')
            )
            
            messages.success(request, f"Successfully restored system data from backup {backup_name}" + (" and media files" if restore_media else ""))
            
            # Cleanup temp dir
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
            return redirect('index')
            
        except Exception as e:
            # Restore failed
            messages.error(request, f"Restore failed: {str(e)}")
            logger.error(f"Restore backup {backup_name} failed: {str(e)}")
            # Log restore failure
            LogEntry.objects.create(
                user=request.user,
                action_type='ERROR',
                object_id=backup_name,
                object_repr=f'Backup: {backup_name}',
                change_message=f'Restore backup {backup_name} failed: {str(e)}'
            )
            return redirect('backup_list')
    
    return render(request, 'inventory/system/restore_backup.html', {'backup': backup})

@login_required
@permission_required('inventory.can_manage_backup')
def delete_backup(request, backup_name):
    """Delete backup view"""
    backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
    if not os.path.exists(backup_dir):
        messages.error(request, f"Backup {backup_name} does not exist")
        return redirect('backup_list')
    
    try:
        # Delete backup dir
        shutil.rmtree(backup_dir)
        
        # Log record
        LogEntry.objects.create(
            user=request.user,
            action_type='DELETE',
            object_id=backup_name,
            object_repr=f'Backup: {backup_name}',
            change_message=f'Deleted system backup {backup_name}'
        )
        
        messages.success(request, f"Successfully deleted backup: {backup_name}")
    except Exception as e:
        messages.error(request, f"Failed to delete backup: {str(e)}")
        logger.error(f"Delete backup {backup_name} failed: {str(e)}")
    
    return redirect('backup_list')

@login_required
@permission_required('inventory.can_manage_backup')
def download_backup(request, backup_name):
    """Download backup view"""
    backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
    if not os.path.exists(backup_dir):
        messages.error(request, f"Backup {backup_name} does not exist")
        return redirect('backup_list')
    
    try:
        # Create temp dir
        temp_dir = os.path.join(settings.TEMP_DIR, f"download_{backup_name}_{int(time.time())}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create zip file
        zip_file_path = os.path.join(temp_dir, f"{backup_name}.zip")
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add backup info
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, backup_dir))
        
        # Return file
        if os.path.exists(zip_file_path):
            with open(zip_file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="{backup_name}.zip"'
                
                # Log download record
                LogEntry.objects.create(
                    user=request.user,
                    action_type='DOWNLOAD',
                    object_id=backup_name,
                    object_repr=f'Backup: {backup_name}',
                    change_message=f'Downloaded system backup {backup_name}'
                )
                
                # Cleanup temp dir
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
                    
                return response
        else:
            messages.error(request, "Failed to generate backup zip file")
            return redirect('backup_list')
            
    except Exception as e:
        messages.error(request, f"Failed to download backup: {str(e)}")
        logger.error(f"Download backup {backup_name} failed: {str(e)}")
        return redirect('backup_list')

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def manual_backup(request):
    """
    Manual backup API
    """
    if request.method == 'POST':
        try:
            backup_name = f"manual_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = BackupService.create_backup(backup_name=backup_name, user=request.user)
            return JsonResponse({
                'success': True,
                'backup_name': backup_name,
                'message': 'Backup created successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Failed to create backup: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Unsupported request method'
    }, status=405) 