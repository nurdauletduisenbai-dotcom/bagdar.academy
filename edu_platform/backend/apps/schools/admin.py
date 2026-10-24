from django.contrib import admin, messages
from django.db.models import Count

from .models import Region, School
from .services import ensure_organization, move_students


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_kk', 'code', 'is_city', 'order', 'schools_count')
    list_editable = ('order',)
    search_fields = ('name_ru', 'name_kk', 'code')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_schools=Count('schools'))

    @admin.display(description='Школ', ordering='_schools')
    def schools_count(self, obj):
        return obj._schools


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'locality', 'region', 'is_approved', 'is_active', 'source', 'organization',
                    'students_count')
    list_filter = ('is_approved', 'is_active', 'kind', 'source', 'region')
    list_editable = ('is_approved', 'is_active')
    search_fields = ('name', 'name_kk', 'name_ru', 'locality')
    list_select_related = ('region', 'organization')
    autocomplete_fields = ('organization',)
    readonly_fields = ('source', 'external_id', 'created_by', 'created_at', 'updated_at')
    fields = ('name', 'name_kk', 'name_ru', 'kind', 'region', 'locality', 'organization',
              'is_approved', 'is_active', 'source', 'external_id', 'created_by', 'created_at', 'updated_at')
    actions = ('approve', 'hide', 'show', 'merge_into_first')
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_students=Count('students'))

    @admin.display(description='Учеников', ordering='_students')
    def students_count(self, obj):
        return obj._students

    def save_model(self, request, obj, form, change):
        if not change:
            obj.source = School.Source.ADMIN
            obj.created_by = request.user
        old_org_id = form.initial.get('organization') if change else None
        super().save_model(request, obj, form, change)
        # Школу связали с другой организацией — её ученики переходят туда же
        if change and 'organization' in form.changed_data and obj.organization:
            moved = move_students(obj, old_org_id, obj.organization)
            if moved:
                self.message_user(request, f'Учеников переведено в «{obj.organization.name}»: {moved}.')

    @admin.action(description='Одобрить (показывать в поиске)')
    def approve(self, request, queryset):
        n = queryset.update(is_approved=True, is_active=True)
        self.message_user(request, f'Одобрено: {n}.')

    @admin.action(description='Скрыть из поиска')
    def hide(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(request, f'Скрыто: {n}. Ученики, выбравшие эти школы, их сохраняют.')

    @admin.action(description='Снова показывать')
    def show(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f'Показывается: {n}.')

    @admin.action(description='Объединить дубли в первую выбранную (по ID)')
    def merge_into_first(self, request, queryset):
        schools = list(queryset.order_by('id'))
        if len(schools) < 2:
            self.message_user(request, 'Выберите минимум две школы.', messages.WARNING)
            return
        main, dupes = schools[0], schools[1:]
        from apps.accounts.models import User
        from apps.organizations.models import OrgMembership

        # Ученики дублей — в организацию основной школы; опустевшие авто-организации дублей отключаются
        main_org = ensure_organization(main) if any(d.students.exists() for d in dupes) else main.organization
        for d in dupes:
            move_students(d, d.organization_id, main_org)
            if d.organization and not OrgMembership.objects.filter(org=d.organization, is_active=True).exists():
                d.organization.is_active = False
                d.organization.save(update_fields=['is_active', 'updated_at'])
        moved = User.all_objects.filter(school__in=dupes).update(school=main)
        School.objects.filter(id__in=[d.id for d in dupes]).update(is_active=False, is_approved=False)
        self.message_user(request, f'Объединено в «{main.name}»: учеников перенесено {moved}, дублей скрыто {len(dupes)}.')
