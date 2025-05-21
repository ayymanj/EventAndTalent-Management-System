from django import template

register = template.Library()

@register.simple_tag
def get_unread_notifications(user):
    return user.notifications.filter(is_read=False).count() 