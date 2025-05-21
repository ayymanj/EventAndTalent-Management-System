from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Profile

class Command(BaseCommand):
    help = 'Fix user roles for existing users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to update (optional)',
        )
        parser.add_argument(
            '--role',
            type=str,
            choices=['performer', 'organizer'],
            help='Role to set',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        role = options.get('role')

        if username:
            try:
                user = User.objects.get(username=username)
                profile, created = Profile.objects.get_or_create(user=user)
                if role:
                    profile.role = role
                    profile.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated role for {username} to {role}')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Current role for {username}: {profile.role}')
                    )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User {username} does not exist')
                )
        else:
            # List all users and their roles
            users = User.objects.all()
            for user in users:
                profile, created = Profile.objects.get_or_create(user=user)
                self.stdout.write(
                    f'User: {user.username}, Role: {profile.role}'
                ) 