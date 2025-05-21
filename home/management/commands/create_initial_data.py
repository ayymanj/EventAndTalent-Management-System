from django.core.management.base import BaseCommand
from home.models import Category, Venue

class Command(BaseCommand):
    help = 'Creates initial data for the application'

    def handle(self, *args, **options):
        # Create categories
        categories = [
            ('Music', 'Music events and concerts'),
            ('Dance', 'Dance performances and shows'),
            ('Theater', 'Theater performances and plays'),
        ]
        
        for name, description in categories:
            Category.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            self.stdout.write(f"Created category: {name}")
        
        # Create a default venue
        Venue.objects.get_or_create(
            name='Main Hall',
            defaults={
                'address': '123 Main Street',
                'city': 'Your City',
                'state': 'Your State',
                'zip_code': '12345'
            }
        )
        self.stdout.write("Created default venue") 