from django import template
import json
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='jsonify')
def jsonify(obj):
    """Convert a Python object to a JSON string"""
    return json.dumps(obj)

@register.filter(name='currency')
def currency(value):
    """Format a number as currency"""
    if value is None:
        return '¥0.00'
    return f'¥{value:.2f}'

@register.filter(name='divisor')
def divisor(value, arg):
    """Compute value divided by arg as a percentage (value/arg*100)"""
    try:
        value = float(value)
        arg = float(arg)
        if arg == 0:
            return 0
        return value / arg * 100
    except (ValueError, TypeError):
        return 0
        
@register.filter(name='div')
def div(value, arg):
    """Compute value divided by arg (for averages)"""
    try:
        value = float(value)
        arg = float(arg)
        if arg == 0:
            return 0
        return value / arg
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """Convert a number to a percentage of total"""
    if total == 0:
        return 0
    return round((value / total) * 100)

@register.simple_tag
def level_badge(level):
    """Generate a formatted badge for a member level"""
    if not level:
        return mark_safe('<span class="badge bg-secondary">No Level</span>')
    
    # Use level color attribute, default to primary
    color = level.color if hasattr(level, 'color') and level.color else 'primary'
    
    # Build badge HTML
    badge = f'<span class="badge bg-{color}">{level.name}</span>'
    
    # If default level, add a special mark
    if hasattr(level, 'is_default') and level.is_default:
        badge = f'<span class="badge bg-{color}">{level.name} <i class="bi bi-star-fill ms-1"></i></span>'
    
    return mark_safe(badge)

@register.inclusion_tag('inventory/member/tags/level_selector.html')
def level_selector(levels, selected_id=None):
    """Render the member level selector"""
    return {
        'levels': levels,
        'selected_id': selected_id
    } 