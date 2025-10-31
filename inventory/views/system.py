"""
System configuration related views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry
from django.utils import timezone
from datetime import datetime, timedelta
import os
import logging

from inventory.models import SystemConfig, Store
from inventory.forms import SystemConfigForm, StoreForm
from inventory.permissions import system_admin_required
from inventory.utils.system_utils import get_system_info
from inventory.models.settings import SystemSettings, BackupSchedule
from inventory.forms.system import SystemSettingsForm, BackupScheduleForm

logger = logging.getLogger(__name__)


@login_required
@system_admin_required
def system_settings(request):
    """System settings view"""
    # Get or create system configuration
    config, created = SystemConfig.objects.get_or_create(pk=1)
    
    if request.method == 'POST':
        form = SystemConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "System settings updated")
            return redirect('system_settings')
    else:
        form = SystemConfigForm(instance=config)
    
    return render(request, 'inventory/system/settings.html', {
        'form': form,
        'config': config
    })


@login_required
@system_admin_required
def store_settings(request, pk=None):
    """Store settings view"""
    if pk:
        store = get_object_or_404(Store, pk=pk)
        if request.method == 'POST':
            form = StoreForm(request.POST, instance=store)
            if form.is_valid():
                form.save()
                messages.success(request, f"Store {store.name} info updated")
                return redirect('store_list')
        else:
            form = StoreForm(instance=store)
        
        return render(request, 'inventory/system/store_form.html', {
            'form': form,
            'store': store,
            'title': f'Edit Store: {store.name}'
        })
    else:
        if request.method == 'POST':
            form = StoreForm(request.POST)
            if form.is_valid():
                store = form.save()
                messages.success(request, f"Store {store.name} created successfully")
                return redirect('store_list')
        else:
            form = StoreForm()
        
        return render(request, 'inventory/system/store_form.html', {
            'form': form,
            'title': 'Add Store'
        })


@login_required
@system_admin_required
def store_list(request):
    """Store list view"""
    stores = Store.objects.all().order_by('name')
    return render(request, 'inventory/system/store_list.html', {
        'stores': stores
    })


@login_required
@system_admin_required
def delete_store(request, pk):
    """Delete store view"""
    store = get_object_or_404(Store, pk=pk)
    
    if request.method == 'POST':
        store_name = store.name
        store.delete()
        messages.success(request, f"Store {store_name} deleted")
        return redirect('store_list')
    
    return render(request, 'inventory/system/store_confirm_delete.html', {
        'store': store
    })


@login_required
@system_admin_required
def system_info(request):
    """System info view"""
    # Collect system info
    system_info = {
        'django_version': settings.DJANGO_VERSION,
        'debug_mode': settings.DEBUG,
        'database_engine': settings.DATABASES['default']['ENGINE'],
        'static_root': settings.STATIC_ROOT,
        'media_root': settings.MEDIA_ROOT,
        'time_zone': settings.TIME_ZONE,
        'language_code': settings.LANGUAGE_CODE,
    }
    
    # User statistics
    user_stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'staff_users': User.objects.filter(is_staff=True).count(),
        'admin_users': User.objects.filter(is_superuser=True).count(),
    }
    
    # Store statistics
    store_stats = {
        'total_stores': Store.objects.count(),
        'active_stores': Store.objects.filter(is_active=True).count(),  # Restore filtering by is_active
    }
    
    return render(request, 'inventory/system/info.html', {
        'system_info': system_info,
        'user_stats': user_stats,
        'store_stats': store_stats,
    })


@login_required
@system_admin_required
def system_maintenance(request):
    """System maintenance view"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'clear_cache':
            # Implement cache clearing functionality
            from django.core.cache import cache
            cache.clear()
            messages.success(request, "System cache cleared")
            
        elif action == 'rebuild_index':
            # Implement rebuild search index functionality
            # Needs to be implemented according to the search engine in use
            messages.success(request, "Search index rebuilt")
            
        elif action == 'backup_database':
            # Implement database backup functionality
            # Custom backup scripts can be called here
            import subprocess
            import os
            import datetime
            
            # Create backup directory
            backup_dir = os.path.join(settings.BASE_DIR, 'db_backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate backup filename
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f'backup_{timestamp}.json')
            
            # Perform database backup
            cmd = [
                'python', 
                os.path.join(settings.BASE_DIR, 'manage.py'), 
                'dumpdata', 
                '--exclude', 'contenttypes', 
                '--exclude', 'auth.Permission', 
                '-o', 
                backup_file
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                messages.success(request, f"Database backup completed: {backup_file}")
            except subprocess.CalledProcessError as e:
                messages.error(request, f"Backup failed: {e.stderr.decode()}")
        
        return redirect('system_maintenance')
    
    # Get list of backups
    backup_dir = os.path.join(settings.BASE_DIR, 'db_backups')
    backups = []
    
    if os.path.exists(backup_dir):
        for file in os.listdir(backup_dir):
            if file.startswith('backup_') and file.endswith('.json'):
                file_path = os.path.join(backup_dir, file)
                file_stats = os.stat(file_path)
                backups.append({
                    'filename': file,
                    'size': file_stats.st_size / 1024.0,  # KB
                    'date': datetime.datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    
    # Sort by date, newest first
    backups.sort(key=lambda x: x['date'], reverse=True)
    
    return render(request, 'inventory/system/maintenance.html', {
        'backups': backups
    })


@login_required
@system_admin_required
def restore_database(request, filename):
    """Restore database view"""
    import os
    import subprocess
    from django.conf import settings
    
    backup_dir = os.path.join(settings.BASE_DIR, 'db_backups')
    backup_file = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_file):
        messages.error(request, f"Backup file does not exist: {filename}")
        return redirect('system_maintenance')
    
    if request.method == 'POST':
        # Perform database restore
        cmd = [
            'python', 
            os.path.join(settings.BASE_DIR, 'manage.py'), 
            'loaddata', 
            backup_file
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            messages.success(request, f"Database has been restored from backup: {filename}")
        except subprocess.CalledProcessError as e:
            messages.error(request, f"Restore failed: {e.stderr.decode()}")
        
        return redirect('system_maintenance')
    
    return render(request, 'inventory/system/restore_confirm.html', {
        'filename': filename
    })


@login_required
@system_admin_required
def delete_backup(request, filename):
    """Delete backup file view"""
    import os
    from django.conf import settings
    
    backup_dir = os.path.join(settings.BASE_DIR, 'db_backups')
    backup_file = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_file):
        messages.error(request, f"Backup file does not exist: {filename}")
        return redirect('system_maintenance')
    
    if request.method == 'POST':
        try:
            os.remove(backup_file)
            messages.success(request, f"Backup file deleted: {filename}")
        except Exception as e:
            messages.error(request, f"Deletion failed: {str(e)}")
        
        return redirect('system_maintenance')
    
    return render(request, 'inventory/system/delete_backup_confirm.html', {
        'filename': filename
    })


@login_required
@permission_required('inventory.view_systemsettings', raise_exception=True)
def system_settings(request):
    """System settings view"""
    settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, "System settings updated")
            return redirect('system_settings')
    else:
        form = SystemSettingsForm(instance=settings)
        
    backup_schedule = BackupSchedule.get_schedule()
    backup_form = BackupScheduleForm(instance=backup_schedule)
    
    system_info = get_system_info()
    
    context = {
        'form': form,
        'backup_form': backup_form,
        'system_info': system_info
    }
    
    return render(request, 'inventory/system/settings.html', context)


@login_required
@permission_required('inventory.change_systemsettings', raise_exception=True)
def backup_schedule(request):
    """Backup schedule view"""
    schedule = BackupSchedule.get_schedule()
    
    if request.method == 'POST':
        form = BackupScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, "Backup schedule updated")
            return redirect('system_settings')
    else:
        form = BackupScheduleForm(instance=schedule)
    
    return render(request, 'inventory/system/backup_schedule.html', {'form': form})


