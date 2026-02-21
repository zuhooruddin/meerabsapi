"""
Django management command to set appliesOnline=1 for all active products
Run: python manage.py set_applies_online
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from inara.models import Item


class Command(BaseCommand):
    help = 'Set appliesOnline=1 for all active products'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )
        parser.add_argument(
            '--sku-pattern',
            type=str,
            default=None,
            help='Only update products matching SKU pattern (e.g., "ZR-25")',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        sku_pattern = options['sku_pattern']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        else:
            self.stdout.write(self.style.WARNING('This will set appliesOnline=1 for all active products'))
            confirm = input('Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        self.stdout.write(self.style.SUCCESS('Starting update...'))

        # Filter items
        items_query = Item.objects.filter(status=Item.ACTIVE)
        if sku_pattern:
            items_query = items_query.filter(sku__icontains=sku_pattern)
            self.stdout.write(f'Filtering by SKU pattern: {sku_pattern}')

        items = items_query.filter(appliesOnline=0)  # Only update items where appliesOnline=0
        item_count = items.count()

        if item_count == 0:
            self.stdout.write(self.style.SUCCESS('All active products already have appliesOnline=1'))
            return

        self.stdout.write(f'\nFound {item_count} products to update')

        with transaction.atomic():
            updated_count = 0
            for item in items:
                if not dry_run:
                    item.appliesOnline = 1
                    item.save()
                updated_count += 1
                self.stdout.write(f'  ✓ Updated: {item.sku} - {item.name[:50]}')

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('SUMMARY:'))
        self.stdout.write(f'  Products updated: {updated_count}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - No changes were made'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to actually update'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Update completed successfully!'))
