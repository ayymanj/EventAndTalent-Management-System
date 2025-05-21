from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile

class Command(BaseCommand):
    help = 'Checks and fixes user profiles'

    def handle(self, *args, **options):
        users = User.objects.all()
        for user in users:
            try:
                profile = user.profile
                self.stdout.write(f"User {user.username} has profile with role: {profile.role}")
            except UserProfile.DoesNotExist:
                # Create profile if it doesn't exist
                profile = UserProfile.objects.create(user=user, role='organizer')
                self.stdout.write(self.style.SUCCESS(f"Created profile for {user.username} with role: {profile.role}")) 