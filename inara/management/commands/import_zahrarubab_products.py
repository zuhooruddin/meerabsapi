"""
Import products from zahrarubab.com (Shopify) into the Item and Category tables.
Run: python manage.py import_zahrarubab_products
"""
from decimal import Decimal
import re
import time
import random
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from inara.models import Category, CategoryItem, Item, ItemGallery, ProductVariant


class Command(BaseCommand):
    help = "Import products from zahrarubab.com (Shopify) into the database."

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default="https://zahrarubab.com")
        parser.add_argument("--page-size", type=int, default=250)
        parser.add_argument("--max-pages", type=int, default=0)
        parser.add_argument("--no-download-images", dest="download_images", action="store_false", help="Skip downloading images (default: images are downloaded)")
        parser.add_argument("--update-existing", action="store_true")
        parser.add_argument("--exchange-rate", type=float, default=0.92, help="Exchange rate to convert prices to Euro (default: 0.92 for USD to EUR)")

    def handle(self, *args, **options):
        base_url = options["base_url"].rstrip("/")
        page_size = options["page_size"]
        max_pages = options["max_pages"]
        # Default to True for download_images unless --no-download-images is used
        # Check if download_images was explicitly set to False (via --no-download-images)
        download_images = options.get("download_images")
        if download_images is None:
            # Not explicitly set, default to True
            download_images = True
        update_existing = options.get("update_existing", False)
        exchange_rate = options.get("exchange_rate", 0.92)
        
        self.stdout.write(f"Using exchange rate: {exchange_rate} (1 source currency = {exchange_rate} EUR)")

        main_category = self._get_or_create_main_category()
        category_map = self._get_or_create_target_categories(main_category)
        self.stdout.write(self.style.SUCCESS("Starting import from Zahra Rubab..."))
        self.stdout.write(f"Download images: {download_images}")

        page = 1
        imported = 0
        skipped = 0

        while True:
            if max_pages and page > max_pages:
                break

            products = self._fetch_products(base_url, page, page_size)
            if not products:
                break

            for product in products:
                result = self._import_product(
                    product,
                    main_category=main_category,
                    category_map=category_map,
                    download_images=download_images,
                    update_existing=update_existing,
                    exchange_rate=exchange_rate,
                )
                if result:
                    imported += 1
                else:
                    skipped += 1

            page += 1
            time.sleep(0.2)

        self.stdout.write(
            self.style.SUCCESS(f"Done. Imported: {imported}, Skipped: {skipped}")
        )

    def _fetch_products(self, base_url, page, limit):
        url = urljoin(base_url, f"/products.json?limit={limit}&page={page}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        return payload.get("products", [])

    def _get_or_create_main_category(self):
        category, _ = Category.objects.get_or_create(
            slug="zahrarubab-products",
            defaults={
                "name": "Zahra Rubab Products",
                "description": "Imported products from zahrarubab.com",
                "status": Category.ACTIVE,
                "appliesOnline": 1,
                "showAtHome": 0,
                "priority": 10,
            },
        )
        return category

    def _get_or_create_subcategory(self, name, parent):
        slug = slugify(name)[:150]
        category, _ = Category.objects.get_or_create(
            slug=slug or "zahrarubab-uncategorized",
            defaults={
                "name": name or "Uncategorized",
                "description": f"Imported products for {name or 'Uncategorized'}",
                "parentId": parent,
                "status": Category.ACTIVE,
                "appliesOnline": 1,
                "showAtHome": 0,
                "priority": 10,
            },
        )
        return category

    def _get_or_create_target_categories(self, parent):
        # All categories to create (with their slugs)
        category_list = [
            ("2 PC - Cotton Viscose", "2-pc-cotton-viscose", None),
            ("2 PC - Karandi Unstitched", "2-pc-karandi-unstitched", None),
            ("2 PC - Linen Unstitched", "2-pc-linen-unstitched", None),
            ("2 PC - Wedding Unstitched (Raw Silk)", "2-pc-wedding-unstitched-raw-silk", None),
            ("3 PC - Cambric", "3-pc-cambric", None),
            ("3 PC - Linen Unstitched", "3-pc-linen-unstitched", None),
            ("3 PC - Premium Khaddar", "3-pc-premium-khaddar", None),
            ("3 PC Chikankari - Summer", "3-pc-chikankari-summer", None),
            ("3 Pc - Karandi Unstitched", "3-pc-karandi-unstitched", None),
            ("3 Pc Suit - Karandi Embroidered Shawl", "3-pc-suit-karandi-embroidered-shawl", None),
            ("All IN STORE", "all-in-store", parent),
            ("CRYSTAL", "crystal", parent),
            ("Daily Edit - Summer", "daily-edit-summer", None),
            ("END OF SEASON", "end-of-season", None),
            ("FORMALS", "formals", parent),
            ("Festive Embroidered - Summer", "festive-embroidered-summer", None),
            ("Home Couture", "home-couture", None),
            ("Karandi Unstitched", "karandi-unstitched-", None),
            ("Khaddar Unstitched", "khaddar-unstitched-", None),
            ("LAVENDER", "lavender", parent),
            ("Lawn", "lawn", None),
            ("Linen Unstitched", "linen-unstitched", None),
            ("Luxury Pret", "luxury-pret", None),
            ("Luxury Pret (Grip)", "luxury-pret-grip", None),
            ("Men", "men", None),
            ("Menswear", "menswear", None),
            ("MOON LIGHT", "moon-light", parent),
            ("Ready To Wear - Summer", "ready-to-wear-summer", None),
            ("SHOP BY PRICE", "shop-by-price", None),
            ("Silk", "silk", parent),
            ("STUDIO SAMPLES", "studio-samples", None),
            ("WINTER", "winter", None),
            ("Wedding Festive Pret", "wedding-festive-pret", None),
            ("Women", "women", None),
            ("ZIRCON", "zircon", parent),
            ("Zardozi - Nikkah Edit", "zardozi-nikkah-edit", parent),
            ("Zardozi - Nikkah Edit Summer", "zardozi-nikkah-edit-summer", parent),
        ]
        
        categories = {}
        for name, slug, category_parent in category_list:
            # Use provided parent or main parent
            parent_category = category_parent if category_parent else parent
            category, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": f"Imported products for {name}",
                    "parentId": parent_category,
                    "status": Category.ACTIVE,
                    "appliesOnline": 1,
                    "showAtHome": 0,
                    "priority": 10,
                },
            )
            categories[name.lower()] = category
        return categories

    def _import_product(self, product, main_category, category_map, download_images, update_existing, exchange_rate=0.92):
        title = product.get("title") or ""
        handle = product.get("handle") or ""
        vendor = product.get("vendor") or ""
        body_html = product.get("body_html") or ""
        images = product.get("images") or []
        variants = product.get("variants") or []
        tags = product.get("tags") or ""

        description = self._clean_html(body_html)
        slug = self._unique_slug(handle or title, product.get("id"))

        item_sku = self._build_item_sku(product, variants)
        existing = Item.objects.filter(sku=item_sku).first()
        if existing and not update_existing:
            return False

        prices = [self._to_number(v.get("price")) for v in variants if v.get("price")]
        compare_prices = [
            self._to_number(v.get("compare_at_price"))
            for v in variants
            if v.get("compare_at_price")
        ]

        # Convert prices to Euro
        sale_price = int(round(min(prices) * exchange_rate)) if prices else None
        mrp_raw = max(compare_prices) if compare_prices else (min(prices) if prices else None)
        mrp = int(round(mrp_raw * exchange_rate)) if mrp_raw is not None else sale_price
        discount = self._calc_discount(mrp, sale_price)

        # List of specific products to mark as new arrival and featured
        featured_new_products = [
            "ZR-2537 | DALIA",
            "ZR-2434 Grey",
            "ZR-2305 Bottle Green Chiffon",
            "ZR-2528 | BURGUNDY",
            "ZR-2439 BLUE",
            "ZR-2536 | CRYSTAL",
            "ZR-2518 | Olive",
            "ZR-2513 | Asmani Nila",
            "ZR-2447 | Pista | 3 PC",
            "ZR-2222 Pink",
            "3 Piece Stitched - ZR 2120 Gold",
            "ZR-2117 Skin",
            "ZR-2331 Skin",
            "ZR-2349 Black, Mehroon, Peach",
            "ZR-2344 Green & Skin",
            "ZR-2357 Magenta & Aqua Dress",
            "ZR-2431-A",
            "ZR-2429-A",
            "ZR-2427-A",
            "ZR-2441 | FEROZA",
            "ZR-2533 | SAPPHIRE",
            "ZR-2115 Coffee, Pink, Pista",
            "ZR-2347 Mustard, Skin",
            "ZR-2120 Perple",
            "ZR-2534 | ZIRCON",
            "ZR-2426-A",
            "ZR-2431-B",
            "ZR-2432-B",
            "ZR-2426-B",
        ]
        
        # Check if current product matches any of the featured/new products
        title_upper = title.upper()
        is_featured_product = False
        
        # Check by exact title match or by SKU pattern
        for featured_product in featured_new_products:
            featured_upper = featured_product.upper()
            # Check if title contains the featured product identifier
            if featured_upper in title_upper or title_upper in featured_upper:
                is_featured_product = True
                break
        
        # Also check by SKU if title doesn't match
        if not is_featured_product:
            for featured_product in featured_new_products:
                # Extract SKU pattern (e.g., "ZR-2537" from "ZR-2537 | DALIA")
                sku_pattern = featured_product.split()[0].upper() if featured_product.split() else ""
                if sku_pattern and sku_pattern in item_sku.upper():
                    is_featured_product = True
                    break
        
        # Only assign isNewArrival and isFeatured to matching products
        is_new = 1 if is_featured_product else 0
        is_featured = 1 if is_featured_product else 0
        
        if is_new:
            self.stdout.write(self.style.SUCCESS(f"  → Marked as NEW ARRIVAL: {item_sku} ({title[:50]})"))
        if is_featured:
            self.stdout.write(self.style.SUCCESS(f"  → Marked as FEATURED: {item_sku} ({title[:50]})"))
        
        item_values = {
            "name": title[:150] or "Zahra Rubab Product",
            "slug": slug,
            "sku": item_sku,
            "description": description[:2000] or None,
            "appliesOnline": 1,
            "manufacturer": vendor[:150] or None,
            "mrp": mrp,
            "salePrice": sale_price,
            "discount": discount,
            "stock": Decimal(10),
            "stockCheckQty": Decimal(1),
            "status": Item.ACTIVE,
            "metaTitle": title[:150] or None,
            "metaDescription": description[:150] or None,
            "timestamp": timezone.now(),
            "isNewArrival": is_new,
            "isFeatured": is_featured,
        }

        if existing:
            for key, value in item_values.items():
                setattr(existing, key, value)
            item = existing
            item.save()
        else:
            item = Item.objects.create(**item_values)

        # Match product to appropriate categories based on title, tags, and product type
        matched_categories = self._match_product_categories(
            title=title,
            tags=tags,
            product_type=product.get("product_type") or "",
            category_map=category_map,
        )
        
        # Always add to "All IN STORE" category
        if category_map.get("all in store"):
            if category_map["all in store"] not in matched_categories:
                matched_categories.append(category_map["all in store"])

        # Add product to matched categories
        for category in matched_categories:
            CategoryItem.objects.get_or_create(
                categoryId=category,
                itemId=item,
                defaults={"level": 2, "status": CategoryItem.ACTIVE},
            )
        
        if matched_categories:
            category_names = [cat.name for cat in matched_categories]
            self.stdout.write(f"  → Added to categories: {', '.join(category_names[:5])}{'...' if len(category_names) > 5 else ''}")

        # Download images if enabled and available
        if download_images:
            if images:
                self._download_images(item, images)
            else:
                self.stdout.write(self.style.WARNING(f"No images to download for product {item.sku}"))
        else:
            self.stdout.write(self.style.WARNING(f"Image downloading is disabled for product {item.sku}"))

        self._import_variants(item, product, variants, exchange_rate)
        return True

    def _import_variants(self, item, product, variants, exchange_rate=0.92):
        options = product.get("options") or []
        option_names = {opt.get("name", "").lower(): opt.get("position") for opt in options}
        
        if not variants:
            self.stdout.write(self.style.WARNING(f"No variants found for product {item.sku}"))
            return
        
        self.stdout.write(f"Importing {len(variants)} variant(s) for product {item.sku}...")
        imported_count = 0

        for variant in variants:
            color = self._get_option_value(variant, option_names, ["color", "colour"])
            size = self._get_option_value(variant, option_names, ["size"])

            if not color and not size:
                continue

            size = self._normalize_size(size)

            if not color:
                color = "Default"

            sku = variant.get("sku") or f"ZR-VAR-{variant.get('id')}"
            sku = self._ensure_unique_variant_sku(sku, item, variant)
            price_raw = self._to_number(variant.get("price"))
            # Convert price to Euro
            price = price_raw * exchange_rate if price_raw is not None else None

            # Try to get by SKU first (since it's unique)
            variant_obj = ProductVariant.objects.filter(sku=sku).first()
            
            # Random stock quantity between 2-229
            random_stock = random.randint(2, 229)
            
            if variant_obj:
                # Update existing variant
                variant_obj.item = item
                variant_obj.color = color[:50]
                variant_obj.size = size
                variant_obj.stock_quantity = random_stock
                variant_obj.variant_price = int(round(price)) if price is not None else None
                variant_obj.status = ProductVariant.ACTIVE
                variant_obj.save()
                imported_count += 1
                self.stdout.write(f"  ✓ Updated variant: {color} - {size} (SKU: {sku}, Stock: {random_stock})")
            else:
                # Random stock quantity between 2-229
                random_stock = random.randint(2, 229)
                
                # Try to get by item, color, size combination
                variant_obj, created = ProductVariant.objects.get_or_create(
                    item=item,
                    color=color[:50],
                    size=size,
                    defaults={
                        "sku": sku[:100],
                        "stock_quantity": random_stock,
                        "variant_price": int(round(price)) if price is not None else None,
                        "status": ProductVariant.ACTIVE,
                    },
                )
                # If it already existed with different SKU, update it
                if not created:
                    variant_obj.sku = sku[:100]
                    variant_obj.stock_quantity = random_stock
                    variant_obj.variant_price = int(round(price)) if price is not None else None
                    variant_obj.status = ProductVariant.ACTIVE
                    variant_obj.save()
                    imported_count += 1
                    self.stdout.write(f"  ✓ Updated variant: {color} - {size} (SKU: {sku}, Stock: {random_stock})")
                else:
                    imported_count += 1
                    self.stdout.write(f"  ✓ Created variant: {color} - {size} (SKU: {sku}, Stock: {random_stock})")
        
        self.stdout.write(self.style.SUCCESS(f"  Imported {imported_count} variant(s) for product {item.sku}"))

    def _get_full_size_image_url(self, url):
        """
        Convert Shopify image URL to full-size original image URL.
        Removes size suffixes like _1024x1024, _2048x2048, _small, _medium, _large, etc.
        """
        if not url:
            return url
        
        # Remove common Shopify size suffixes from the URL
        # Pattern: _1024x1024, _2048x2048, _small, _medium, _large, etc.
        import re
        
        # Remove size suffixes before file extension (e.g., image_1024x1024.jpg -> image.jpg)
        # Match patterns like _1024x1024, _2048x2048, _small, _medium, _large, _grande, _master
        url = re.sub(r'_(\d+x\d+|small|medium|large|grande|master|compact|thumb)(?=\.)', '', url)
        
        # Also remove query parameters that might specify dimensions (but keep version parameter)
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Keep only the 'v' (version) parameter, remove dimension-related parameters
        if 'v' in query_params:
            new_query = {'v': query_params['v']}
            new_query_string = urlencode(new_query, doseq=True)
        else:
            new_query_string = ''
        
        # Reconstruct URL without size parameters
        new_parsed = parsed._replace(query=new_query_string)
        full_size_url = urlunparse(new_parsed)
        
        return full_size_url

    def _download_images(self, item, images):
        if not images:
            self.stdout.write(self.style.WARNING(f"No images found for product {item.sku}"))
            return
        
        # Check if main image already exists
        has_main_image = item.image and hasattr(item.image, 'name') and item.image.name
        
        # Check if gallery images exist
        existing_gallery_count = ItemGallery.objects.filter(itemId=item, status=ItemGallery.ACTIVE).count()
        
        # Skip if images already downloaded
        if has_main_image and existing_gallery_count >= len(images) - 1:
            self.stdout.write(self.style.SUCCESS(f"Skipping image download for {item.sku} - images already exist (main: {bool(has_main_image)}, gallery: {existing_gallery_count})"))
            return
        
        self.stdout.write(f"Downloading {len(images)} image(s) for product {item.sku}...")
        
        for index, image_data in enumerate(images):
            original_url = image_data.get("src")
            if not original_url:
                self.stdout.write(self.style.WARNING(f"Skipping image {index + 1} - no URL"))
                continue

            # Get full-size image URL
            full_size_url = self._get_full_size_image_url(original_url)
            
            try:
                self.stdout.write(f"  Downloading image {index + 1} (full size) from {full_size_url[:60]}...")
                response = requests.get(full_size_url, timeout=60)  # Increased timeout for larger images
                response.raise_for_status()
                
                # Get file extension from URL or default to jpg
                file_ext = 'jpg'
                if '.' in full_size_url:
                    ext = full_size_url.split('.')[-1].split('?')[0].lower()
                    if ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                        file_ext = ext
                
                filename = f"zahrarubab_{item.sku}_{index + 1}.{file_ext}"
                
                # Skip if main image already exists
                if index == 0:
                    if has_main_image:
                        self.stdout.write(f"  ⊘ Skipping main image {index + 1} - already exists")
                        continue
                    content = ContentFile(response.content)
                    item.image.save(filename, content, save=True)
                    file_size_kb = len(response.content) / 1024
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Saved main image: {filename} ({file_size_kb:.1f} KB)"))
                else:
                    # Check if this gallery image already exists
                    existing_gallery = ItemGallery.objects.filter(
                        itemId=item, 
                        status=ItemGallery.ACTIVE,
                        image__icontains=f"zahrarubab_{item.sku}_{index + 1}"
                    ).first()
                    if existing_gallery:
                        self.stdout.write(f"  ⊘ Skipping gallery image {index + 1} - already exists")
                        continue
                    content = ContentFile(response.content)
                    gallery = ItemGallery(itemId=item, status=ItemGallery.ACTIVE)
                    gallery.image.save(filename, content, save=True)
                    file_size_kb = len(response.content) / 1024
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Saved gallery image: {filename} ({file_size_kb:.1f} KB)"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed to download image {index + 1}: {str(e)}"))
                # Try fallback to original URL if full-size fails
                if full_size_url != original_url:
                    try:
                        self.stdout.write(f"  Trying fallback URL: {original_url[:60]}...")
                        response = requests.get(original_url, timeout=60)
                        response.raise_for_status()
                        file_ext = 'jpg'
                        if '.' in original_url:
                            ext = original_url.split('.')[-1].split('?')[0].lower()
                            if ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                                file_ext = ext
                        filename = f"zahrarubab_{item.sku}_{index + 1}.{file_ext}"
                        content = ContentFile(response.content)
                        if index == 0:
                            item.image.save(filename, content, save=True)
                        else:
                            gallery = ItemGallery(itemId=item, status=ItemGallery.ACTIVE)
                            gallery.image.save(filename, content, save=True)
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Saved using fallback URL: {filename}"))
                    except Exception as e2:
                        self.stdout.write(self.style.ERROR(f"  ✗ Fallback also failed: {str(e2)}"))
                continue

    def _clean_html(self, html):
        text = re.sub(r"<[^>]+>", " ", html or "")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _unique_slug(self, base, product_id):
        base_slug = slugify(base)[:140] or "zahrarubab-product"
        slug = base_slug
        if product_id:
            slug = f"{base_slug}-{product_id}"
        return slug[:150]

    def _build_item_sku(self, product, variants):
        for variant in variants:
            if variant.get("sku"):
                return variant["sku"][:100]
        product_id = product.get("id") or ""
        return f"ZR-{product_id}"[:100]

    def _to_number(self, value):
        if value is None or value == "":
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _calc_discount(self, mrp, sale_price):
        if not mrp or not sale_price or mrp <= 0 or sale_price >= mrp:
            return 0
        return int(round((mrp - sale_price) / mrp * 100))

    def _get_option_value(self, variant, option_names, keys):
        for key in keys:
            pos = option_names.get(key)
            if pos:
                value = variant.get(f"option{pos}")
                if value:
                    return value
        return None

    def _match_product_categories(self, title, tags, product_type, category_map):
        """
        Match product to appropriate categories based on title, tags, and product type.
        Returns list of matched categories.
        """
        tags_text = ", ".join(tags) if isinstance(tags, list) else (tags or "")
        search_text = " ".join([title or "", tags_text, product_type or ""]).lower()
        matches = []
        
        # Define keyword mappings for each category
        category_keywords = {
            "2 pc - cotton viscose": ["2 pc", "cotton viscose", "two piece cotton viscose"],
            "2 pc - karandi unstitched": ["2 pc karandi", "two piece karandi", "karandi unstitched 2pc"],
            "2 pc - linen unstitched": ["2 pc linen", "two piece linen", "linen unstitched 2pc"],
            "2 pc - wedding unstitched (raw silk)": ["2 pc wedding", "two piece wedding", "raw silk 2pc", "wedding unstitched 2pc"],
            "3 pc - cambric": ["3 pc cambric", "three piece cambric", "cambric 3pc"],
            "3 pc - linen unstitched": ["3 pc linen", "three piece linen", "linen unstitched 3pc"],
            "3 pc - premium khaddar": ["3 pc khaddar", "three piece khaddar", "premium khaddar 3pc"],
            "3 pc chikankari - summer": ["3 pc chikankari", "three piece chikankari", "chikankari summer 3pc"],
            "3 pc - karandi unstitched": ["3 pc karandi", "three piece karandi", "karandi unstitched 3pc"],
            "3 pc suit - karandi embroidered shawl": ["3 pc suit karandi", "karandi embroidered shawl", "3pc suit"],
            "crystal": ["crystal"],
            "daily edit - summer": ["daily edit", "summer daily"],
            "end of season": ["end of season", "sale", "clearance"],
            "formals": ["formal", "formals", "office wear", "corporate"],
            "festive embroidered - summer": ["festive embroidered", "summer festive"],
            "home couture": ["home", "homewear", "loungewear"],
            "karandi unstitched": ["karandi unstitched", "karandi"],
            "khaddar unstitched": ["khaddar unstitched", "khaddar"],
            "lavender": ["lavender"],
            "lawn": ["lawn", "lawn suit", "summer lawn"],
            "linen unstitched": ["linen unstitched", "linen"],
            "luxury pret": ["luxury pret", "luxury", "premium"],
            "luxury pret (grip)": ["luxury pret grip", "grip"],
            "men": ["men", "mens", "male"],
            "menswear": ["menswear", "men wear", "male clothing"],
            "moon light": ["moon light", "moonlight"],
            "ready to wear - summer": ["ready to wear", "rtw", "summer ready"],
            "shop by price": [],  # Will be assigned randomly or by price range
            "silk": ["silk", "raw silk", "pure silk"],
            "studio samples": ["sample", "studio sample"],
            "winter": ["winter", "winter wear", "warm"],
            "wedding festive pret": ["wedding", "festive", "bridal", "occasion wear"],
            "women": ["women", "womens", "female", "ladies"],
            "zircon": ["zircon"],
            "zardozi - nikkah edit": ["zardozi", "nikkah", "nikkah edit", "zardozi nikkah", "zr-", "zr "],
            "zardozi - nikkah edit summer": ["zardozi summer", "nikkah edit summer", "zardozi nikkah summer", "nikkah summer"],
        }
        
        # Match categories based on keywords
        for category_name, keywords in category_keywords.items():
            if category_name not in category_map:
                continue
                
            # Check if any keyword matches
            matched = False
            for keyword in keywords:
                if keyword in search_text:
                    matched = True
                    break
            
            # Special handling for certain categories
            if category_name == "shop by price":
                # Add 10% of products randomly to shop by price
                if random.random() < 0.1:
                    matched = True
            elif category_name == "end of season":
                # Check for sale/clearance indicators
                if any(word in search_text for word in ["sale", "clearance", "discount", "end of season"]):
                    matched = True
            elif category_name == "zardozi - nikkah edit":
                # More aggressive matching for Zardozi - match if product has ZR- pattern or zardozi/nikkah keywords
                if "zr-" in search_text or "zr " in search_text or "zardozi" in search_text or "nikkah" in search_text:
                    matched = True
            
            if matched:
                matches.append(category_map[category_name])
        
        # Ensure at least one category is matched (fallback to common categories)
        if not matches:
            # Default fallback categories - prioritize Zardozi if product has ZR- pattern
            if "zr-" in search_text or "zr " in search_text:
                fallback_categories = ["zardozi - nikkah edit", "women", "all in store"]
            else:
                fallback_categories = ["women", "all in store"]
            
            for fallback in fallback_categories:
                if fallback in category_map:
                    matches.append(category_map[fallback])
                    break
        
        return matches

    def _ensure_unique_variant_sku(self, sku, item, variant):
        if not sku:
            sku = f"ZR-VAR-{variant.get('id')}"
        existing = ProductVariant.objects.filter(sku=sku).first()
        if not existing:
            return sku
        if existing.item_id == item.id:
            return sku
        variant_id = variant.get("id")
        if variant_id:
            return f"{sku}-{variant_id}"[:100]
        return f"{sku}-DUP"[:100]

    def _normalize_size(self, size):
        if not size:
            return ProductVariant.SIZE_M
        normalized = str(size).strip().upper()
        size_map = {
            "XS": ProductVariant.SIZE_XS,
            "EXTRA SMALL": ProductVariant.SIZE_XS,
            "S": ProductVariant.SIZE_S,
            "SMALL": ProductVariant.SIZE_S,
            "M": ProductVariant.SIZE_M,
            "MEDIUM": ProductVariant.SIZE_M,
            "L": ProductVariant.SIZE_L,
            "LARGE": ProductVariant.SIZE_L,
            "XL": ProductVariant.SIZE_XL,
            "EXTRA LARGE": ProductVariant.SIZE_XL,
            "XXL": ProductVariant.SIZE_XXL,
            "2XL": ProductVariant.SIZE_XXL,
            "XXXL": ProductVariant.SIZE_XXXL,
            "3XL": ProductVariant.SIZE_XXXL,
        }
        return size_map.get(normalized, ProductVariant.SIZE_M)
