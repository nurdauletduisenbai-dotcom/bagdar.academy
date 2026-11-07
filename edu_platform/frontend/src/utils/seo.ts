/**
 * Заголовок и meta-теги страницы (description, Open Graph, Twitter, canonical).
 * Значения по умолчанию лежат в index.html — их видят соцсети, которые не выполняют JS;
 * здесь мы обновляем их при переходах, чтобы поисковик с рендерингом видел теги конкретной страницы.
 */
export const SITE_NAME = 'bagdar.academy'

const OG_LOCALES: Record<string, string> = { kk: 'kk_KZ', ru: 'ru_RU' }

export interface PageMeta {
  /** Название страницы без суффикса; пусто — просто «bagdar.academy» */
  title?: string
  /** «bagdar.academy — слоган» вместо «Страница — bagdar.academy» (для главной) */
  brandFirst?: boolean
  description: string
  /** Картинка для превью (абсолютный или корневой путь); по умолчанию /og-image.png */
  image?: string
  /** Тип Open Graph: article для постов, website для остального */
  type?: 'website' | 'article'
  locale?: string
}

function absolute(url: string): string {
  return new URL(url, window.location.origin).href
}

function setMeta(attr: 'name' | 'property', key: string, content: string) {
  let el = document.head.querySelector<HTMLMetaElement>(`meta[${attr}="${key}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, key)
    document.head.appendChild(el)
  }
  el.content = content
}

function setCanonical(href: string) {
  let el = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]')
  if (!el) {
    el = document.createElement('link')
    el.rel = 'canonical'
    document.head.appendChild(el)
  }
  el.href = href
}

export function setPageMeta(meta: PageMeta) {
  const title = !meta.title ? SITE_NAME : meta.brandFirst ? `${SITE_NAME} — ${meta.title}` : `${meta.title} — ${SITE_NAME}`
  // Канонический адрес — без query и якоря (?next=…, #courses)
  const url = absolute(window.location.pathname)
  const image = absolute(meta.image ?? '/og-image.png')
  // В превью соцсетей бренд и так виден из og:site_name — у поста оставляем чистый заголовок
  const shareTitle = meta.title && !meta.brandFirst ? meta.title : title

  document.title = title
  setMeta('name', 'description', meta.description)
  setCanonical(url)

  setMeta('property', 'og:site_name', SITE_NAME)
  setMeta('property', 'og:type', meta.type ?? 'website')
  setMeta('property', 'og:title', shareTitle)
  setMeta('property', 'og:description', meta.description)
  setMeta('property', 'og:url', url)
  setMeta('property', 'og:image', image)
  if (meta.locale && OG_LOCALES[meta.locale]) {
    setMeta('property', 'og:locale', OG_LOCALES[meta.locale])
    const other = Object.entries(OG_LOCALES).find(([code]) => code !== meta.locale)
    if (other) setMeta('property', 'og:locale:alternate', other[1])
  }

  setMeta('name', 'twitter:card', 'summary_large_image')
  setMeta('name', 'twitter:title', shareTitle)
  setMeta('name', 'twitter:description', meta.description)
  setMeta('name', 'twitter:image', image)
}
