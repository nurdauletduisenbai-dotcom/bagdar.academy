"""
Загрузка справочника школ: из файла (JSON/CSV) или из OpenStreetMap (данные © участники OpenStreetMap, ODbL).

Формат записи (JSON-список или колонки CSV):
    external_id, name, name_kk, name_ru, region_code, locality, kind
Обязательны name и region_code (ISO 3166-2, например KZ-75). kind пустой — определяется по названию.
"""
import csv
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

from django.db import transaction

from .models import Region, School
from .osm import JUNK_RE, PLACES_QUERY, SCHOOLS_QUERY, build_records

OVERPASS_URL = 'https://overpass-api.de/api/interpreter'
USER_AGENT = 'bagdar-academy-school-import/1.0'

# Не учебные заведения для школьников — в справочник не берём
SKIP_RE = re.compile(r'автошкол|автомектеп|driving|вождени|автоинструктор', re.I)

KIND_RULES = [
    (School.Kind.SPECIALIZED, r'назарбаев|nazarbayev|\bниш\b|\bnis\b|рфмш|республиканск\w* физико|білім[- ]?инновац|билим[- ]?инновац'),
    (School.Kind.EXTRA, r'музыкал|музыка|өнер|искусств|художеств|сурет|спорт|дюсш|балалар-жасөспірімдер|хореограф|'
                        r'art school|music|дополнительн\w* образован|қосымша білім'),
    (School.Kind.COLLEGE, r'колледж|college'),
    (School.Kind.GYMNASIUM, r'гимназ'),
    (School.Kind.LYCEUM, r'лице[йі]|lyceum'),
    (School.Kind.CLUB, r'кружок|секци|үйірме|оқушылар үйі|дом школьник|станци\w* юн'),
    (School.Kind.CENTER, r'центр\b|центр развития|орталығ|academy|академи|курсы'),
]


def detect_kind(*names: str) -> str:
    text = ' '.join(n for n in names if n).lower()
    for kind, pattern in KIND_RULES:
        if re.search(pattern, text):
            return kind
    return School.Kind.SCHOOL


def _norm(text: str) -> str:
    return re.sub(r'[\s"«»№#.,-]+', ' ', (text or '').lower()).strip()


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0


def read_file(path: str) -> list[dict]:
    if path.endswith('.json'):
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


@transaction.atomic
def import_records(records: list[dict], source: str = School.Source.IMPORT) -> ImportResult:
    """Идемпотентно: по external_id обновляет, иначе ищет дубль по (регион, пункт, название)."""
    regions = {r.code: r for r in Region.objects.all()}
    seen = {(s.region_id, _norm(s.locality), _norm(s.name)): s
            for s in School.objects.only('id', 'region_id', 'locality', 'name')}
    result = ImportResult()
    for rec in records:
        name = (rec.get('name') or rec.get('name_ru') or rec.get('name_kk') or '').strip()
        region = regions.get((rec.get('region_code') or '').strip())
        if not name or not region or SKIP_RE.search(name) or JUNK_RE.search(name):
            result.skipped += 1
            continue
        fields = {
            'name': name[:255],
            'name_kk': (rec.get('name_kk') or '').strip()[:255],
            'name_ru': (rec.get('name_ru') or '').strip()[:255],
            'region': region,
            'locality': (rec.get('locality') or '').strip()[:120],
            'kind': rec.get('kind') or detect_kind(name, rec.get('name_ru'), rec.get('name_kk')),
            'source': source,
        }
        ext = (rec.get('external_id') or '').strip() or None
        key = (region.id, _norm(fields['locality']), _norm(name))
        if ext and School.objects.filter(external_id=ext).update(**fields):
            result.updated += 1
            continue
        if key in seen:  # тот же объект с другой точкой на карте (узел и контур здания)
            result.skipped += 1
            continue
        seen[key] = School.objects.create(external_id=ext, is_approved=True, **fields)
        result.created += 1
    return result


# ---------- OpenStreetMap ----------

def _overpass(query: str, timeout: int = 320) -> dict:
    data = urllib.parse.urlencode({'data': query}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — фиксированный https-адрес
        return json.load(resp)


def _region_relations() -> dict[str, int]:
    q = ('[out:json][timeout:120];area["ISO3166-1"="KZ"][admin_level=2]->.kz;'
         'rel(area.kz)[boundary=administrative][admin_level=4];out tags;')
    return {e['tags'].get('ISO3166-2'): e['id'] for e in _overpass(q)['elements'] if e['tags'].get('ISO3166-2')}


def osm_records(log=print, pause: float = 5.0) -> list[dict]:
    """Скачивает по каждому региону именованные amenity=school и населённые пункты (≈40 запросов к Overpass)."""
    region_names = dict(Region.objects.values_list('code', 'name_ru'))
    city_regions = set(Region.objects.filter(is_city=True).values_list('code', flat=True))
    records = []
    for code, rel_id in _region_relations().items():
        if code not in region_names:
            continue
        area = 3600000000 + rel_id
        try:
            schools = _overpass_retry(SCHOOLS_QUERY.format(area=area), log)
            places = [] if code in city_regions else _overpass_retry(PLACES_QUERY.format(area=area), log)
        except RuntimeError:
            log(f'  {code}: пропущен')
            continue
        batch = build_records(code, schools, places, region_names[code] if code in city_regions else None)
        records += batch
        log(f'  {code} {region_names[code]}: {len(batch)}')
        time.sleep(pause)
    return records


def _overpass_retry(query: str, log) -> list[dict]:
    for attempt in range(3):
        try:
            return _overpass(query)['elements']
        except Exception as exc:  # noqa: BLE001 — сеть/таймаут Overpass, пробуем ещё раз
            log(f'  попытка {attempt + 1} не удалась ({exc})')
            time.sleep(20)
    raise RuntimeError('Overpass недоступен')
