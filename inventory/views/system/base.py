"""
System settings and information related views
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
import os
import platform
import django
import psutil
import time
import logging

from inventory.permissions.decorators import permission_required
from inventory.utils.logging import log_view_access

# Get logger
logger = logging.getLogger(__name__)

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def system_settings(request):
    """
    System settings view
    """
    context = {
        'settings': {
            'debug_mode': settings.DEBUG,
            'media_root': settings.MEDIA_ROOT,
            'timezone': settings.TIME_ZONE,
            'database_engine': settings.DATABASES['default']['ENGINE'],
            'version': getattr(settings, 'VERSION', '1.0.0'),
        }
    }
    return render(request, 'inventory/system/settings.html', context)

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def system_info(request):
    """
    System information view showing system status and environment
    """
    # Get system information
    system_info = {
        'os': platform.system(),
        'os_version': platform.version(),
        'python_version': platform.python_version(),
        'django_version': django.__version__,
        'cpu_count': psutil.cpu_count(),
        'memory_total': round(psutil.virtual_memory().total / (1024 * 1024 * 1024), 2),  # GB
        'memory_available': round(psutil.virtual_memory().available / (1024 * 1024 * 1024), 2),  # GB
        'disk_total': round(psutil.disk_usage('/').total / (1024 * 1024 * 1024), 2),  # GB
        'disk_free': round(psutil.disk_usage('/').free / (1024 * 1024 * 1024), 2),  # GB
        'hostname': platform.node(),
        'server_time': timezone.now(),
        'uptime': round((time.time() - psutil.boot_time()) / 3600, 2),  # hours
    }
    
    # Get database statistics
    from django.db import connection
    db_stats = {}
    
    # Record count for each main table
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM inventory_product")
        db_stats['product_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM inventory_category")
        db_stats['category_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM inventory_inventory")
        db_stats['inventory_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM inventory_sale")
        db_stats['sale_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM inventory_member")
        db_stats['member_count'] = cursor.fetchone()[0]
    
    # Directory and file size
    media_size = 0
    if os.path.exists(settings.MEDIA_ROOT):
        for dirpath, dirnames, filenames in os.walk(settings.MEDIA_ROOT):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                media_size += os.path.getsize(fp)
    
    # Convert to MB
    media_size_mb = round(media_size / (1024 * 1024), 2)
    
    # System log statistics
    log_file = os.path.join(settings.BASE_DIR, 'logs', 'inventory.log')
    log_size_mb = 0
    log_entries = 0
    if os.path.exists(log_file):
        log_size_mb = round(os.path.getsize(log_file) / (1024 * 1024), 2)
        # Simple approximation for log entry count
        with open(log_file, 'r') as f:
            log_entries = sum(1 for _ in f)
    
    # Combine all info
    context = {
        'system_info': system_info,
        'db_stats': db_stats,
        'media_size_mb': media_size_mb,
        'log_size_mb': log_size_mb,
        'log_entries': log_entries,
    }
    
    return render(request, 'inventory/system/system_info.html', context)

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def store_settings(request):
    """
    Store settings view
    """
    from inventory.models import Store
    
    # Get current store settings
    store = Store.objects.first()
    
    if request.method == 'POST':
        # Update store settings
        store_name = request.POST.get('store_name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        website = request.POST.get('website')
        store_description = request.POST.get('store_description')
        logo = request.FILES.get('logo')
        
        if not store:
            store = Store()
        
        store.name = store_name
        store.address = address
        store.phone = phone
        store.email = email
        store.website = website
        store.description = store_description
        
        if logo:
            store.logo = logo
        
        store.save()
        messages.success(request, 'Store settings updated')
        return redirect('store_settings')
    
    return render(request, 'inventory/system/store_settings.html', {'store': store})

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def store_list(request):
    """
    Store list view
    """
    from inventory.models import Store
    
    stores = Store.objects.all()
    return render(request, 'inventory/system/store_list.html', {'stores': stores})

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def delete_store(request, store_id):
    """
    Store delete view
    """
    from inventory.models import Store
    
    store = Store.objects.get(pk=store_id)
    store.delete()
    messages.success(request, f'Store "{store.name}" has been deleted')
    return redirect('store_list')

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def system_maintenance(request):
    """
    System maintenance view providing cleanup and optimization
    """
    # Execute maintenance operations
    if request.method == 'POST':
        operation = request.POST.get('operation')
        
        if operation == 'clear_sessions':
            # Clean up expired sessions
            from django.contrib.sessions.models import Session
            Session.objects.filter(expire_date__lt=timezone.now()).delete()
            messages.success(request, 'Expired sessions have been cleared')
            
        elif operation == 'clear_logs':
            # Clean up log file (keep last 10000 lines)
            log_file = os.path.join(settings.BASE_DIR, 'logs', 'inventory.log')
            if os.path.exists(log_file):
                try:
                    # Read last 10000 lines
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        last_lines = lines[-10000:] if len(lines) > 10000 else lines
                    
                    # Rewrite log file
                    with open(log_file, 'w') as f:
                        f.writelines(last_lines)
                    
                    messages.success(request, 'Log file cleared')
                except Exception as e:
                    messages.error(request, f'Failed to clear logs: {str(e)}')
            
        elif operation == 'optimize_db':
            # Optimize database
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    if 'sqlite' in connection.vendor:
                        cursor.execute("VACUUM")
                    elif 'postgresql' in connection.vendor:
                        cursor.execute("VACUUM ANALYZE")
                    elif 'mysql' in connection.vendor:
                        cursor.execute("OPTIMIZE TABLE")
                
                messages.success(request, 'Database optimized')
            except Exception as e:
                messages.error(request, f'Failed to optimize database: {str(e)}')
        
        return redirect('system_maintenance')
    
    # Get system status information
    disk_usage = psutil.disk_usage('/')
    disk_usage_percent = disk_usage.percent
    memory_usage = psutil.virtual_memory()
    memory_usage_percent = memory_usage.percent
    
    # Log file size
    log_file = os.path.join(settings.BASE_DIR, 'logs', 'inventory.log')
    log_size_mb = 0
    if os.path.exists(log_file):
        log_size_mb = round(os.path.getsize(log_file) / (1024 * 1024), 2)
    
    # Session count
    from django.contrib.sessions.models import Session
    active_sessions = Session.objects.filter(expire_date__gt=timezone.now()).count()
    expired_sessions = Session.objects.filter(expire_date__lt=timezone.now()).count()
    
    context = {
        'disk_usage_percent': disk_usage_percent,
        'memory_usage_percent': memory_usage_percent,
        'log_size_mb': log_size_mb,
        'active_sessions': active_sessions,
        'expired_sessions': expired_sessions,
    }
    
    return render(request, 'inventory/system/maintenance.html', context) 