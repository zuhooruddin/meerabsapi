# PowerShell script to add fashion categories and set up homepage sections

Write-Host "Adding fashion categories to database..." -ForegroundColor Green
python manage.py add_fashion_categories

Write-Host ""
Write-Host "Setting up homepage sections..." -ForegroundColor Green
python manage.py setup_homepage_sections

Write-Host ""
Write-Host "✅ Fashion categories have been added and homepage sections have been configured!" -ForegroundColor Green










