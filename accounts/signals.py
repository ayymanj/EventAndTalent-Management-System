from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.urls import reverse
from .models import Notification, CalendarEvent
from home.models import Event, EventApplication

# Calendar Event Triggers
@receiver(post_save, sender=Event)
def create_event_calendar_event(sender, instance, created, **kwargs):
    """Create a calendar event when an organizer creates a new event"""
    if created and instance.status == 'published':
        CalendarEvent.objects.create(
            user=instance.organizer,
            title=instance.title,
            description=instance.description,
            event_type='performance',
            date=instance.date,
            start_time=instance.start_time,
            end_time=instance.end_time,
            location=str(instance.venue) if instance.venue else '',
            related_event=instance
        )

@receiver(post_save, sender=EventApplication)
def create_application_calendar_event(sender, instance, created, **kwargs):
    """Create a calendar event when a performer's application is approved"""
    if not created and instance.status == 'accepted':
        CalendarEvent.objects.create(
            user=instance.performer,
            title=f"Performance: {instance.event.title}",
            description=instance.event.description,
            event_type='performance',
            date=instance.event.date,
            start_time=instance.event.start_time,
            end_time=instance.event.end_time,
            location=str(instance.event.venue) if instance.event.venue else '',
            related_event=instance.event
        )

# Notification Triggers
@receiver(post_save, sender=EventApplication)
def create_application_notification(sender, instance, created, **kwargs):
    """Create notifications for application status changes"""
    if created:
        # Notify organizer about new application
        Notification.objects.create(
            user=instance.event.organizer,
            notification_type='application',
            title='New application received',
            message=f"{instance.performer.username} has applied for {instance.event.title}",
            link=reverse('event_detail', args=[instance.event.id])
        )
    elif instance.status in ['accepted', 'rejected']:
        # Notify performer about application status change
        title = 'Application Accepted' if instance.status == 'accepted' else 'Application Rejected'
        Notification.objects.create(
            user=instance.performer,
            notification_type='application',
            title=title,
            message=f"Your application for {instance.event.title} has been {instance.status}",
            link=reverse('event_detail', args=[instance.event.id])
        )

@receiver(post_save, sender=Event)
def create_event_notification(sender, instance, created, **kwargs):
    """Create notifications for event changes"""
    if created:
        # Notify organizer about event creation
        Notification.objects.create(
            user=instance.organizer,
            notification_type='event',
            title='Event added Successfully',
            message=f"Your event '{instance.title}' has been created successfully",
            link=reverse('event_detail', args=[instance.id])
        )
    elif not created:
        # Notify performers about event changes
        approved_applications = EventApplication.objects.filter(
            event=instance,
            status='accepted'
        )
        for application in approved_applications:
            Notification.objects.create(
                user=application.performer,
                notification_type='event',
                title='Change in event details',
                message=f"The details of '{instance.title}' have been updated",
                link=reverse('event_detail', args=[instance.id])
            )

@receiver(post_delete, sender=Event)
def create_event_deletion_notification(sender, instance, **kwargs):
    """Create notification when an event is deleted"""
    Notification.objects.create(
        user=instance.organizer,
        notification_type='event',
        title='Event deleted successfully',
        message=f"Your event '{instance.title}' has been deleted",
        link=reverse('event_list')
    )

# User Activity Triggers
@receiver(post_save, sender=Event)
def log_event_activity(sender, instance, created, **kwargs):
    """Log user activity for event creation/updates"""
    from home.models import UserActivity
    action = 'created' if created else 'updated'
    UserActivity.objects.create(
        user=instance.organizer,
        action=f'Event {action}',
        details={
            'event_id': instance.id,
            'event_title': instance.title,
            'timestamp': timezone.now().isoformat()
        }
    )

@receiver(post_save, sender=EventApplication)
def log_application_activity(sender, instance, created, **kwargs):
    """Log user activity for application creation/updates"""
    from home.models import UserActivity
    if created:
        UserActivity.objects.create(
            user=instance.performer,
            action='Application submitted',
            details={
                'event_id': instance.event.id,
                'event_title': instance.event.title,
                'timestamp': timezone.now().isoformat()
            }
        )
    else:
        UserActivity.objects.create(
            user=instance.event.organizer,
            action=f'Application {instance.status}',
            details={
                'event_id': instance.event.id,
                'event_title': instance.event.title,
                'performer': instance.performer.username,
                'timestamp': timezone.now().isoformat()
            }
        )
