from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from oauth2_provider.settings import oauth2_settings


def validate_resource_uri(value):
    from oauth2_provider.oauth2_validators import is_valid_resource_uri

    try:
        is_valid = is_valid_resource_uri(value) and urlsplit(value).scheme.lower() == "https"
    except (TypeError, ValueError):
        is_valid = False
    if not is_valid:
        raise ValidationError(
            _("Enter a valid HTTPS resource URI without user information or a fragment."),
            code="invalid_resource_uri",
        )


class OAuthClientPolicy(models.Model):
    application = models.OneToOneField(
        oauth2_settings.APPLICATION_MODEL,
        on_delete=models.CASCADE,
        related_name="client_policy",
    )
    default_scopes = models.JSONField(
        blank=True,
        null=True,
        default=None,
        help_text=_("Scopes used when the client omits scope. Empty means use global defaults."),
    )

    class Meta:
        verbose_name = _("OAuth client defaults")
        verbose_name_plural = _("OAuth client defaults")

    def __str__(self):
        return _("Defaults for %(client)s") % {"client": self.application.client_id}

    def clean(self):
        super().clean()
        if self.default_scopes is not None and not isinstance(self.default_scopes, list):
            raise ValidationError({"default_scopes": _("Select a list of scopes.")})


class OAuthResourcePolicy(models.Model):
    application = models.ForeignKey(
        oauth2_settings.APPLICATION_MODEL,
        on_delete=models.CASCADE,
        related_name="resource_policies",
    )
    resource_uri = models.URLField(
        max_length=500,
        validators=[validate_resource_uri],
        help_text=_("Canonical HTTPS URI used as this resource's audience."),
    )
    scopes = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Scopes this client may request for this resource."),
    )
    is_default = models.BooleanField(
        default=False,
        help_text=_("Use this audience when the client does not send a resource parameter."),
    )

    class Meta:
        ordering = ("application__client_id", "resource_uri")
        verbose_name = _("OAuth resource policy")
        verbose_name_plural = _("OAuth resource policies")
        constraints = [
            models.UniqueConstraint(
                fields=("application", "resource_uri"),
                name="oauth_resource_policy_unique_resource",
            ),
            models.UniqueConstraint(
                fields=("application",),
                condition=Q(is_default=True),
                name="oauth_resource_policy_one_default",
            ),
        ]

    def __str__(self):
        return f"{self.application.client_id}: {self.resource_uri}"

    def clean(self):
        super().clean()
        if not isinstance(self.scopes, list):
            raise ValidationError({"scopes": _("Select a list of scopes.")})