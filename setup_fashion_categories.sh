#!/bin/bash
# Script to add fashion categories and set up homepage sections

echo "Adding fashion categories to database..."
python manage.py add_fashion_categories

echo ""
echo "Setting up homepage sections..."
python manage.py setup_homepage_sections

echo ""
echo "✅ Fashion categories have been added and homepage sections have been configured!"

