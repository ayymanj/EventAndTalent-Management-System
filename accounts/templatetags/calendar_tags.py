from django import template

register = template.Library()

@register.filter
def filter_availability(availabilities, day):
    """Filter availabilities by day of week (for recurring only)."""
    try:
        day_int = int(day)
    except Exception:
        return False
    return any(
        getattr(avail, 'is_recurring', False) and hasattr(avail, 'day_of_week') and avail.day_of_week == day_int
        for avail in availabilities
    )

@register.filter
def split_string(value, delimiter=','):
    """Split a string by the given delimiter."""
    return value.split(delimiter) 