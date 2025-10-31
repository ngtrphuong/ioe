from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType

from ...models.common import OperationLog


@login_required
@permission_required('auth.view_user', raise_exception=True)
def user_list(request):
    """User list view"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    is_active = request.GET.get('is_active', '')
    user_group = request.GET.get('group', '')
    
    # Base queryset
    users = User.objects.select_related('profile').prefetch_related('groups').all()
    
    # Apply filters
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if is_active:
        users = users.filter(is_active=(is_active == 'true'))
    
    if user_group:
        users = users.filter(groups__id=user_group)
    
    # Get user groups
    groups = Group.objects.all()
    
    context = {
        'users': users,
        'groups': groups,
        'search_query': search_query,
        'is_active': is_active,
        'user_group': user_group
    }
    
    return render(request, 'inventory/system/user_list.html', context)


@login_required
@permission_required('auth.add_user', raise_exception=True)
def user_create(request):
    """Create user view"""
    groups = Group.objects.all()
    
    # Ensure sales group exists
    sales_group, created = Group.objects.get_or_create(name='Salesperson')
    
    # If the group was newly created, set its permissions
    if created:
        # Sales-related permissions
        content_types = ContentType.objects.filter(
            Q(app_label='inventory', model='sale') |
            Q(app_label='inventory', model='saleitem')
        )
        permissions = Permission.objects.filter(content_type__in=content_types)
        sales_group.permissions.add(*permissions)
        # Log creation
        OperationLog.objects.create(
            operator=request.user,
            operation_type='ADD',
            details=f'Created Salesperson user group and set permissions',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        email = request.POST.get('email', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        group_ids = request.POST.getlist('groups')
        
        # Form validation
        errors = []
        
        # Username validation
        if not username:
            errors.append('Username cannot be empty')
        elif User.objects.filter(username=username).exists():
            errors.append('Username already exists')
        
        # Password validation
        if not password:
            errors.append('Password cannot be empty')
        elif len(password) < 8:
            errors.append('Password must be at least 8 characters')
        elif password != password_confirm:
            errors.append('Passwords do not match')
        
        # If there are errors, return them
        if errors:
            messages.error(request, '\n'.join(errors))
            return render(request, 'inventory/system/user_create.html', {
                'groups': groups,
                'form_data': request.POST
            })
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_staff=is_staff,
            is_superuser=is_superuser
        )
        
        # Assign user group
        if group_ids:
            selected_groups = Group.objects.filter(id__in=group_ids)
            user.groups.add(*selected_groups)
        
        # Log operation
        OperationLog.objects.create(
            operator=request.user,
            operation_type='ADD',
            details=f'Created user: {username}',
            related_object_id=user.id,
            related_content_type=ContentType.objects.get_for_model(user),
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        messages.success(request, f'User {username} created successfully')
        return redirect('user_list')
    
    return render(request, 'inventory/system/user_create.html', {
        'groups': groups
    })


@login_required
@permission_required('auth.change_user', raise_exception=True)
def user_update(request, pk):
    """Update user view"""
    user = get_object_or_404(User, pk=pk)
    groups = Group.objects.all()
    
    if request.method == 'POST':
        email = request.POST.get('email', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        group_ids = request.POST.getlist('groups')
        new_password = request.POST.get('new_password', '')
        new_password_confirm = request.POST.get('new_password_confirm', '')
        
        # Form validation
        errors = []
        
        # Password validation
        if new_password:
            if len(new_password) < 8:
                errors.append('Password must be at least 8 characters')
            elif new_password != new_password_confirm:
                errors.append('Passwords do not match')
        
        # If there are errors, return them
        if errors:
            messages.error(request, '\n'.join(errors))
            return render(request, 'inventory/system/user_update.html', {
                'user': user,
                'groups': groups,
                'form_data': request.POST
            })
        
        # Update user information
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = is_active
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        
        # If a new password is provided, update it
        if new_password:
            user.set_password(new_password)
        
        user.save()
        
        # Update user groups
        user.groups.clear()
        if group_ids:
            selected_groups = Group.objects.filter(id__in=group_ids)
            user.groups.add(*selected_groups)
        
        # Log operation
        OperationLog.objects.create(
            operator=request.user,
            operation_type='CHANGE',
            details=f'Updated user: {user.username}',
            related_object_id=user.id,
            related_content_type=ContentType.objects.get_for_model(user),
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        messages.success(request, f'User {user.username} updated successfully')
        return redirect('user_list')
    
    return render(request, 'inventory/system/user_update.html', {
        'user': user,
        'groups': groups
    })


@login_required
@permission_required('auth.delete_user', raise_exception=True)
def user_delete(request, pk):
    """Delete user view"""
    user = get_object_or_404(User, pk=pk)
    
    # Prevent deleting yourself
    if user == request.user:
        messages.error(request, 'Cannot delete the currently logged-in user')
        return redirect('user_list')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        
        # Log operation
        OperationLog.objects.create(
            operator=request.user,
            operation_type='DELETE',
            details=f'Deleted user: {username}',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        messages.success(request, f'User {username} deleted')
        return redirect('user_list')
    
    return render(request, 'inventory/system/user_delete.html', {
        'user': user
    })


@login_required
@permission_required('auth.view_user', raise_exception=True)
def user_detail(request, pk):
    """User detail view"""
    user = get_object_or_404(User, pk=pk)
    
    # Get user's recent operation logs
    logs = OperationLog.objects.filter(operator=user).order_by('-timestamp')[:20]
    
    return render(request, 'inventory/system/user_detail.html', {
        'user': user,
        'logs': logs
    }) 