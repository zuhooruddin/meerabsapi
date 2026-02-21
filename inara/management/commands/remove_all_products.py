"""
Django management command to remove all products from the database
Run: python manage.py remove_all_products
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from inara.models import (
    Item, ProductVariant, CategoryItem, BundleItem, 
    Wishlist, ProductReview, ItemGallery, ItemTags,
    OrderDescription
)

class Command(BaseCommand):
    help = 'Remove all products from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--soft-delete',
            action='store_true',
            help='Set status to DELETED instead of hard deleting',
        )
        parser.add_argument(
            '--keep-orders',
            action='store_true',
            help='Keep order descriptions (mark as deleted instead of removing)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        soft_delete = options['soft_delete']
        keep_orders = options['keep_orders']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        else:
            # Confirmation prompt
            self.stdout.write(self.style.ERROR('WARNING: This will delete ALL products from the database!'))
            if not dry_run:
                confirm = input('Type "yes" to confirm: ')
                if confirm.lower() != 'yes':
                    self.stdout.write(self.style.ERROR('Operation cancelled.'))
                    return

        self.stdout.write(self.style.SUCCESS('Starting removal of all products...'))

        with transaction.atomic():
            # Get all items
            all_items = Item.objects.all()
            item_count = all_items.count()
            
            if item_count == 0:
                self.stdout.write(self.style.WARNING('No products found in database.'))
                return

            self.stdout.write(f'\nFound {item_count} products to remove')
            
            # Get item IDs for related data queries
            item_ids = list(all_items.values_list('id', flat=True))
            
            # Count related data (using correct field names)
            variants_count = ProductVariant.objects.filter(item_id__in=item_ids).count()
            category_items_count = CategoryItem.objects.filter(itemId_id__in=item_ids).count()
            bundle_items_count = BundleItem.objects.filter(itemId_id__in=item_ids).count()
            wishlist_count = Wishlist.objects.filter(item_id__in=item_ids).count()
            reviews_count = ProductReview.objects.filter(itemid_id__in=item_ids).count()
            gallery_count = ItemGallery.objects.filter(itemId_id__in=item_ids).count()
            tags_count = ItemTags.objects.filter(itemId_id__in=item_ids).count()
            
            # Count order descriptions (via variants)
            variant_ids = list(ProductVariant.objects.filter(item_id__in=item_ids).values_list('id', flat=True))
            order_descriptions_count = OrderDescription.objects.filter(variant_id__in=variant_ids).count() if variant_ids else 0
            
            self.stdout.write(f'\nRelated data to be removed:')
            self.stdout.write(f'  - Product Variants: {variants_count}')
            self.stdout.write(f'  - Category-Item relationships: {category_items_count}')
            self.stdout.write(f'  - Bundle items: {bundle_items_count}')
            self.stdout.write(f'  - Wishlist entries: {wishlist_count}')
            self.stdout.write(f'  - Product reviews: {reviews_count}')
            self.stdout.write(f'  - Item gallery images: {gallery_count}')
            self.stdout.write(f'  - Item tags: {tags_count}')
            self.stdout.write(f'  - Order descriptions (via variants): {order_descriptions_count}')
            
            if not dry_run:
                self.stdout.write('\nRemoving related data...')
                
                # Delete/soft-delete related data
                # Note: ProductVariant has CASCADE, so it will be deleted automatically when items are deleted
                # But we'll handle it explicitly for soft-delete option
                if variants_count > 0:
                    if soft_delete:
                        ProductVariant.objects.filter(item_id__in=item_ids).update(status=ProductVariant.DELETED)
                    else:
                        # CASCADE will handle this, but delete explicitly for clarity
                        ProductVariant.objects.filter(item_id__in=item_ids).delete()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Processed {variants_count} product variants'))
                
                if category_items_count > 0:
                    if soft_delete:
                        CategoryItem.objects.filter(itemId_id__in=item_ids).update(status=CategoryItem.DELETED)
                    else:
                        # For hard delete, need to actually delete PROTECT relationships
                        CategoryItem.objects.filter(itemId_id__in=item_ids).delete()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Removed {category_items_count} category-item relationships'))
                
                if bundle_items_count > 0:
                    if soft_delete:
                        BundleItem.objects.filter(itemId_id__in=item_ids).update(status=BundleItem.DELETED)
                    else:
                        # For hard delete, need to actually delete PROTECT relationships
                        BundleItem.objects.filter(itemId_id__in=item_ids).delete()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Removed {bundle_items_count} bundle items'))
                
                if wishlist_count > 0:
                    Wishlist.objects.filter(item_id__in=item_ids).delete()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Removed {wishlist_count} wishlist entries'))
                
                if reviews_count > 0:
                    # ProductReview has CASCADE, but let's be explicit
                    ProductReview.objects.filter(itemid_id__in=item_ids).delete()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Removed {reviews_count} product reviews'))
                
                if gallery_count > 0:
                    if soft_delete:
                        ItemGallery.objects.filter(itemId_id__in=item_ids).update(status=ItemGallery.DELETED)
                    else:
                        # For hard delete, need to actually delete PROTECT relationships
                        ItemGallery.objects.filter(itemId_id__in=item_ids).delete()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Removed {gallery_count} gallery images'))
                
                if tags_count > 0:
                    if soft_delete:
                        ItemTags.objects.filter(itemId_id__in=item_ids).update(status=ItemTags.DELETED)
                    else:
                        # For hard delete, need to actually delete PROTECT relationships
                        ItemTags.objects.filter(itemId_id__in=item_ids).delete()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Removed {tags_count} item tags'))
                
                if order_descriptions_count > 0:
                    if keep_orders:
                        # Mark order descriptions as deleted but keep them for history
                        OrderDescription.objects.filter(variant_id__in=variant_ids).update(isDeleted=True)
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Marked {order_descriptions_count} order descriptions as deleted (kept for history)'))
                    else:
                        # Note: OrderDescription has PROTECT, so we can't delete if there are active orders
                        # We'll try to mark as deleted
                        try:
                            OrderDescription.objects.filter(variant_id__in=variant_ids).update(isDeleted=True)
                            self.stdout.write(self.style.SUCCESS(f'  ✓ Marked {order_descriptions_count} order descriptions as deleted'))
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'  ⚠ Could not update order descriptions: {e}'))
                
                # Delete or soft-delete items
                self.stdout.write(f'\nRemoving {item_count} products...')
                if soft_delete:
                    all_items.update(status=Item.DELETED)
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Soft-deleted {item_count} products'))
                else:
                    all_items.delete()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Hard-deleted {item_count} products'))

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('SUMMARY:'))
        self.stdout.write(f'  Products processed: {item_count}')
        self.stdout.write(f'  Product Variants: {variants_count}')
        self.stdout.write(f'  Category-Item relationships: {category_items_count}')
        self.stdout.write(f'  Bundle items: {bundle_items_count}')
        self.stdout.write(f'  Wishlist entries: {wishlist_count}')
        self.stdout.write(f'  Product reviews: {reviews_count}')
        self.stdout.write(f'  Item gallery images: {gallery_count}')
        self.stdout.write(f'  Item tags: {tags_count}')
        self.stdout.write(f'  Order descriptions: {order_descriptions_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - No changes were made'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to actually delete'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Removal completed successfully!'))