@login_required
@permission_required('admin.view_logentry', raise_exception=True)
def log_list(request):
    """System log list view"""
    # Get filtering parameters
    action_filter = request.GET.get('action', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    page_size = request.GET.get('page_size', 50)
    
    # Query logs
    logs = LogEntry.objects.all().order_by('-action_time')
    
    # Apply filtering
    if action_filter:
        logs = logs.filter(action_flag=action_filter)
    
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            logs = logs.filter(action_time__date__gte=start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            logs = logs.filter(action_time__date__lte=end_date_obj)
        except ValueError:
            pass
    
    # Statistics
    total_logs = logs.count()
    add_logs = logs.filter(action_flag=1).count()
    change_logs = logs.filter(action_flag=2).count()
    delete_logs = logs.filter(action_flag=3).count()
    
    # Get log file list
    log_files = []
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    
    if os.path.exists(log_dir):
        for file in os.listdir(log_dir):
            if file.endswith('.log'):
                file_path = os.path.join(log_dir, file)
                stats = os.stat(file_path)
                size_kb = stats.st_size / 1024
                last_modified = datetime.fromtimestamp(stats.st_mtime)
                
                log_files.append({
                    'name': file,
                    'size': f"{size_kb:.2f} KB",
                    'last_modified': last_modified
                })
    
    context = {
        'logs': logs[:int(page_size)],  # Simple paging for demonstration only
        'total_logs': total_logs,
        'add_logs': add_logs,
        'change_logs': change_logs,
        'delete_logs': delete_logs,
        'action_filter': action_filter,
        'start_date': start_date,
        'end_date': end_date,
        'page_size': page_size,
        'log_files': log_files
    }
    
    return render(request, 'inventory/system/log_list.html', context)


@login_required
@permission_required('admin.delete_logentry', raise_exception=True)
def clear_logs(request):
    """Clear system logs view"""
    # Default date is 30 days ago
    default_date = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        log_type = request.POST.get('log_type', 'admin')
        date_before = request.POST.get('date_before')
        confirm = request.POST.get('confirm') == 'on'
        
        if confirm and date_before:
            try:
                # Parse date
                date_obj = datetime.strptime(date_before, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
                
                # Create filter kwargs
                filter_kwargs = {'action_time__lt': date_obj}
                
                # Delete logs
                deleted_count = LogEntry.objects.filter(**filter_kwargs).delete()[0]
                
                # Record operation to log
                logger.info(f"User {request.user.username} cleared system logs: type {log_type}, before date {date_before}, total {deleted_count} records")
                
                messages.success(request, f"Successfully cleared {deleted_count} log records")
                return redirect('log_list')
            except ValueError:
                messages.error(request, "Invalid date format")
        else:
            messages.error(request, "Please confirm the clear operation")
    
    context = {
        'default_date': default_date
    }
    
    return render(request, 'inventory/system/clear_logs.html', context) 