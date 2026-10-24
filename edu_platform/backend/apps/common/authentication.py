from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

from .tenancy import resolve_org_id


class TenantJWTAuthentication(JWTAuthentication):
    """
    JWT-аутентификация + определение текущей организации (request.org_id).

    Middleware не видит JWT-пользователя (DRF аутентифицирует позже, во view),
    поэтому организация проверяется здесь: заголовок X-Org-ID важнее org_id из токена,
    и пользователь обязан состоять в выбранной организации.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, token = result
        header_org = getattr(request._request, 'org_id', None)
        if header_org:
            # Явно выбранная организация: нет членства — 403
            request._request.org_id = resolve_org_id(user, header_org)
            return user, token
        try:
            request._request.org_id = resolve_org_id(user, token.get('org_id'))
        except PermissionDenied:
            # Организация в токене устарела (ученик сменил школу, его отключили) — выбираем заново, без ошибки
            request._request.org_id = resolve_org_id(user, None)
        return user, token


class TenantJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """Описание схемы Bearer JWT для Swagger (кнопка Authorize)."""

    target_class = 'apps.common.authentication.TenantJWTAuthentication'
    name = 'jwtAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': 'Access-токен из POST /api/v1/auth/login/ (поле access_token).',
        }
