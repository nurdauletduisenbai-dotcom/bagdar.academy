"""
Разбор данных OpenStreetMap (© участники OpenStreetMap, лицензия ODbL) без зависимостей от Django:
используется командой import_schools и для подготовки встроенного снимка.
"""
import math
import re

# Школы и населённые пункты одного региона (area id = 3600000000 + id отношения региона)
SCHOOLS_QUERY = '[out:json][timeout:300];area({area})->.a;nwr(area.a)[amenity=school][name];out tags center;'
PLACES_QUERY = '[out:json][timeout:300];area({area})->.a;node(area.a)[place~"^(city|town|village)$"][name];out;'

# Школа относится к пункту, если он ближе этого радиуса (км)
PLACE_RADIUS_KM = {'city': 15.0, 'town': 8.0, 'village': 4.0}

# Не школа: здания, служебные постройки и названия без конкретики
JUNK_RE = re.compile(r'корпус|котельн|столов|спортзал|спортивный зал|пристройк|гараж|склад|^(школа|мектеп|мектебі|school|сш|сош)$',
                     re.I)


def _point(element: dict):
    if 'lat' in element:
        return element['lat'], element['lon']
    center = element.get('center')
    return (center['lat'], center['lon']) if center else None


def _distance_km(a, b) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def _place_name(tags: dict) -> str:
    return tags.get('name:ru') or tags.get('name') or ''


def nearest_locality(point, places: list[tuple[tuple[float, float], str, str]]) -> str:
    """places: [((lat, lon), place_type, name)]. Ближайший пункт в пределах радиуса своего типа."""
    best, best_d = '', float('inf')
    for p, kind, name in places:
        if abs(p[0] - point[0]) > 0.2 or abs(p[1] - point[1]) > 0.3:  # быстрый отсев дальних
            continue
        d = _distance_km(point, p)
        if d <= PLACE_RADIUS_KM.get(kind, 4.0) and d < best_d:
            best, best_d = name, d
    return best


def build_records(region_code: str, school_elements: list[dict], place_elements: list[dict],
                  city_name: str | None = None) -> list[dict]:
    """Записи для import_records. Для городов республиканского значения пункт — сам город."""
    places = [(pt, e['tags'].get('place', ''), _place_name(e['tags']))
              for e in place_elements if (pt := _point(e)) and _place_name(e.get('tags', {}))]
    records = []
    for e in school_elements:
        t = e.get('tags', {})
        name = (t.get('name') or '').strip()
        if not name or JUNK_RE.search(name):
            continue
        locality = city_name or t.get('addr:city') or t.get('addr:town') or t.get('addr:village') or t.get('addr:place') or ''
        if not locality and (pt := _point(e)):
            locality = nearest_locality(pt, places)
        records.append({
            'external_id': f"osm:{e['type']}/{e['id']}",
            'name': name,
            'name_kk': t.get('name:kk', ''),
            'name_ru': t.get('name:ru', ''),
            'region_code': region_code,
            'locality': locality,
        })
    return records
