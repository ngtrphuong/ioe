"""
Permission decorators for views.
"""
import functools
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

from inventory.exceptions import AuthorizationError


def permission_required(perm):
    """
    Decorator for views that checks whether a user has a particular permission.
    If not, raises AuthorizationError.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                error_message = f"You do not have permission to perform this action: {perm}"
                raise AuthorizationError(error_message, code="permission_denied")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def group_required(group_name):
    """
    Decorator for views that checks if a user is in a particular group.
    If not, raises AuthorizationError.
    """
    def check_group(user):
        if user.is_superuser:
            return True
        if user.groups.filter(name=group_name).exists():
            return True
        return False
    
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not check_group(request.user):
                error_message = f"You are not in the '{group_name}' group and cannot perform this action"
                raise AuthorizationError(error_message, code="group_required")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def superuser_required(view_func):
    """
    Decorator for views that checks if the user is a superuser.
    If not, raises AuthorizationError.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            error_message = "Superuser permissions are required to perform this action"
            raise AuthorizationError(error_message, code="superuser_required")
        return view_func(request, *args, **kwargs)
    return wrapper


def owner_or_permission_required(owner_field, permission):
    """
    Decorator for views that checks if the user is the owner of the object 
    or has the specified permission.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get the object from the view
            obj = view_func.__globals__['get_object_or_404'](
                view_func.__globals__[owner_field.split('__')[0]], 
                pk=kwargs.get('pk', kwargs.get(f'{owner_field.split("__")[0]}_id'))
            )
            
            # Check if user is the owner
            is_owner = False
            owner_chain = owner_field.split('__')
            owner = obj
            for attr in owner_chain:
                owner = getattr(owner, attr)
            
            is_owner = owner == request.user
            
            # If not owner, check permission
            if not is_owner and not request.user.has_perm(permission):
                error_message = f"You are not the owner of this resource and lack permission: {permission}"
                raise AuthorizationError(error_message, code="not_owner_or_perm_denied")
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def system_admin_required(view_func):
    """
    Decorator that checks whether the user is a system administrator.
    If not, redirect to home page and show a permission error.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser or (
            request.user.groups.filter(name='System Administrator').exists() or 
            request.user.groups.filter(name='admin').exists()
        ):
            return view_func(request, *args, **kwargs)
        else:
            # Redirect to home and show an error message
            from django.contrib import messages
            messages.error(request, "You need system administrator permissions to access this page")
            return redirect('index')
    return wrapper 