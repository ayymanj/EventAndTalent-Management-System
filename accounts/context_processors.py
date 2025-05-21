def notification_processor(request):
    """
    Context processor to add notification count to all templates
    """
    notification_count = 0
    if request.user.is_authenticated:
        notification_count = request.user.notifications.filter(is_read=False).count()
    
    return {
        'notification_count': notification_count
    } 