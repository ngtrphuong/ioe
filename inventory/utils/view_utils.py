"""View utility functions to reduce duplicate code in views."""
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from inventory.models import OperationLog

def log_operation(user, operation_type, details, related_object=None):
    """
    Generic helper to record an operation log entry.
    
    Args:
        user: User performing the action
        operation_type: Operation type
        details: Operation details
        related_object: Related object
    """
    log_entry = OperationLog(
        operator=user,
        operation_type=operation_type,
        details=details
    )
    
    if related_object:
        content_type = ContentType.objects.get_for_model(related_object)
        log_entry.related_content_type = content_type
        log_entry.related_object_id = related_object.id
    
    log_entry.save()
    return log_entry

def handle_form_submission(request, form_class, template_name, success_url, 
                          success_message, instance=None, extra_context=None, 
                          pre_save_callback=None, post_save_callback=None):
    """
    Generic helper to process form submissions.
    
    Args:
        request: HTTP request
        form_class: Form class
        template_name: Template name
        success_url: URL to redirect to on success
        success_message: Success message
        instance: Instance for edit forms
        extra_context: Extra context data
        pre_save_callback: Callback to invoke before saving
        post_save_callback: Callback to invoke after saving
        
    Returns:
        HttpResponse: Response object
    """
    from django.shortcuts import render, redirect
    
    context = extra_context or {}
    
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=instance) if instance else form_class(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            
            # Invoke pre-save callback if provided
            if pre_save_callback:
                pre_save_callback(obj, form)
                
            obj.save()
            form.save_m2m()  # Save many-to-many relations
            
            # Invoke post-save callback if provided
            if post_save_callback:
                post_save_callback(obj, form)
                
            messages.success(request, success_message)
            return redirect(success_url)
    else:
        form = form_class(instance=instance) if instance else form_class()
    
    context['form'] = form
    return render(request, template_name, context)

def get_object_with_check(model_class, object_id, user=None, permission=None):
    """
    Generic helper to get an object and optionally check permission.
    
    Args:
        model_class: Model class
        object_id: Object ID
        user: User object
        permission: Permission codename to check
        
    Returns:
        Model: The fetched object
    """
    obj = get_object_or_404(model_class, id=object_id)
    
    # If permission check is required
    if user and permission and not user.has_perm(permission):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied()
        
    return obj

def search_objects(queryset, search_term, search_fields):
    """
    Generic search helper.
    
    Args:
        queryset: Initial queryset
        search_term: Search term
        search_fields: List of fields to search
        
    Returns:
        QuerySet: Filtered queryset
    """
    if not search_term:
        return queryset
        
    q_objects = Q()
    for field in search_fields:
        q_objects |= Q(**{f"{field}__icontains": search_term})
        
    return queryset.filter(q_objects)

def require_ajax(view_func):
    """
    Decorator: ensure the view can only be called via AJAX.
    
    Args:
        view_func: The view function to wrap
        
    Returns:
        Wrapped view function
    """
    from django.http import HttpResponseBadRequest
    from functools import wraps
    
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return HttpResponseBadRequest('This endpoint only accepts AJAX requests')
        return view_func(request, *args, **kwargs)
    return wrapped

def require_post(view_func):
    """
    Decorator: ensure the view can only be called via POST method.
    
    Args:
        view_func: The view function to wrap
        
    Returns:
        Wrapped view function
    """
    from django.http import HttpResponseNotAllowed
    from functools import wraps
    
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'], 'This endpoint only accepts POST requests')
        return view_func(request, *args, **kwargs)
    return wrapped

def get_referer_url(request, default_url='/'):
    """
    Get the request's Referer URL or return the default URL.
    
    Args:
        request: HTTP request object
        default_url: Default URL to return
        
    Returns:
        str: Referer URL or the default URL
    """
    referer = request.META.get('HTTP_REFERER')
    return referer if referer else default_url

def get_int_param(request, param_name, default=None):
    """
    Get an integer parameter from the request.
    
    Args:
        request: HTTP request object
        param_name: Parameter name
        default: Default value when not found or invalid
        
    Returns:
        int/None: Parsed integer or the default value
    """
    value = request.GET.get(param_name) or request.POST.get(param_name)
    if value:
        try:
            return int(value)
        except (ValueError, TypeError):
            pass
    return default