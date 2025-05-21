from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile

class Command(BaseCommand):
    help = 'Check and fix user profiles'

    def handle(self, *args, **options):
        users = User.objects.all()
        for user in users:
            try:
                profile = user.profile
                self.stdout.write(f"User {user.username} has profile with role: {profile.role}")
            except UserProfile.DoesNotExist:
                self.stdout.write(f"Creating profile for user {user.username}")
                UserProfile.objects.create(user=user, role='organizer') 