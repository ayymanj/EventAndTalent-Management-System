from django.urls import reverse
from .models import Notification

def create_notification(user, notification_type, title, message, link=''):
    """
    Create a notification for a user.
    
    Args:
        user: The user to create the notification for
        notification_type: Type of notification ('message', 'application', 'event', 'system')
        title: Title of the notification
        message: Detailed message
        link: Optional URL to link to
    """
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    ) 