from django.contrib import admin
from django.contrib.admin import AdminSite
from inara.models import Item, ProductVariant, Category, Bundle, BundleItem, Order, OrderDescription, User

# Customize Django Admin Panel Branding
admin.site.site_header = "Meerab's Wardrobe Admin"
admin.site.site_title = "Meerab's Wardrobe Admin Portal"
admin.site.index_title = "Welcome to Meerab's Wardrobe Administration"


# Inline admin for Product Variants
class ProductVariantInline(admin.TabularInline):
    """
    Inline admin for managing product variants within the Item admin.
    Allows admins to add/edit color, size, stock, and pricing for each variant.
    """
    model = ProductVariant
    extra = 1  # Number of empty forms to display
    fields = ['color', 'color_hex', 'size', 'sku', 'stock_quantity', 'variant_price', 'status']
    list_display = ['color', 'size', 'sku', 'stock_quantity', 'variant_price', 'status']
    ordering = ['color', 'size']


# Enhanced Item (Product) Admin
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """
    Enhanced admin for Item (Product) model with variant management.
    Supports clothing-specific fields and inline variant management.
    """
    list_display = ['name', 'sku', 'brand', 'product_category', 'base_price', 'discount_price', 'is_active', 'status', 'isFeatured']
    list_filter = ['product_category', 'brand', 'is_active', 'status', 'isFeatured', 'isNewArrival']
    search_fields = ['name', 'sku', 'brand', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'sku', 'image', 'description')
        }),
        ('Clothing Details', {
            'fields': ('brand', 'product_category', 'base_price', 'discount_price', 'is_active')
        }),
        ('Legacy Pricing (for backward compatibility)', {
            'fields': ('mrp', 'salePrice', 'discount'),
            'classes': ('collapse',)
        }),
        ('Inventory & Stock', {
            'fields': ('stock', 'stockCheckQty'),
            'classes': ('collapse',)
        }),
        ('SEO & Marketing', {
            'fields': ('metaUrl', 'metaTitle', 'metaDescription', 'isFeatured', 'isNewArrival', 'newArrivalTill'),
            'classes': ('collapse',)
        }),
        ('Status & Visibility', {
            'fields': ('appliesOnline', 'status')
        }),
    )
    
    inlines = [ProductVariantInline]
    
    def save_model(self, request, obj, form, change):
        """Custom save to handle additional logic if needed"""
        super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        """Save the inline formset (variants)"""
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()


# ProductVariant Admin (standalone)
@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """
    Standalone admin for ProductVariant model.
    Useful for bulk variant management across products.
    """
    list_display = ['item', 'color', 'size', 'sku', 'stock_quantity', 'variant_price', 'status']
    list_filter = ['color', 'size', 'status', 'item__brand', 'item__product_category']
    search_fields = ['sku', 'item__name', 'color']
    list_editable = ['stock_quantity', 'variant_price', 'status']
    ordering = ['item', 'color', 'size']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('item',)
        }),
        ('Variant Details', {
            'fields': ('color', 'color_hex', 'size', 'sku')
        }),
        ('Stock & Pricing', {
            'fields': ('stock_quantity', 'variant_price')
        }),
        ('Status', {
            'fields': ('status',)
        }),
    )


# Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parentId', 'isBrand', 'status', 'showAtHome']
    list_filter = ['isBrand', 'status', 'showAtHome']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}


# Order Admin
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['orderNo', 'custName', 'custEmail', 'custPhone', 'totalBill', 'status', 'timestamp']
    list_filter = ['status', 'paymentMethod', 'timestamp']
    search_fields = ['orderNo', 'custName', 'custEmail', 'custPhone']
    readonly_fields = ['timestamp']


# OrderDescription Admin
@admin.register(OrderDescription)
class OrderDescriptionAdmin(admin.ModelAdmin):
    list_display = ['order', 'itemName', 'itemSku', 'selected_color', 'selected_size', 'itemQty', 'itemTotalPrice']
    list_filter = ['item_type', 'selected_color', 'selected_size']
    search_fields = ['itemName', 'itemSku', 'order__orderNo']
    readonly_fields = ['variant_details_display']
    
    def variant_details_display(self, obj):
        """Display variant details in a readable format"""
        if obj.variant:
            return f"{obj.variant.item.name} - {obj.variant.color} - {obj.variant.size}"
        return "No variant selected"
    variant_details_display.short_description = "Variant Details"


# User Admin
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'name', 'role', 'status', 'is_active']
    list_filter = ['role', 'status', 'is_active']
    search_fields = ['username', 'email', 'name']
    fieldsets = (
        ('Authentication', {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Info', {
            'fields': ('name', 'phone', 'mobile', 'gender', 'address', 'profile_pic')
        }),
        ('Permissions', {
            'fields': ('role', 'status', 'is_staff', 'is_superuser', 'is_active')
        }),
    )
