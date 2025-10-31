from django.db.models import Prefetch, Q, Count, Sum, Avg, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from datetime import timedelta
from functools import wraps
import time

def optimize_query(queryset, select_fields=None, prefetch_fields=None):
    """
    Optimize queryset to reduce database round trips.
    
    Args:
        queryset: The queryset to optimize
        select_fields: Fields for select_related
        prefetch_fields: Fields or Prefetch objects for prefetch_related
    
    Returns:
        Optimized queryset
    """
    if select_fields:
        queryset = queryset.select_related(*select_fields)
    
    if prefetch_fields:
        queryset = queryset.prefetch_related(*prefetch_fields)
    
    return queryset

def query_performance_logger(func):
    """
    Decorator: log query execution time for performance analysis.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        print(f"Query {func.__name__} execution time: {execution_time:.4f}s")
        return result
    return wrapper

def paginate_queryset(queryset, page_number, items_per_page=20):
    """
    Paginate a queryset.
    
    Args:
        queryset: The queryset to paginate
        page_number: Current page number
        items_per_page: Items per page
        
    Returns:
        Paginated queryset
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    paginator = Paginator(queryset, items_per_page)
    
    try:
        paginated_queryset = paginator.page(page_number)
    except PageNotAnInteger:
        # If page number is not an integer, return the first page
        paginated_queryset = paginator.page(1)
    except EmptyPage:
        # If page is out of range, return the last page
        paginated_queryset = paginator.page(paginator.num_pages)
    
    return paginated_queryset

def get_filtered_queryset(queryset, filter_params):
    """
    Filter a queryset by provided parameters.
    
    Args:
        queryset: The queryset to filter
        filter_params: Dict of filters
        
    Returns:
        Filtered queryset
    """
    # Remove empty values
    valid_filters = {k: v for k, v in filter_params.items() if v}
    
    if valid_filters:
        queryset = queryset.filter(**valid_filters)
    
    return queryset

def get_date_range_filter(start_date, end_date, date_field='created_at'):
    """
    Build a date range filter dict.
    
    Args:
        start_date: Start date
        end_date: End date
        date_field: Date field name
        
    Returns:
        dict: Date range filter kwargs
    """
    filter_kwargs = {}
    
    if start_date:
        filter_kwargs[f"{date_field}__gte"] = start_date
    
    if end_date:
        # Adjust end date to end of the day
        end_date = timezone.datetime.combine(
            end_date, 
            timezone.datetime.max.time()
        ).replace(tzinfo=timezone.get_current_timezone())
        filter_kwargs[f"{date_field}__lte"] = end_date
    
    return filter_kwargs

# Add alias function to keep backward compatibility
def get_paginated_queryset(queryset, page_number, items_per_page=20):
    """
    Alias for paginate_queryset to keep backward compatibility.
    
    Args:
        queryset: The queryset to paginate
        page_number: Current page number
        items_per_page: Items per page
        
    Returns:
        Paginated queryset
    """
    return paginate_queryset(queryset, page_number, items_per_page)

def build_filter_query(filter_dict):
    """
    Build a combined filter query using Django Q objects.
    
    This function creates a composite Django ORM query (Q) from a filter dict.
    
    Args:
        filter_dict: Dict of {field_name: value}
        
    Returns:
        Combined Django Q object to use with queryset.filter()
    """
    from django.db.models import Q
    
    # Remove empty values
    valid_filters = {k: v for k, v in filter_dict.items() if v is not None and v != ''}
    
    # Initialize query object
    query = Q()
    
    # Build and combine query clauses for each filter condition
    for field, value in valid_filters.items():
        # Support list values (for __in queries)
        if isinstance(value, list):
            if value:  # Only add when list is non-empty
                query &= Q(**{f"{field}__in": value})
        else:
            query &= Q(**{field: value})
    
    return query