import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.schools.importing import import_records, osm_records, read_file
from apps.schools.models import School

BUNDLED = Path(__file__).resolve().parents[2] / 'data' / 'kz_schools_osm.json'


class Command(BaseCommand):
    help = ('Загрузить справочник школ Казахстана. Без аргументов — встроенный снимок OpenStreetMap; '
            'путь к JSON/CSV — свой список (например, реестр от управления образования); '
            '--osm — скачать свежие данные из OpenStreetMap.')

    def add_arguments(self, parser):
        parser.add_argument('path', nargs='?', help='JSON или CSV: external_id,name,name_kk,name_ru,region_code,locality,kind')
        parser.add_argument('--osm', action='store_true', help='Скачать из OpenStreetMap (Overpass API)')
        parser.add_argument('--dump', help='С --osm: сохранить скачанное в файл, ничего не импортируя')
        parser.add_argument('--if-empty', action='store_true',
                            help='Только если справочник пуст (для деплоя: не трогать правки администратора)')

    def handle(self, *args, path=None, osm=False, dump=None, if_empty=False, **options):
        if if_empty and School.objects.exists():
            self.stdout.write('Справочник школ уже заполнен — пропускаем.')
            return
        if osm:
            self.stdout.write('Скачиваем школы из OpenStreetMap по регионам…')
            records = osm_records(log=self.stdout.write)
            if dump:
                Path(dump).write_text(json.dumps(records, ensure_ascii=False, indent=0), encoding='utf-8')
                self.stdout.write(self.style.SUCCESS(f'Сохранено {len(records)} записей в {dump}'))
                return
            source = School.Source.OSM
        else:
            file = path or str(BUNDLED)
            if not Path(file).exists():
                raise CommandError(f'Файл не найден: {file}')
            records = read_file(file)
            source = School.Source.OSM if file == str(BUNDLED) else School.Source.IMPORT

        result = import_records(records, source=source)
        self.stdout.write(self.style.SUCCESS(
            f'Школ добавлено: {result.created}, обновлено: {result.updated}, пропущено: {result.skipped}. '
            f'Всего в справочнике: {School.objects.count()}.'))
