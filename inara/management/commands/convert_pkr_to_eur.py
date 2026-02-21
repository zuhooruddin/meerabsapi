"""
Django management command to convert PKR prices to EUR for existing products.
Run: python manage.py convert_pkr_to_eur
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from inara.models import Item, ProductVariant


class Command(BaseCommand):
    help = 'Convert PKR prices to EUR for all products and variants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exchange-rate',
            type=float,
            default=0.0033,
            help='Exchange rate: 1 PKR = X EUR (default: 0.0033, meaning 1 EUR ≈ 303 PKR)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be converted without actually converting',
        )
        parser.add_argument(
            '--sku-pattern',
            type=str,
            default=None,
            help='Only convert products matching SKU pattern (e.g., "ZR-25")',
        )

    def handle(self, *args, **options):
        exchange_rate = options['exchange_rate']
        dry_run = options['dry_run']
        sku_pattern = options['sku_pattern']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        else:
            self.stdout.write(self.style.WARNING(f'This will convert all PKR prices to EUR using rate: 1 PKR = {exchange_rate} EUR'))
            confirm = input('Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        self.stdout.write(f'\nUsing exchange rate: 1 PKR = {exchange_rate} EUR (1 EUR ≈ {1/exchange_rate:.2f} PKR)')
        self.stdout.write(self.style.SUCCESS('Starting PKR to EUR conversion...'))

        # Filter items
        items_query = Item.objects.all()
        if sku_pattern:
            items_query = items_query.filter(sku__icontains=sku_pattern)
            self.stdout.write(f'Filtering by SKU pattern: {sku_pattern}')

        items = items_query.filter(status=Item.ACTIVE)
        item_count = items.count()

        if item_count == 0:
            self.stdout.write(self.style.WARNING('No products found to convert.'))
            return

        self.stdout.write(f'\nFound {item_count} products to convert')

        with transaction.atomic():
            converted_items = 0
            converted_variants = 0
            total_price_changes = 0

            for item in items:
                item_changed = False
                original_mrp = item.mrp
                original_sale_price = item.salePrice
                original_base_price = item.base_price
                original_discount_price = item.discount_price

                # Convert Item prices
                if item.mrp and item.mrp > 100:  # Assume PKR if price > 100 (EUR prices are typically lower)
                    new_mrp = int(round(item.mrp * exchange_rate))
                    if new_mrp != item.mrp:
                        if not dry_run:
                            item.mrp = new_mrp
                        item_changed = True
                        self.stdout.write(f'  {item.sku}: MRP {original_mrp} PKR → {new_mrp} EUR')

                if item.salePrice and item.salePrice > 100:
                    new_sale_price = int(round(item.salePrice * exchange_rate))
                    if new_sale_price != item.salePrice:
                        if not dry_run:
                            item.salePrice = new_sale_price
                        item_changed = True
                        self.stdout.write(f'  {item.sku}: Sale Price {original_sale_price} PKR → {new_sale_price} EUR')

                if item.base_price and item.base_price > 100:
                    new_base_price = int(round(item.base_price * exchange_rate))
                    if new_base_price != item.base_price:
                        if not dry_run:
                            item.base_price = new_base_price
                        item_changed = True
                        self.stdout.write(f'  {item.sku}: Base Price {original_base_price} PKR → {new_base_price} EUR')

                if item.discount_price and item.discount_price > 100:
                    new_discount_price = int(round(item.discount_price * exchange_rate))
                    if new_discount_price != item.discount_price:
                        if not dry_run:
                            item.discount_price = new_discount_price
                        item_changed = True
                        self.stdout.write(f'  {item.sku}: Discount Price {original_discount_price} PKR → {new_discount_price} EUR')

                if item_changed:
                    if not dry_run:
                        item.save()
                    converted_items += 1
                    total_price_changes += 1

                # Convert ProductVariant prices
                variants = ProductVariant.objects.filter(item=item, status=ProductVariant.ACTIVE)
                for variant in variants:
                    if variant.variant_price and variant.variant_price > 100:
                        original_variant_price = variant.variant_price
                        new_variant_price = int(round(variant.variant_price * exchange_rate))
                        if new_variant_price != variant.variant_price:
                            if not dry_run:
                                variant.variant_price = new_variant_price
                                variant.save()
                            converted_variants += 1
                            total_price_changes += 1
                            self.stdout.write(f'    Variant {variant.color}/{variant.size}: {original_variant_price} PKR → {new_variant_price} EUR')

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('SUMMARY:'))
        self.stdout.write(f'  Products processed: {item_count}')
        self.stdout.write(f'  Products converted: {converted_items}')
        self.stdout.write(f'  Variants converted: {converted_variants}')
        self.stdout.write(f'  Total price changes: {total_price_changes}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - No changes were made'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to actually convert prices'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Conversion completed successfully!'))
