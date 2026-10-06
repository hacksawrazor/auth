from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from oauthlib.oauth2.rfc6749 import errors
from oauth2_provider.models import Grant
from oauth2_provider.oauth2_validators import OAuth2Validator


class UserClaimsValidator(OAuth2Validator):
    @staticmethod
    def _request_resources(request):
        resource = getattr(request, "resource", None)
        body = getattr(request, "decoded_body", None) or []
        repeated_resources = [value for key, value in body if key == "resource"]
        if len(repeated_resources) > 1:
            resource = repeated_resources

        if isinstance(resource, str):
            return [resource] if resource.strip() else []
        if isinstance(resource, (list, tuple)):
            return list(resource)
        return []

    def _set_inherited_resource(self, request, code=None):
        resources = self._request_resources(request)
        if resources:
            request.resource = resources
            return resources

        if code is not None:
            grant = Grant.objects.filter(code=code, application=request.client).first()
            resources = list(grant.resource or []) if grant else []
        elif getattr(request, "grant_type", None) == "refresh_token":
            refresh_token = getattr(request, "refresh_token_instance", None)
            resources = list(refresh_token.resource or []) if refresh_token else []
        else:
            client_defaults = settings.OAUTH2_CLIENT_DEFAULTS.get(request.client.client_id, {})
            resources = list(client_defaults.get("resources", []))

        request.resource = resources
        return resources

    def validate_scopes(self, client_id, scopes, client, request, *args, **kwargs):
        if not super().validate_scopes(client_id, scopes, client, request, *args, **kwargs):
            return False

        resources = self._set_inherited_resource(request, getattr(request, "code", None))
        api_scopes = set(settings.OAUTH2_API_SCOPES)
        requested_api_scopes = set(scopes).intersection(api_scopes)

        if not resources:
            return not requested_api_scopes

        client_policies = settings.OAUTH2_RESOURCE_POLICIES.get(client_id, {})
        if not isinstance(client_policies, dict) or any(resource not in client_policies for resource in resources):
            return False

        allowed_scopes = [set(client_policies[resource]) for resource in resources]
        permitted_scopes = set.intersection(*allowed_scopes) if allowed_scopes else set()
        return requested_api_scopes.issubset(permitted_scopes)

    def validate_code(self, client_id, code, client, request, *args, **kwargs):
        valid = super().validate_code(client_id, code, client, request, *args, **kwargs)
        if valid and not self._request_resources(request):
            grant = Grant.objects.get(code=code, application=client)
            request.resource = list(grant.resource or [])
        return valid

    def validate_refresh_token(self, refresh_token, client, request, *args, **kwargs):
        valid = super().validate_refresh_token(refresh_token, client, request, *args, **kwargs)
        if valid:
            self._set_inherited_resource(request)
        return valid

    def get_default_scopes(self, client_id, request, *args, **kwargs):
        client_defaults = settings.OAUTH2_CLIENT_DEFAULTS.get(client_id, {})
        self._set_inherited_resource(request)
        if "scopes" in client_defaults:
            return list(client_defaults["scopes"])
        return list(settings.OAUTH2_DEFAULT_SCOPES)

    def finalize_id_token(self, id_token, token, token_handler, request):
        try:
            request.client.jwk_key
        except ImproperlyConfigured as exc:
            raise errors.InvalidClientError(
                description=f'OAuth client signing configuration is invalid: {exc}'
            ) from exc
        return super().finalize_id_token(id_token, token, token_handler, request)

    def get_additional_claims(self, request):
        user = request.user
        return {
            'email': user.email,
            'email_verified': bool(user.email),
        }