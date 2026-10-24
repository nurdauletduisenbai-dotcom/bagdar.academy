"""
/sitemap.xml для поисковиков: публичные страницы SPA (главная, лента новостей) и опубликованные посты.
Ссылки строятся от FRONTEND_URL — сайт и API живут на одном домене, но страницы рендерит фронтенд.
"""
from urllib.parse import quote
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from .models import Post


def _url(loc: str, lastmod=None, changefreq: str | None = None, priority: str | None = None) -> str:
    parts = [f'<loc>{escape(loc)}</loc>']
    if lastmod:
        parts.append(f'<lastmod>{lastmod.date().isoformat()}</lastmod>')
    if changefreq:
        parts.append(f'<changefreq>{changefreq}</changefreq>')
    if priority:
        parts.append(f'<priority>{priority}</priority>')
    return f'<url>{"".join(parts)}</url>'


@require_GET
@cache_control(public=True, max_age=3600)
def sitemap_xml(request):
    base = settings.FRONTEND_URL
    posts = list(Post.objects.published().order_by('-published_at').only('slug', 'published_at', 'updated_at'))
    latest = max((p.updated_at for p in posts), default=None)

    urls = [
        _url(f'{base}/', latest, 'daily', '1.0'),
        _url(f'{base}/news', latest, 'daily', '0.8'),
        # Unicode-slug кодируем по RFC 3986 — так требует протокол sitemaps
        *(_url(f'{base}/news/{quote(p.slug)}', max(p.updated_at, p.published_at), 'monthly', '0.6') for p in posts),
    ]
    body = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + '\n'.join(urls) + '\n</urlset>\n')
    return HttpResponse(body, content_type='application/xml; charset=utf-8')
