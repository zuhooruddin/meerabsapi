# Add European Countries and Cities

This document explains how to add all European countries and their cities to the database.

## Overview

A Django management command has been created to bulk add all European countries and their major cities to the database. This includes:

- **50 European countries** (including transcontinental countries like Turkey, Russia, Kazakhstan, etc.)
- **500+ cities** across all European countries

## Running the Command

### Basic Usage

Navigate to the Django project directory and run:

```bash
cd chitralhivedjango
python manage.py add_european_countries_cities
```

### Skip Existing Records

If you want to skip countries and cities that already exist (to avoid errors), use:

```bash
python manage.py add_european_countries_cities --skip-existing
```

## What Gets Added

### Countries
- Each country is added with:
  - **Name**: Full country name
  - **Type**: `MAJOR` for major European countries (France, Germany, Italy, Spain, UK, etc.) or `OTHER` for smaller countries
  - **Status**: `ACTIVE`

### Cities
- Each city is added with:
  - **Name**: City name
  - **Country**: Foreign key to the country
  - **Type**: `MAJOR` for capital cities, `OTHER` for other cities
  - **Status**: `ACTIVE`

## Countries Included

The script includes all 50 European countries:
- Albania, Andorra, Armenia, Austria, Azerbaijan
- Belarus, Belgium, Bosnia and Herzegovina, Bulgaria
- Croatia, Cyprus, Czech Republic
- Denmark
- Estonia
- Finland, France
- Georgia, Germany, Greece
- Hungary
- Iceland, Ireland, Italy
- Kazakhstan, Kosovo
- Latvia, Liechtenstein, Lithuania, Luxembourg
- Malta, Moldova, Monaco, Montenegro
- Netherlands, North Macedonia, Norway
- Poland, Portugal
- Romania, Russia
- San Marino, Serbia, Slovakia, Slovenia, Spain, Sweden, Switzerland
- Turkey
- Ukraine, United Kingdom
- Vatican City

## Cities Included

Each country includes:
- Capital city (marked as MAJOR type)
- 5-10 major cities per country
- Total of 500+ cities across Europe

## Output

The command will display:
- ✓ Success messages for each country and city created
- ⊘ Warning messages for existing records (if not using --skip-existing)
- Summary statistics at the end showing:
  - Countries created
  - Cities created
  - Countries skipped
  - Cities skipped

## Example Output

```
Starting to add European countries and cities...
✓ Created country: Albania
  ✓ Created city: Tirana
  ✓ Created city: Durrës
  ✓ Created city: Vlorë
...
✅ Successfully completed!
   - Countries created: 50
   - Cities created: 523
   - Countries skipped: 0
   - Cities skipped: 0
```

## Notes

- The script uses `get_or_create()` to avoid duplicates
- If a country or city already exists, it will be skipped (unless --skip-existing flag is used, which provides cleaner output)
- All countries and cities are set to `ACTIVE` status by default
- Capital cities are marked as `MAJOR` type, others as `OTHER` type

## Troubleshooting

If you encounter errors:
1. Make sure you're in the correct directory (`chitralhivedjango`)
2. Ensure Django is properly set up and the database is accessible
3. Check that the `Country` and `City` models are properly migrated
4. Use `--skip-existing` flag if you're re-running the script

## API Endpoints

After running this script, the countries and cities will be available through:
- Country Configuration: `/admin/country/country-configuration`
- City Configuration: `/admin/country/city-configuration`

The data can also be accessed via the API endpoints:
- `getallcountry` - Get all countries
- `getAllCity` - Get all cities
- `getcountries` - Get countries list for dropdowns




