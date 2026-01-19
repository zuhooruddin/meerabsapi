"""
Import products from zahrarubab.com (Shopify) into the Item and Category tables.
Run: python manage.py import_zahrarubab_products
"""
from decimal import Decimal
import re
import time
from urllib.parse import urljoin

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
        parser.add_argument("--download-images", action="store_true")
        parser.add_argument("--update-existing", action="store_true")

    def handle(self, *args, **options):
        base_url = options["base_url"].rstrip("/")
        page_size = options["page_size"]
        max_pages = options["max_pages"]
        download_images = options["download_images"]
        update_existing = options["update_existing"]

        main_category = self._get_or_create_main_category()
        category_map = self._get_or_create_target_categories(main_category)
        self.stdout.write(self.style.SUCCESS("Starting import from Zahra Rubab..."))

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
        target_names = [
            "Zardozi - Nikkah Edit",
            "Zardozi - Nikkah Edit Summer",
            "FORMALS",
            "All IN STORE",
        ]
        categories = {}
        for name in target_names:
            slug = slugify(name)[:150] or "zahrarubab-uncategorized"
            category, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": f"Imported products for {name}",
                    "parentId": parent,
                    "status": Category.ACTIVE,
                    "appliesOnline": 1,
                    "showAtHome": 0,
                    "priority": 10,
                },
            )
            categories[name.lower()] = category
        return categories

    def _import_product(self, product, main_category, category_map, download_images, update_existing):
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

        sale_price = int(min(prices)) if prices else None
        mrp = int(max(compare_prices)) if compare_prices else sale_price
        discount = self._calc_discount(mrp, sale_price)

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
        }

        if existing:
            for key, value in item_values.items():
                setattr(existing, key, value)
            item = existing
            item.save()
        else:
            item = Item.objects.create(**item_values)

        matched_categories = self._match_categories(
            title=title,
            tags=tags,
            product_type=product.get("product_type") or "",
            category_map=category_map,
        )
        if not matched_categories:
            matched_categories = [category_map["all in store"]]

        if category_map.get("all in store") not in matched_categories:
            matched_categories.append(category_map["all in store"])

        for category in matched_categories:
            CategoryItem.objects.get_or_create(
                categoryId=category,
                itemId=item,
                defaults={"level": 2, "status": CategoryItem.ACTIVE},
            )

        if download_images and images:
            self._download_images(item, images)

        self._import_variants(item, product, variants)
        return True

    def _import_variants(self, item, product, variants):
        options = product.get("options") or []
        option_names = {opt.get("name", "").lower(): opt.get("position") for opt in options}

        for variant in variants:
            color = self._get_option_value(variant, option_names, ["color", "colour"])
            size = self._get_option_value(variant, option_names, ["size"])

            if not color and not size:
                continue

            size = self._normalize_size(size)

            if not color:
                color = "Default"

            sku = variant.get("sku") or f"ZR-VAR-{variant.get('id')}"
            price = self._to_number(variant.get("price"))

            ProductVariant.objects.get_or_create(
                item=item,
                color=color[:50],
                size=size,
                defaults={
                    "sku": sku[:100],
                    "stock_quantity": variant.get("inventory_quantity") or 0,
                    "variant_price": int(price) if price is not None else None,
                    "status": ProductVariant.ACTIVE,
                },
            )

    def _download_images(self, item, images):
        for index, image_data in enumerate(images):
            url = image_data.get("src")
            if not url:
                continue

            response = requests.get(url, timeout=30)
            response.raise_for_status()
            filename = f"zahrarubab_{item.sku}_{index + 1}.jpg"
            content = ContentFile(response.content)

            if index == 0:
                item.image.save(filename, content, save=True)
            else:
                gallery = ItemGallery(itemId=item, status=ItemGallery.ACTIVE)
                gallery.image.save(filename, content, save=True)

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

    def _match_categories(self, title, tags, product_type, category_map):
        tags_text = ", ".join(tags) if isinstance(tags, list) else (tags or "")
        haystack = " ".join([title or "", tags_text, product_type or ""]).lower()
        matches = []
        for name, category in category_map.items():
            if name == "all in store":
                continue
            if name in haystack:
                matches.append(category)
        return matches

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
