from django.db import migrations

from apps.schools.regions import REGIONS


def add_regions(apps, schema_editor):
    Region = apps.get_model('schools', 'Region')
    for order, (code, name_ru, name_kk, is_city) in enumerate(REGIONS):
        Region.objects.update_or_create(code=code, defaults={
            'name_ru': name_ru, 'name_kk': name_kk, 'is_city': is_city, 'order': order})


class Migration(migrations.Migration):
    dependencies = [('schools', '0001_initial')]

    operations = [migrations.RunPython(add_regions, migrations.RunPython.noop)]
