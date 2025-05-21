from django.core.management.base import BaseCommand
from accounts.models import Profile

class Command(BaseCommand):
    help = 'Generates random ratings for existing performer profiles that don\'t have ratings'

    def handle(self, *args, **options):
        performer_profiles = Profile.objects.filter(role='performer', rating__isnull=True)
        generated_count = 0
        
        for profile in performer_profiles:
            profile.generate_random_rating()
            generated_count += 1
            self.stdout.write(f'Generated rating for user: {profile.user.username}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated ratings for {generated_count} performer profiles'
            )
        ) 