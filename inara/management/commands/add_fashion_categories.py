"""
Django management command to add fashion categories to the database
Run: python manage.py add_fashion_categories
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from inara.models import Category


class Command(BaseCommand):
    help = 'Add fashion categories to the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to add fashion categories...'))
        
        # List of categories to add (removed duplicates)
        categories_data = [
            {
                'name': 'END OF SEASON',
                'description': 'End of Season Sale - Flat 50% Off',
                'showAtHome': 1,
                'priority': 1,
            },
            {
                'name': 'Luxury Pret',
                'description': 'Luxury Pret Collection',
                'showAtHome': 1,
                'priority': 2,
            },
            {
                'name': 'Karandi Unstitched - Winter',
                'description': 'Karandi Unstitched Winter Collection',
                'showAtHome': 1,
                'priority': 3,
            },
            {
                'name': 'Linen Unstitched - Winter',
                'description': 'Linen Unstitched Winter Collection',
                'showAtHome': 1,
                'priority': 4,
            },
            {
                'name': 'Khaddar Unstitched - Winter',
                'description': 'Khaddar Unstitched Winter Collection',
                'showAtHome': 1,
                'priority': 5,
            },
            {
                'name': 'Daily Edit - Summer',
                'description': 'Daily Edit Summer Collection',
                'showAtHome': 1,
                'priority': 6,
            },
            {
                'name': '3 PC Chikankari - Summer',
                'description': '3 Piece Chikankari Summer Collection',
                'showAtHome': 1,
                'priority': 7,
            },
            {
                'name': 'Festive Embroidered - Summer',
                'description': 'Festive Embroidered Summer Collection',
                'showAtHome': 1,
                'priority': 8,
            },
            {
                'name': '2 PC - Wedding Unstitched (Raw Silk)',
                'description': '2 Piece Wedding Unstitched Raw Silk Collection',
                'showAtHome': 1,
                'priority': 9,
            },
            {
                'name': 'Wedding Festive Pret',
                'description': 'Wedding Festive Pret Collection',
                'showAtHome': 1,
                'priority': 10,
            },
            {
                'name': 'Luxury Pret (Grip)',
                'description': 'Luxury Pret Grip Collection',
                'showAtHome': 1,
                'priority': 11,
            },
            {
                'name': '3 PC - Cambric',
                'description': '3 Piece Cambric Collection',
                'showAtHome': 1,
                'priority': 12,
            },
            {
                'name': '2 PC - Cotton Viscose',
                'description': '2 Piece Cotton Viscose Collection',
                'showAtHome': 1,
                'priority': 13,
            },
            {
                'name': 'Ready To Wear - Summer',
                'description': 'Ready To Wear Summer Collection',
                'showAtHome': 1,
                'priority': 14,
            },
            {
                'name': 'Menswear',
                'description': 'Menswear Collection',
                'showAtHome': 1,
                'priority': 15,
            },
            {
                'name': 'Home Couture',
                'description': 'Home Couture Collection',
                'showAtHome': 1,
                'priority': 16,
            },
            {
                'name': 'WINTER',
                'description': 'Winter Collection - Flat 50% Off',
                'showAtHome': 1,
                'priority': 17,
            },
            {
                'name': 'SHOP BY PRICE',
                'description': 'Shop By Price - Flat 50% Off',
                'showAtHome': 1,
                'priority': 18,
            },
            {
                'name': 'STUDIO SAMPLES',
                'description': 'Studio Samples - Ready to Wear Sale',
                'showAtHome': 1,
                'priority': 19,
            },
            {
                'name': '3 PC - Premium Khaddar',
                'description': '3 Piece Premium Khaddar Collection',
                'showAtHome': 1,
                'priority': 20,
            },
            {
                'name': '2 PC - Karandi Unstitched',
                'description': '2 Piece Karandi Unstitched Collection',
                'showAtHome': 1,
                'priority': 21,
            },
            {
                'name': '3 Pc - Karandi Unstitched',
                'description': '3 Piece Karandi Unstitched Collection',
                'showAtHome': 1,
                'priority': 22,
            },
            {
                'name': '3 Pc Suit - Karandi Embroidered Shawl',
                'description': '3 Piece Suit Karandi Embroidered Shawl Collection',
                'showAtHome': 1,
                'priority': 23,
            },
            {
                'name': '2 PC - Linen Unstitched',
                'description': '2 Piece Linen Unstitched Collection',
                'showAtHome': 1,
                'priority': 24,
            },
            {
                'name': '3 PC - Linen Unstitched',
                'description': '3 Piece Linen Unstitched Collection',
                'showAtHome': 1,
                'priority': 25,
            },
        ]
        
        categories_created = 0
        categories_updated = 0
        
        for idx, cat_data in enumerate(categories_data, start=1):
            try:
                # Generate slug from name
                slug = slugify(cat_data['name'])
                
                # Ensure slug is unique by appending number if needed
                base_slug = slug
                counter = 1
                while Category.objects.filter(slug=slug).exclude(name=cat_data['name']).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                # Create or get category
                category, created = Category.objects.get_or_create(
                    slug=slug,
                    defaults={
                        'name': cat_data['name'],
                        'description': cat_data.get('description', ''),
                        'parentId': None,  # Main category
                        'isBrand': False,
                        'status': Category.ACTIVE,
                        'appliesOnline': 1,
                        'showAtHome': cat_data.get('showAtHome', 1),
                        'priority': cat_data.get('priority', idx),
                        'metaUrl': f'/categories/{slug}',
                        'metaTitle': f"{cat_data['name']} - Buy Online | Meerab's Wardrobe",
                        'metaDescription': cat_data.get('description', f"Shop {cat_data['name']} collection online. Premium quality fashion items with free delivery across Pakistan."),
                    }
                )
                
                if created:
                    categories_created += 1
                    self.stdout.write(self.style.SUCCESS(f'✅ Created category: {category.name} (slug: {category.slug})'))
                else:
                    # Update existing category
                    category.name = cat_data['name']
                    category.description = cat_data.get('description', '')
                    category.parentId = None
                    category.isBrand = False
                    category.status = Category.ACTIVE
                    category.appliesOnline = 1
                    category.showAtHome = cat_data.get('showAtHome', 1)
                    category.priority = cat_data.get('priority', idx)
                    category.metaUrl = f'/categories/{slug}'
                    category.metaTitle = f"{cat_data['name']} - Buy Online | Meerab's Wardrobe"
                    category.metaDescription = cat_data.get('description', f"Shop {cat_data['name']} collection online. Premium quality fashion items with free delivery across Pakistan.")
                    category.save()
                    categories_updated += 1
                    self.stdout.write(self.style.WARNING(f'🔄 Updated category: {category.name} (slug: {category.slug})'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error creating category {cat_data["name"]}: {str(e)}'))
                continue
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Successfully processed categories:\n'
            f'   - Created: {categories_created}\n'
            f'   - Updated: {categories_updated}\n'
            f'   - Total: {categories_created + categories_updated}'
        ))



