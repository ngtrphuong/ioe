"""
System log management related views
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.admin.models import LogEntry
from django.db.models import Q
from django.utils.html import escape
from django.http import FileResponse
from django.utils import timezone
import os
import logging
import re
from datetime import datetime, timedelta

from inventory.permissions.decorators import permission_required
from inventory.utils.logging import log_view_access

logger = logging.getLogger(__name__)

@login_required
@permission_required('is_superuser')
@log_view_access('OTHER')
def log_list(request):
    """System log list view"""
    # Get query parameters
    search_query = request.GET.get('q', '')
    action_type = request.GET.get('action_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build filtering conditions
    query = LogEntry.objects.all()
    
    if search_query:
        query = query.filter(
            Q(object_repr__icontains=search_query) | 
            Q(change_message__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    if action_type:
        query = query.filter(action_flag=int(action_type))
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(action_time__gte=date_from_obj)
        except ValueError:
            messages.error(request, "Invalid start date format")
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Add a day to include the entire end date
            date_to_obj = date_to_obj + timedelta(days=1)
            query = query.filter(action_time__lt=date_to_obj)
        except ValueError:
            messages.error(request, "Invalid end date format")
    
    # Pagination
    page_size = int(request.GET.get('page_size', 50))
    paginator = Paginator(query.order_by('-action_time'), page_size)
    page_number = request.GET.get('page', 1)
    logs = paginator.get_page(page_number)
    
    # Prepare statistics
    stats = {
        'total': LogEntry.objects.count(),
        'add': LogEntry.objects.filter(action_flag=1).count(),
        'change': LogEntry.objects.filter(action_flag=2).count(),
        'delete': LogEntry.objects.filter(action_flag=3).count(),
    }
    
    # Prepare file log data
    log_files = []
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
    
    if os.path.exists(log_dir):
        for file_name in os.listdir(log_dir):
            if file_name.endswith('.log'):
                file_path = os.path.join(log_dir, file_name)
                try:
                    size = os.path.getsize(file_path)
                    modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # Convert bytes to human readable format
                    if size < 1024:
                        size_str = f"{size} bytes"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.2f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.2f} MB"
                    
                    log_files.append({
                        'name': file_name,
                        'path': file_path,
                        'size': size_str,
                        'modified': modified,
                    })
                except OSError:
                    continue
                    
        # Sort by modification time
        log_files.sort(key=lambda x: x['modified'], reverse=True)
    
    context = {
        'logs': logs,
        'stats': stats,
        'log_files': log_files,
        'search_query': search_query,
        'action_type': action_type,
        'date_from': date_from,
        'date_to': date_to,
        'page_size': page_size,
    }
    
    return render(request, 'inventory/system/log_list.html', context)

@login_required
@permission_required('is_superuser')
@log_view_access('OTHER')
def clear_logs(request):
    """Clear system logs view"""
    # Default date is 30 days ago
    default_date = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        log_type = request.POST.get('log_type', '')
        date_before = request.POST.get('date_before', '')
        confirm = request.POST.get('confirm') == 'on'
        
        if not confirm:
            messages.error(request, "Please confirm you want to clear logs")
            return redirect('log_list')
        
        try:
            # Filter by date
            if date_before:
                try:
                    date_before_obj = datetime.strptime(date_before, '%Y-%m-%d')
                    date_before_obj = date_before_obj.replace(tzinfo=timezone.get_current_timezone())
                    query = LogEntry.objects.filter(action_time__lt=date_before_obj)
                except ValueError:
                    messages.error(request, "Invalid date format")
                    return redirect('log_list')
            else:
                query = LogEntry.objects.all()
            
            # Filter by type
            if log_type and log_type.isdigit():
                query = query.filter(action_flag=int(log_type))
            
            # Get the number of records to delete
            count = query.count()
            
            # Delete logs
            query.delete()
            
            # Log the operation
            logger.info(f"User {request.user.username} cleared system logs: type {log_type}, before date {date_before}, total {count} records")
            
            messages.success(request, f"Successfully cleared {count} log records")
            
        except Exception as e:
            messages.error(request, f"Failed to clear logs: {str(e)}")
            logger.error(f"Failed to clear logs: {str(e)}")
        
        return redirect('log_list')
    
    context = {
        'default_date': default_date
    }
    
    return render(request, 'inventory/system/clear_logs.html', context)

@login_required
@permission_required('is_superuser')
def view_log_file(request, file_name):
    """View log file content"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
    file_path = os.path.join(log_dir, file_name)
    
    # Security check, ensure file name is a valid log file name
    if not re.match(r'^[\w.-]+\.log$', file_name) or '..' in file_name:
        messages.error(request, "Invalid log file name")
        return redirect('log_list')
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        messages.error(request, f"Log file {file_name} does not exist")
        return redirect('log_list')
    
    # Get line limit
    lines = request.GET.get('lines', 500)
    try:
        lines = int(lines)
    except ValueError:
        lines = 500
    
    # Get file content (last specified lines)
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            # Read all lines and reverse
            all_lines = f.readlines()
            total_lines = len(all_lines)
            
            # Get the last lines
            if lines >= total_lines:
                content = ''.join(all_lines)
            else:
                content = ''.join(all_lines[-lines:])
            
            # Convert content to safe HTML
            content = escape(content)
            
            return render(request, 'inventory/system/view_log_file.html', {
                'file_name': file_name,
                'content': content,
                'lines': lines,
                'total_lines': total_lines,
            })
            
    except Exception as e:
        messages.error(request, f"Failed to read log file: {str(e)}")
        logger.error(f"Failed to read log file: {str(e)}")
        return redirect('log_list')

