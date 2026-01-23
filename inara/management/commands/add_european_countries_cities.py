"""
Django management command to add all European countries and their cities to the database
Run: python manage.py add_european_countries_cities
"""
from django.core.management.base import BaseCommand
from inara.models import Country, City


class Command(BaseCommand):
    help = 'Add all European countries and their cities to the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip countries and cities that already exist',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to add European countries and cities...'))
        
        skip_existing = options.get('skip_existing', False)
        countries_created = 0
        cities_created = 0
        countries_skipped = 0
        cities_skipped = 0
        
        # European countries with their cities
        european_data = {
            'Albania': ['Tirana', 'Durrës', 'Vlorë', 'Elbasan', 'Shkodër', 'Korçë', 'Fier', 'Berat', 'Lushnjë', 'Kavajë'],
            'Andorra': ['Andorra la Vella', 'Escaldes-Engordany', 'Encamp', 'Sant Julià de Lòria', 'La Massana', 'Canillo', 'Ordino'],
            'Armenia': ['Yerevan', 'Gyumri', 'Vanadzor', 'Etchmiadzin', 'Abovyan', 'Kapan', 'Hrazdan', 'Armavir', 'Gavar', 'Artashat'],
            'Austria': ['Vienna', 'Graz', 'Linz', 'Salzburg', 'Innsbruck', 'Klagenfurt', 'Villach', 'Wels', 'Sankt Pölten', 'Dornbirn'],
            'Azerbaijan': ['Baku', 'Ganja', 'Sumqayit', 'Lankaran', 'Mingachevir', 'Nakhchivan', 'Shaki', 'Yevlakh', 'Khankendi', 'Shamakhi'],
            'Belarus': ['Minsk', 'Gomel', 'Mogilev', 'Vitebsk', 'Grodno', 'Brest', 'Babruysk', 'Baranavichy', 'Barysaw', 'Pinsk'],
            'Belgium': ['Brussels', 'Antwerp', 'Ghent', 'Charleroi', 'Liège', 'Bruges', 'Namur', 'Leuven', 'Mons', 'Aalst'],
            'Bosnia and Herzegovina': ['Sarajevo', 'Banja Luka', 'Tuzla', 'Zenica', 'Mostar', 'Bijeljina', 'Prijedor', 'Doboj', 'Brčko', 'Bihać'],
            'Bulgaria': ['Sofia', 'Plovdiv', 'Varna', 'Burgas', 'Ruse', 'Stara Zagora', 'Pleven', 'Sliven', 'Dobrich', 'Shumen'],
            'Croatia': ['Zagreb', 'Split', 'Rijeka', 'Osijek', 'Zadar', 'Slavonski Brod', 'Pula', 'Sesvete', 'Karlovac', 'Varaždin'],
            'Cyprus': ['Nicosia', 'Limassol', 'Larnaca', 'Famagusta', 'Paphos', 'Kyrenia', 'Protaras', 'Aradippou', 'Paralimni', 'Latsia'],
            'Czech Republic': ['Prague', 'Brno', 'Ostrava', 'Plzeň', 'Liberec', 'Olomouc', 'Ústí nad Labem', 'České Budějovice', 'Hradec Králové', 'Pardubice'],
            'Denmark': ['Copenhagen', 'Aarhus', 'Odense', 'Aalborg', 'Esbjerg', 'Randers', 'Kolding', 'Horsens', 'Vejle', 'Roskilde'],
            'Estonia': ['Tallinn', 'Tartu', 'Narva', 'Pärnu', 'Kohtla-Järve', 'Viljandi', 'Rakvere', 'Maardu', 'Kuressaare', 'Sillamäe'],
            'Finland': ['Helsinki', 'Espoo', 'Tampere', 'Vantaa', 'Oulu', 'Turku', 'Jyväskylä', 'Lahti', 'Kuopio', 'Pori'],
            'France': ['Paris', 'Marseille', 'Lyon', 'Toulouse', 'Nice', 'Nantes', 'Strasbourg', 'Montpellier', 'Bordeaux', 'Lille'],
            'Georgia': ['Tbilisi', 'Kutaisi', 'Batumi', 'Rustavi', 'Zugdidi', 'Gori', 'Poti', 'Khashuri', 'Senaki', 'Zestafoni'],
            'Germany': ['Berlin', 'Hamburg', 'Munich', 'Cologne', 'Frankfurt', 'Stuttgart', 'Düsseldorf', 'Dortmund', 'Essen', 'Leipzig'],
            'Greece': ['Athens', 'Thessaloniki', 'Patras', 'Heraklion', 'Larissa', 'Volos', 'Rhodes', 'Ioannina', 'Kavala', 'Kalamata'],
            'Hungary': ['Budapest', 'Debrecen', 'Szeged', 'Miskolc', 'Pécs', 'Győr', 'Nyíregyháza', 'Kecskemét', 'Székesfehérvár', 'Szombathely'],
            'Iceland': ['Reykjavik', 'Kópavogur', 'Hafnarfjörður', 'Akureyri', 'Reykjanesbær', 'Garðabær', 'Mosfellsbær', 'Árborg', 'Akranes', 'Selfoss'],
            'Ireland': ['Dublin', 'Cork', 'Limerick', 'Galway', 'Waterford', 'Drogheda', 'Dundalk', 'Swords', 'Bray', 'Navan'],
            'Italy': ['Rome', 'Milan', 'Naples', 'Turin', 'Palermo', 'Genoa', 'Bologna', 'Florence', 'Bari', 'Catania'],
            'Kazakhstan': ['Nur-Sultan', 'Almaty', 'Shymkent', 'Karaganda', 'Aktobe', 'Taraz', 'Pavlodar', 'Ust-Kamenogorsk', 'Semey', 'Oral'],
            'Kosovo': ['Pristina', 'Prizren', 'Peja', 'Gjakova', 'Mitrovica', 'Gjilan', 'Ferizaj', 'Podujeva', 'Rahovec', 'Lipjan'],
            'Latvia': ['Riga', 'Daugavpils', 'Liepāja', 'Jelgava', 'Jūrmala', 'Ventspils', 'Rēzekne', 'Valmiera', 'Jēkabpils', 'Ogre'],
            'Liechtenstein': ['Vaduz', 'Schaan', 'Balzers', 'Triesen', 'Eschen', 'Mauren', 'Triesenberg', 'Ruggell', 'Gamprin', 'Planken'],
            'Lithuania': ['Vilnius', 'Kaunas', 'Klaipėda', 'Šiauliai', 'Panevėžys', 'Alytus', 'Marijampolė', 'Mazeikiai', 'Jonava', 'Utena'],
            'Luxembourg': ['Luxembourg', 'Esch-sur-Alzette', 'Differdange', 'Dudelange', 'Ettelbruck', 'Diekirch', 'Wiltz', 'Echternach', 'Rumelange', 'Grevenmacher'],
            'Malta': ['Valletta', 'Birkirkara', 'Mosta', 'Qormi', 'Sliema', 'Żabbar', 'Naxxar', 'San Ġwann', 'Żejtun', 'Rabat'],
            'Moldova': ['Chișinău', 'Bălți', 'Tiraspol', 'Bender', 'Rîbnița', 'Cahul', 'Ungheni', 'Soroca', 'Orhei', 'Comrat'],
            'Monaco': ['Monaco', 'Monte Carlo', 'La Condamine', 'Fontvieille', 'Moneghetti'],
            'Montenegro': ['Podgorica', 'Nikšić', 'Herceg Novi', 'Pljevlja', 'Bijelo Polje', 'Cetinje', 'Bar', 'Budva', 'Berane', 'Ulcinj'],
            'Netherlands': ['Amsterdam', 'Rotterdam', 'The Hague', 'Utrecht', 'Eindhoven', 'Groningen', 'Tilburg', 'Almere', 'Breda', 'Nijmegen'],
            'North Macedonia': ['Skopje', 'Bitola', 'Kumanovo', 'Prilep', 'Tetovo', 'Veles', 'Štip', 'Ohrid', 'Gostivar', 'Strumica'],
            'Norway': ['Oslo', 'Bergen', 'Stavanger', 'Trondheim', 'Drammen', 'Fredrikstad', 'Kristiansand', 'Sandnes', 'Tromsø', 'Sarpsborg'],
            'Poland': ['Warsaw', 'Kraków', 'Łódź', 'Wrocław', 'Poznań', 'Gdańsk', 'Szczecin', 'Bydgoszcz', 'Lublin', 'Katowice'],
            'Portugal': ['Lisbon', 'Porto', 'Vila Nova de Gaia', 'Amadora', 'Braga', 'Funchal', 'Coimbra', 'Setúbal', 'Almada', 'Agualva-Cacém'],
            'Romania': ['Bucharest', 'Cluj-Napoca', 'Timișoara', 'Iași', 'Constanța', 'Craiova', 'Brașov', 'Galați', 'Ploiești', 'Oradea'],
            'Russia': ['Moscow', 'Saint Petersburg', 'Novosibirsk', 'Yekaterinburg', 'Nizhny Novgorod', 'Kazan', 'Chelyabinsk', 'Omsk', 'Samara', 'Rostov-on-Don'],
            'San Marino': ['San Marino', 'Serravalle', 'Borgo Maggiore', 'Domagnano', 'Fiorentino', 'Acquaviva', 'Chiesanuova', 'Faetano', 'Montegiardino'],
            'Serbia': ['Belgrade', 'Novi Sad', 'Niš', 'Kragujevac', 'Subotica', 'Zrenjanin', 'Pančevo', 'Čačak', 'Kraljevo', 'Smederevo'],
            'Slovakia': ['Bratislava', 'Košice', 'Prešov', 'Žilina', 'Banská Bystrica', 'Nitra', 'Trnava', 'Trenčín', 'Martin', 'Poprad'],
            'Slovenia': ['Ljubljana', 'Maribor', 'Celje', 'Kranj', 'Velenje', 'Koper', 'Novo Mesto', 'Ptuj', 'Trbovlje', 'Kamnik'],
            'Spain': ['Madrid', 'Barcelona', 'Valencia', 'Seville', 'Zaragoza', 'Málaga', 'Murcia', 'Palma', 'Las Palmas', 'Bilbao'],
            'Sweden': ['Stockholm', 'Gothenburg', 'Malmö', 'Uppsala', 'Västerås', 'Örebro', 'Linköping', 'Helsingborg', 'Jönköping', 'Norrköping'],
            'Switzerland': ['Bern', 'Zurich', 'Geneva', 'Basel', 'Lausanne', 'Winterthur', 'St. Gallen', 'Lucerne', 'Lugano', 'Biel'],
            'Turkey': ['Ankara', 'Istanbul', 'Izmir', 'Bursa', 'Adana', 'Gaziantep', 'Antalya', 'Konya', 'Kayseri', 'Mersin'],
            'Ukraine': ['Kyiv', 'Kharkiv', 'Odessa', 'Dnipro', 'Donetsk', 'Zaporizhzhia', 'Lviv', 'Kryvyi Rih', 'Mykolaiv', 'Mariupol'],
            'United Kingdom': ['London', 'Birmingham', 'Manchester', 'Glasgow', 'Liverpool', 'Leeds', 'Sheffield', 'Edinburgh', 'Bristol', 'Cardiff'],
            'Vatican City': ['Vatican City'],
        }
        
        # Add countries and cities
        for country_name, cities in european_data.items():
            # Add country
            country, created = Country.objects.get_or_create(
                name=country_name,
                defaults={
                    'type': 'MAJOR' if country_name in ['France', 'Germany', 'Italy', 'Spain', 'United Kingdom', 'Poland', 'Netherlands', 'Belgium', 'Greece', 'Portugal', 'Czech Republic', 'Romania', 'Hungary', 'Sweden', 'Austria', 'Switzerland', 'Denmark', 'Finland', 'Norway', 'Ireland'] else 'OTHER',
                    'status': 'ACTIVE'
                }
            )
            
            if created:
                countries_created += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created country: {country_name}'))
            else:
                if skip_existing:
                    countries_skipped += 1
                    self.stdout.write(self.style.WARNING(f'⊘ Skipped existing country: {country_name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'⊘ Country already exists: {country_name}'))
            
            # Add cities for this country
            for city_name in cities:
                city, city_created = City.objects.get_or_create(
                    name=city_name,
                    country=country,
                    defaults={
                        'type': 'MAJOR' if city_name == cities[0] else 'OTHER',  # Capital city is MAJOR
                        'status': 'ACTIVE'
                    }
                )
                
                if city_created:
                    cities_created += 1
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created city: {city_name}'))
                else:
                    if skip_existing:
                        cities_skipped += 1
                    else:
                        self.stdout.write(self.style.WARNING(f'  ⊘ City already exists: {city_name}'))
        
        # Summary
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Successfully completed!\n'
            f'   - Countries created: {countries_created}\n'
            f'   - Cities created: {cities_created}\n'
            f'   - Countries skipped: {countries_skipped}\n'
            f'   - Cities skipped: {cities_skipped}\n'
        ))




