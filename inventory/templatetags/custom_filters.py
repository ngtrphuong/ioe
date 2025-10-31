from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply a numeric value by the given argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value 