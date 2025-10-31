"""
System backup and restore related views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.contrib.admin.models import LogEntry
from django.core import management
from django.utils.text import slugify
import os
import json
import time
import shutil
import logging
import re
import zipfile
from datetime import datetime

from inventory.permissions.decorators import permission_required
from inventory.utils.logging import log_view_access
from inventory.services.backup_service import BackupService

# Getlogger
logger = logging.getLogger(__name__)

def get_dir_size_display(dir_path):
    """Get human-friendly display of directory size"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(dir_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    
    # Convert to appropriate unit
    size_bytes = total_size
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

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
                if os.path.exists(backup_info_file):
                    with open(backup_info_file, 'r', encoding='utf-8') as f:
                        backup_info = json.load(f)
                    
                    backups.append({
                        'name': backup_name,
                        'created_at': datetime.fromisoformat(backup_info.get('created_at', '')),
                        'created_by': backup_info.get('created_by', 'Unknown'),
                        'size': get_dir_size_display(backup_dir),
                    })
            except Exception as e:
                logger.error(f"Failed to read backup info: {str(e)}")
    
    # Sort by creation time
    backups.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render(request, 'inventory/system/backup_list.html', {'backups': backups})

@login_required
@permission_required('inventory.can_manage_backup')
def create_backup(request):
    """Create backup view"""
    # Generate suggested backup name
    now = datetime.now()
    suggested_name = f"backup_{now.strftime('%Y%m%d_%H%M%S')}"
    
    if request.method == 'POST':
        # Get form data
        backup_name = request.POST.get('backup_name', '').strip()
        if not backup_name:
            backup_name = suggested_name
        
        # Validate backup name
        if not re.match(r'^[a-zA-Z0-9_\-]+$', backup_name):
            messages.error(request, "Backup name can only contain letters, digits, underscores, and hyphens.")
            return render(request, 'inventory/system/create_backup.html', {'suggested_name': suggested_name})
        
        # Check if backup already exists
        backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
        if os.path.exists(backup_dir):
            messages.error(request, f"Backup {backup_name} already exists")
            return render(request, 'inventory/system/create_backup.html', {'suggested_name': suggested_name})
        
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # Backup database
            db_file = os.path.join(backup_dir, 'db.json')
            management.call_command('dumpdata', '--exclude', 'auth.permission', '--exclude', 'contenttypes', 
                                  '--exclude', 'sessions.session', '--indent', '4', 
                                  '--output', db_file)
            
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
            
            # Save backup info
            backup_info = {
                'name': backup_name,
                'created_at': now.isoformat(),
                'created_by': request.user.username,
                'description': backup_description,
                'includes_media': backup_media,
            }
            
            backup_info_file = os.path.join(backup_dir, 'backup_info.json')
            with open(backup_info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=4, ensure_ascii=False)
            
            # Log action
            LogEntry.objects.create(
                user=request.user,
                action_flag=1,  # Add
                content_type_id=0,  # Custom content type
                object_id=backup_name,
                object_repr=f'Backup: {backup_name}',
                change_message=f'Created system backup {backup_name}' + (' with media files' if backup_media else '')
            )
            
            messages.success(request, f"Successfully created backup: {backup_name}")
            return redirect('backup_list')
            
        except Exception as e:
            # Backup failed, clean up backup directory
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            
            messages.error(request, f"Failed to create backup: {str(e)}")
            logger.error(f"Failed to create backup: {str(e)}")
            return render(request, 'inventory/system/create_backup.html', {'suggested_name': suggested_name})
    
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
    
    # Get backup info
    backup_info_file = os.path.join(backup_dir, 'backup_info.json')
    backup_info = {}
    if os.path.exists(backup_info_file):
        with open(backup_info_file, 'r', encoding='utf-8') as f:
            backup_info = json.load(f)
    
    if request.method == 'POST':
        # Confirm restore
        confirmed = request.POST.get('confirm') == 'on'
        if not confirmed:
            messages.error(request, "Please confirm you want to restore the backup")
            return render(request, 'inventory/system/restore_backup.html', {
                'backup_name': backup_name,
                'backup_info': backup_info
            })
        
        try:
            # Restore database
            db_file = os.path.join(backup_dir, 'db.json')
            if not os.path.exists(db_file):
                messages.error(request, f"Backup file {db_file} does not exist")
                return redirect('backup_list')
            
            # Execute restore
            management.call_command('loaddata', db_file)
            
            # Restore media files
            restore_media = request.POST.get('restore_media') == 'on'
            if restore_media and backup_info.get('includes_media', False):
                media_dir = os.path.join(backup_dir, 'media')
                if os.path.exists(media_dir):
                    # Clear existing media directory
                    if os.path.exists(settings.MEDIA_ROOT):
                        for item in os.listdir(settings.MEDIA_ROOT):
                            item_path = os.path.join(settings.MEDIA_ROOT, item)
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                    
                    # Copy media files from backup
                    for item in os.listdir(media_dir):
                        src_path = os.path.join(media_dir, item)
                        dst_path = os.path.join(settings.MEDIA_ROOT, item)
                        if os.path.isdir(src_path):
                            if os.path.exists(dst_path):
                                shutil.rmtree(dst_path)
                            shutil.copytree(src_path, dst_path)
                        else:
                            if os.path.exists(dst_path):
                                os.remove(dst_path)
                            shutil.copy2(src_path, dst_path)
            
            # Log action
            LogEntry.objects.create(
                user=request.user,
                action_flag=2,  # Modify
                content_type_id=0,  # Custom content type
                object_id=backup_name,
                object_repr=f'Restored backup: {backup_name}',
                change_message=f'Restored system backup {backup_name}' + (' with media files' if restore_media else '')
            )
            
            messages.success(request, f"Successfully restored backup: {backup_name}")
            return redirect('system_settings')
            
        except Exception as e:
            messages.error(request, f"Failed to restore backup: {str(e)}")
            logger.error(f"Failed to restore backup: {str(e)}")
            return render(request, 'inventory/system/restore_backup.html', {
                'backup_name': backup_name,
                'backup_info': backup_info
            })
    
    return render(request, 'inventory/system/restore_backup.html', {
        'backup_name': backup_name,
        'backup_info': backup_info
    })

