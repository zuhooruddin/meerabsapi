"""
Import specific products from zahrarubab.com by URL and mark them as featured and new arrival.
Run: python manage.py import_zahrarubab_products_by_url --urls "url1,url2,url3"
"""
from decimal import Decimal
import re
import time
import random
from urllib.parse import urlparse, urljoin

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from inara.models import Category, CategoryItem, Item, ItemGallery, ProductVariant


class Command(BaseCommand):
    help = "Import specific products from zahrarubab.com by URL and mark as featured/new arrival."

    def add_arguments(self, parser):
        parser.add_argument(
            "--urls",
            type=str,
            required=True,
            help='Comma-separated list of product URLs (e.g., "url1,url2,url3")',
        )
        parser.add_argument(
            "--base-url",
            default="https://zahrarubab.com",
            help="Base URL for the Shopify store",
        )
        parser.add_argument(
            "--no-download-images",
            dest="download_images",
            action="store_false",
            help="Skip downloading images (default: images are downloaded)",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update existing products instead of skipping",
        )
        parser.add_argument(
            "--exchange-rate",
            type=float,
            default=0.0033,
            help="Exchange rate to convert prices to Euro (default: 0.0033 for PKR to EUR, meaning 1 EUR ≈ 303 PKR)",
        )

    def handle(self, *args, **options):
        urls_string = options["urls"]
        base_url = options["base_url"].rstrip("/")
        download_images = options.get("download_images")
        if download_images is None:
            download_images = True
        update_existing = options.get("update_existing", False)
        exchange_rate = options.get("exchange_rate", 0.0033)

        # Parse URLs
        urls = [url.strip() for url in urls_string.split(",") if url.strip()]
        if not urls:
            self.stdout.write(self.style.ERROR("No valid URLs provided"))
            return

        self.stdout.write(f"Using exchange rate: {exchange_rate} (1 source currency = {exchange_rate} EUR)")
        self.stdout.write(self.style.SUCCESS(f"Starting import of {len(urls)} products from URLs..."))
        self.stdout.write(f"Download images: {download_images}")

        main_category = self._get_or_create_main_category()
        category_map = self._get_or_create_target_categories(main_category)

        imported = 0
        skipped = 0
        errors = 0

        for url in urls:
            try:
                # Extract handle from URL
                handle = self._extract_handle_from_url(url)
                if not handle:
                    self.stdout.write(self.style.ERROR(f"Could not extract handle from URL: {url}"))
                    errors += 1
                    continue

                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"Processing: {url}")
                self.stdout.write(f"Extracted handle: {handle}")

                # Fetch product from Shopify API
                product = self._fetch_product_by_handle(base_url, handle)
                if not product:
                    self.stdout.write(self.style.ERROR(f"Product not found: {handle}"))
                    errors += 1
                    continue

                # Import product with featured and new arrival flags
                result = self._import_product(
                    product,
                    main_category=main_category,
                    category_map=category_map,
                    download_images=download_images,
                    update_existing=update_existing,
                    exchange_rate=exchange_rate,
                    force_featured=True,  # Always mark as featured and new arrival
                )
                if result:
                    imported += 1
                else:
                    skipped += 1

                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {url}: {str(e)}"))
                errors += 1
                continue

        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("SUMMARY:"))
        self.stdout.write(f"  Imported: {imported}")
        self.stdout.write(f"  Skipped: {skipped}")
        self.stdout.write(f"  Errors: {errors}")

    def _extract_handle_from_url(self, url):
        """Extract product handle from zahrarubab.com URL"""
        try:
            # URL format: https://zahrarubab.com/products/zr-2571-ice-blue
            # or: https://zahrarubab.com/products/zr-2571-ice-blue?_pos=2&_sid=...
            
            # Use regex to extract handle more reliably
            pattern = r'/products/([^/?]+)'
            match = re.search(pattern, url)
            if match:
                handle = match.group(1)
                return handle.strip()
            
            # Fallback: parse URL manually
            parsed = urlparse(url)
            path = parsed.path.strip("/")
            
            # Extract handle from path
            if path.startswith("products/"):
                handle = path[9:]  # Remove "products/" prefix (9 characters)
            elif "/products/" in path:
                handle = path.split("/products/")[-1]
            else:
                # If path doesn't contain "products/", assume the whole path is the handle
                handle = path
            
            # Remove query parameters
            handle = handle.split("?")[0]
            handle = handle.strip("/")
            
            if handle:
                return handle
            return None
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Error extracting handle from {url}: {e}"))
            return None

    def _fetch_product_by_handle(self, base_url, handle):
        """Fetch a single product from Shopify API by handle"""
        url = urljoin(base_url, f"/products/{handle}.json")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            payload = response.json()
            return payload.get("product")
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch product {handle}: {e}"))
            return None

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

    def _import_product(
        self,
        product,
        main_category,
        category_map,
        download_images,
        update_existing,
        exchange_rate=0.0033,
        force_featured=False,
    ):
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
            self.stdout.write(self.style.WARNING(f"  Product {item_sku} already exists, skipping (use --update-existing to update)"))
            return False

        prices = [self._to_number(v.get("price")) for v in variants if v.get("price")]
        compare_prices = [
            self._to_number(v.get("compare_at_price"))
            for v in variants
            if v.get("compare_at_price")
        ]

        # Convert prices to Euro
        mrp_raw = max(compare_prices) if compare_prices else (min(prices) if prices else None)
        mrp = int(round(mrp_raw * exchange_rate)) if mrp_raw is not None else None

        # Calculate discount percentage
        if compare_prices and prices:
            min_price = min(prices)
            max_compare = max(compare_prices)
            min_price_eur = int(round(min_price * exchange_rate))
            max_compare_eur = int(round(max_compare * exchange_rate))

            if max_compare_eur > min_price_eur:
                discount = self._calc_discount(max_compare_eur, min_price_eur)
            else:
                discount = 0
        else:
            discount = 0

        sale_price = mrp

        # Force featured and new arrival if requested
        if force_featured:
            is_new = 1
            is_featured = 1
            self.stdout.write(self.style.SUCCESS(f"  → Marked as NEW ARRIVAL and FEATURED: {item_sku}"))
        else:
            is_new = 0
            is_featured = 0

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
            self.stdout.write(self.style.SUCCESS(f"  ✓ Updated product: {item_sku}"))
        else:
            item = Item.objects.create(**item_values)
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created product: {item_sku}"))

        # Match product to appropriate categories
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

        # Download images if enabled
        if download_images:
            if images:
                self._download_images(item, images)
            else:
                self.stdout.write(self.style.WARNING(f"  No images to download for product {item.sku}"))
        else:
            self.stdout.write(self.style.WARNING(f"  Image downloading is disabled for product {item.sku}"))

        self._import_variants(item, product, variants, exchange_rate)
        return True

    def _import_variants(self, item, product, variants, exchange_rate=0.92):
        options = product.get("options") or []
        option_names = {opt.get("name", "").lower(): opt.get("position") for opt in options}

        if not variants:
            self.stdout.write(self.style.WARNING(f"  No variants found for product {item.sku}"))
            return

        self.stdout.write(f"  Importing {len(variants)} variant(s) for product {item.sku}...")
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
            price = price_raw * exchange_rate if price_raw is not None else None

            variant_obj = ProductVariant.objects.filter(sku=sku).first()

            random_stock = random.randint(2, 229)

            if variant_obj:
                variant_obj.item = item
                variant_obj.color = color[:50]
                variant_obj.size = size
                variant_obj.stock_quantity = random_stock
                variant_obj.variant_price = int(round(price)) if price is not None else None
                variant_obj.status = ProductVariant.ACTIVE
                variant_obj.save()
                imported_count += 1
                self.stdout.write(f"    ✓ Updated variant: {color} - {size} (SKU: {sku}, Stock: {random_stock})")
            else:
                random_stock = random.randint(2, 229)

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
                if not created:
                    variant_obj.sku = sku[:100]
                    variant_obj.stock_quantity = random_stock
                    variant_obj.variant_price = int(round(price)) if price is not None else None
                    variant_obj.status = ProductVariant.ACTIVE
                    variant_obj.save()
                    imported_count += 1
                    self.stdout.write(f"    ✓ Updated variant: {color} - {size} (SKU: {sku}, Stock: {random_stock})")
                else:
                    imported_count += 1
                    self.stdout.write(f"    ✓ Created variant: {color} - {size} (SKU: {sku}, Stock: {random_stock})")

        self.stdout.write(self.style.SUCCESS(f"  Imported {imported_count} variant(s) for product {item.sku}"))

    def _get_full_size_image_url(self, url):
        """Convert Shopify image URL to full-size original image URL."""
        if not url:
            return url

        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

        url = re.sub(r"_(\d+x\d+|small|medium|large|grande|master|compact|thumb)(?=\.)", "", url)

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        if "v" in query_params:
            new_query = {"v": query_params["v"]}
            new_query_string = urlencode(new_query, doseq=True)
        else:
            new_query_string = ""

        new_parsed = parsed._replace(query=new_query_string)
        full_size_url = urlunparse(new_parsed)

        return full_size_url

    def _download_images(self, item, images):
        if not images:
            self.stdout.write(self.style.WARNING(f"  No images found for product {item.sku}"))
            return

        # A "real" main image means it is NOT the default placeholder.
        # item.image always has a name (the placeholder), so we must explicitly
        # check it is NOT the default before treating it as already-downloaded.
        DEFAULT_PLACEHOLDER = "idris/asset/default-item-image.jpg"
        has_main_image = (
            item.image
            and hasattr(item.image, "name")
            and item.image.name
            and item.image.name != DEFAULT_PLACEHOLDER
        )
        existing_gallery_count = ItemGallery.objects.filter(itemId=item, status=ItemGallery.ACTIVE).count()

        if has_main_image and existing_gallery_count >= len(images) - 1:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Skipping image download for {item.sku} - images already exist (main: {bool(has_main_image)}, gallery: {existing_gallery_count})"
                )
            )
            return

        self.stdout.write(f"  Downloading {len(images)} image(s) for product {item.sku}...")

        for index, image_data in enumerate(images):
            original_url = image_data.get("src")
            if not original_url:
                self.stdout.write(self.style.WARNING(f"    Skipping image {index + 1} - no URL"))
                continue

            full_size_url = self._get_full_size_image_url(original_url)

            try:
                self.stdout.write(f"    Downloading image {index + 1} (full size) from {full_size_url[:60]}...")
                response = requests.get(full_size_url, timeout=60)
                response.raise_for_status()

                file_ext = "jpg"
                if "." in full_size_url:
                    ext = full_size_url.split(".")[-1].split("?")[0].lower()
                    if ext in ["jpg", "jpeg", "png", "webp", "gif"]:
                        file_ext = ext

                filename = f"zahrarubab_{item.sku}_{index + 1}.{file_ext}"

                if index == 0:
                    if has_main_image:
                        self.stdout.write(f"    ⊘ Skipping main image {index + 1} - already exists")
                        continue
                    content = ContentFile(response.content)
                    item.image.save(filename, content, save=True)
                    file_size_kb = len(response.content) / 1024
                    self.stdout.write(self.style.SUCCESS(f"    ✓ Saved main image: {filename} ({file_size_kb:.1f} KB)"))
                else:
                    existing_gallery = ItemGallery.objects.filter(
                        itemId=item,
                        status=ItemGallery.ACTIVE,
                        image__icontains=f"zahrarubab_{item.sku}_{index + 1}",
                    ).first()
                    if existing_gallery:
                        self.stdout.write(f"    ⊘ Skipping gallery image {index + 1} - already exists")
                        continue
                    content = ContentFile(response.content)
                    gallery = ItemGallery(itemId=item, status=ItemGallery.ACTIVE)
                    gallery.image.save(filename, content, save=True)
                    file_size_kb = len(response.content) / 1024
                    self.stdout.write(self.style.SUCCESS(f"    ✓ Saved gallery image: {filename} ({file_size_kb:.1f} KB)"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"    ✗ Failed to download image {index + 1}: {str(e)}"))
                if full_size_url != original_url:
                    try:
                        self.stdout.write(f"    Trying fallback URL: {original_url[:60]}...")
                        response = requests.get(original_url, timeout=60)
                        response.raise_for_status()
                        file_ext = "jpg"
                        if "." in original_url:
                            ext = original_url.split(".")[-1].split("?")[0].lower()
                            if ext in ["jpg", "jpeg", "png", "webp", "gif"]:
                                file_ext = ext
                        filename = f"zahrarubab_{item.sku}_{index + 1}.{file_ext}"
                        content = ContentFile(response.content)
                        if index == 0:
                            item.image.save(filename, content, save=True)
                        else:
                            gallery = ItemGallery(itemId=item, status=ItemGallery.ACTIVE)
                            gallery.image.save(filename, content, save=True)
                        self.stdout.write(self.style.SUCCESS(f"    ✓ Saved using fallback URL: {filename}"))
                    except Exception as e2:
                        self.stdout.write(self.style.ERROR(f"    ✗ Fallback also failed: {str(e2)}"))
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
        """Match product to appropriate categories based on title, tags, and product type."""
        tags_text = ", ".join(tags) if isinstance(tags, list) else (tags or "")
        search_text = " ".join([title or "", tags_text, product_type or ""]).lower()
        matches = []

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
            "shop by price": [],
            "silk": ["silk", "raw silk", "pure silk"],
            "studio samples": ["sample", "studio sample"],
            "winter": ["winter", "winter wear", "warm"],
            "wedding festive pret": ["wedding", "festive", "bridal", "occasion wear"],
            "women": ["women", "womens", "female", "ladies"],
            "zircon": ["zircon"],
            "zardozi - nikkah edit": ["zardozi", "nikkah", "nikkah edit", "zardozi nikkah", "zr-", "zr "],
            "zardozi - nikkah edit summer": ["zardozi summer", "nikkah edit summer", "zardozi nikkah summer", "nikkah summer"],
        }

        for category_name, keywords in category_keywords.items():
            if category_name not in category_map:
                continue

            matched = False
            for keyword in keywords:
                if keyword in search_text:
                    matched = True
                    break

            if category_name == "shop by price":
                if random.random() < 0.1:
                    matched = True
            elif category_name == "end of season":
                if any(word in search_text for word in ["sale", "clearance", "discount", "end of season"]):
                    matched = True
            elif category_name == "zardozi - nikkah edit":
                if "zr-" in search_text or "zr " in search_text or "zardozi" in search_text or "nikkah" in search_text:
                    matched = True

            if matched:
                matches.append(category_map[category_name])

        if not matches:
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
