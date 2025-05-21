from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class Venue(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}, {self.city}"

class Event(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    allow_manual_invites = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def is_past(self):
        return self.date < timezone.now().date()

    @property
    def is_upcoming(self):
        return self.date >= timezone.now().date()

class EventTalent(models.Model):
    TALENT_TYPE_CHOICES = [
        ('musician', 'Musician'),
        ('dancer', 'Dancer'),
        ('speaker', 'Speaker'),
        ('other', 'Other'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='talent_needs')
    talent_type = models.CharField(max_length=20, choices=TALENT_TYPE_CHOICES)
    description = models.TextField()
    quantity_needed = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_talent_type_display()} for {self.event.title}"

class EventApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='applications')
    performer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_applications')
    talent_type = models.ForeignKey(EventTalent, on_delete=models.CASCADE)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.performer.username} - {self.event.title}"

    class Meta:
        unique_together = ['event', 'performer', 'talent_type']

class Availability(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availabilities')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'date', 'start_time', 'end_time')
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.user.username} available {self.date} {self.start_time}-{self.end_time}";

class WebsiteAnalytics(models.Model):
    date = models.DateField(default=timezone.now)
    total_users = models.IntegerField(default=0)
    total_events = models.IntegerField(default=0)
    total_applications = models.IntegerField(default=0)
    active_events = models.IntegerField(default=0)
    completed_events = models.IntegerField(default=0)
    new_users_today = models.IntegerField(default=0)
    new_events_today = models.IntegerField(default=0)
    new_applications_today = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Website Analytics"
        get_latest_by = "date"

    def __str__(self):
        return f"Analytics for {self.date}"

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)

    class Meta:
        verbose_name_plural = "User Activities"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"
