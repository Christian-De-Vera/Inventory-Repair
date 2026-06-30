import os
from django.core.management.base import BaseCommand
from django.db.models import Count
from inventory.models import Item


class Command(BaseCommand):
    help = 'Delete orphaned image files that are no longer referenced by any item'

    def handle(self, *args, **options):
        used_images = Item.objects.exclude(image='').values_list('image', flat=True)
        used_image_names = set(os.path.basename(img) for img in used_images if img)
        
        media_dir = 'media/item_images'
        if not os.path.exists(media_dir):
            self.stdout.write('No media/item_images directory found.')
            return
        
        all_files = os.listdir(media_dir)
        deleted_count = 0
        
        for filename in all_files:
            if filename not in used_image_names:
                filepath = os.path.join(media_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    deleted_count += 1
                    self.stdout.write(f'Deleted: {filename}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} orphaned image(s).'))