@login_required
@permission_required('inventory.can_manage_backup')
def delete_backup(request, backup_name):
    """Delete backup view"""
    # Check if backup exists
    backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
    if not os.path.exists(backup_dir):
        messages.error(request, f"Backup {backup_name} does not exist")
        return redirect('backup_list')
    
    if request.method == 'POST':
        # Confirm deletion
        confirmed = request.POST.get('confirm') == 'on'
        if not confirmed:
            messages.error(request, "Please confirm you want to delete the backup")
            return render(request, 'inventory/system/delete_backup.html', {'backup_name': backup_name})
        
        try:
            # Delete backup directory
            shutil.rmtree(backup_dir)
            
            # Log action
            LogEntry.objects.create(
                user=request.user,
                action_flag=3,  # Delete
                content_type_id=0,  # Custom content type
                object_id=backup_name,
                object_repr=f'Deleted backup: {backup_name}',
                change_message=f'Deleted system backup {backup_name}'
            )
            
            messages.success(request, f"Successfully deleted backup: {backup_name}")
            return redirect('backup_list')
            
        except Exception as e:
            messages.error(request, f"Failed to delete backup: {str(e)}")
            logger.error(f"Failed to delete backup: {str(e)}")
            return render(request, 'inventory/system/delete_backup.html', {'backup_name': backup_name})
    
    return render(request, 'inventory/system/delete_backup.html', {'backup_name': backup_name})

@login_required
@permission_required('inventory.can_manage_backup')
def download_backup(request, backup_name):
    """Download backup view"""
    # Check if backup exists
    backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
    if not os.path.exists(backup_dir):
        messages.error(request, f"Backup {backup_name} does not exist")
        return redirect('backup_list')
    
    # Create temporary ZIP file
    temp_file = os.path.join(settings.TEMP_DIR, f"{backup_name}.zip")
    
    try:
        # Create ZIP file
        with zipfile.ZipFile(temp_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add backup files
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, os.path.dirname(backup_dir)))
        
        # Open file for download
        with open(temp_file, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{backup_name}.zip"'
            
            # Log action
            LogEntry.objects.create(
                user=request.user,
                action_flag=1,  # Add
                content_type_id=0,  # Custom content type
                object_id=backup_name,
                object_repr=f'Downloaded backup: {backup_name}',
                change_message=f'Downloaded system backup {backup_name}'
            )
            
            return response
            
    except Exception as e:
        messages.error(request, f"Failed to download backup: {str(e)}")
        logger.error(f"Failed to download backup: {str(e)}")
        return redirect('backup_list')
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)

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
                'message': f'Failed to create manual backup: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Unsupported request method'
    }, status=405) 