@login_required
@permission_required('is_superuser')
def download_log_file(request, file_name):
    """Download log file"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
    file_path = os.path.join(log_dir, file_name)
    
    # Security check, ensure file name is a valid log file name
    if not re.match(r'^[\w.-]+\.log$', file_name) or '..' in file_name:
        messages.error(request, "Invalid log file name")
        return redirect('log_list')
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        messages.error(request, f"Log file {file_name} does not exist")
        return redirect('log_list')
    
    try:
        # Log download operation
        LogEntry.objects.create(
            user=request.user,
            action_flag=1,
            content_type_id=0,
            object_id=file_name,
            object_repr=f'Downloaded log: {file_name}',
            change_message=f'Downloaded log file {file_name}'
        )
        
        # Return file response
        response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_name)
        return response
        
    except Exception as e:
        messages.error(request, f"Failed to download log file: {str(e)}")
        logger.error(f"Failed to download log file: {str(e)}")
        return redirect('log_list')

@login_required
@permission_required('is_superuser')
def delete_log_file(request, file_name):
    """Delete log file"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
    file_path = os.path.join(log_dir, file_name)
    
    # Security check, ensure file name is a valid log file name
    if not re.match(r'^[\w.-]+\.log$', file_name) or '..' in file_name:
        messages.error(request, "Invalid log file name")
        return redirect('log_list')
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        messages.error(request, f"Log file {file_name} does not exist")
        return redirect('log_list')
    
    if request.method == 'POST':
        # Confirm deletion
        confirm = request.POST.get('confirm') == 'on'
        if not confirm:
            messages.error(request, "Please confirm you want to delete this log file")
            return render(request, 'inventory/system/delete_log_file.html', {'file_name': file_name})
        
        try:
            # Delete file
            os.remove(file_path)
            
            # Log deletion operation
            LogEntry.objects.create(
                user=request.user,
                action_flag=3,
                content_type_id=0,
                object_id=file_name,
                object_repr=f'Deleted log: {file_name}',
                change_message=f'Deleted log file {file_name}'
            )
            
            messages.success(request, f"Successfully deleted log file {file_name}")
            return redirect('log_list')
            
        except Exception as e:
            messages.error(request, f"Failed to delete log file: {str(e)}")
            logger.error(f"Failed to delete log file: {str(e)}")
            return redirect('log_list')
    
    return render(request, 'inventory/system/delete_log_file.html', {'file_name': file_name}) 