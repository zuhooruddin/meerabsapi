from django.contrib import admin
from django.contrib.admin import AdminSite

# Customize Django Admin Panel Branding
admin.site.site_header = "Meerab's Wardrobe Admin"
admin.site.site_title = "Meerab's Wardrobe Admin Portal"
admin.site.index_title = "Welcome to Meerab's Wardrobe Administration"

# Register your models here.
# Models can be registered here when needed
# Example:
# from .models import YourModel
# admin.site.register(YourModel)
