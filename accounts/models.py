from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import random

# Create your models here.

class Profile(models.Model):
    ROLE_CHOICES = (
        ('performer', 'Performer'),
        ('organizer', 'Organizer'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    bio = models.TextField(max_length=500, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    email_notifications = models.BooleanField(default=True)
    application_updates = models.BooleanField(default=True)
    show_profile = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    def generate_random_rating(self):
        if self.role == 'performer' and self.rating is None:
            self.rating = round(random.uniform(3.0, 5.0), 1)
            self.save()

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation {self.id}"

    @classmethod
    def get_or_create_conversation(cls, user1, user2):
        """
        Get or create a conversation between two users.
        Returns a tuple of (conversation, created) where created is a boolean
        specifying whether a new conversation was created.
        """
        # Try to find existing conversation
        conversation = cls.objects.filter(participants=user1).filter(participants=user2).first()
        
        if conversation:
            return conversation, False
        
        # Create new conversation
        conversation = cls.objects.create()
        conversation.participants.add(user1, user2)
        return conversation, True

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} in {self.conversation}"

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('message', 'New Message'),
        ('application', 'Application Update'),
        ('event', 'Event Update'),
        ('system', 'System Notification'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} notification for {self.user.username}"

# Signal to create/update UserProfile when User is created/updated
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Get the role from the form data if available
        role = getattr(instance, '_role', 'performer')  # Default to performer if not set
        profile = Profile.objects.create(user=instance, role=role)
        if role == 'performer':
            profile.generate_random_rating()

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Get or create the profile
    profile, created = Profile.objects.get_or_create(user=instance)
    if created:
        # If profile was just created, set the role from the form data if available
        role = getattr(instance, '_role', 'performer')  # Default to performer if not set
        profile.role = role
        profile.save()
        if role == 'performer':
            profile.generate_random_rating()

class CalendarEvent(models.Model):
    EVENT_TYPES = [
        ('performance', 'Performance'),
        ('rehearsal', 'Rehearsal'),
        ('meeting', 'Meeting'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calendar_events')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=200, blank=True)
    related_event = models.ForeignKey('home.Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='calendar_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.date}"

    class Meta:
        ordering = ['date', 'start_time']
