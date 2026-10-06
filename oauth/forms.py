from django import forms
from django.conf import settings

from .models import OAuthClientPolicy, OAuthResourcePolicy


def configured_scope_choices():
    return sorted(settings.OAUTH2_PROVIDER["SCOPES"].items())


def api_scope_choices():
    return sorted(
        (scope, settings.OAUTH2_PROVIDER["SCOPES"][scope])
        for scope in settings.OAUTH2_API_SCOPES
        if scope in settings.OAUTH2_PROVIDER["SCOPES"]
    )


class OAuthClientPolicyForm(forms.ModelForm):
    default_scopes = forms.MultipleChoiceField(
        required=False,
        choices=(),
        widget=forms.SelectMultiple(attrs={"size": 8}),
        help_text="Used when the client omits scope. Leave empty to use global defaults.",
    )

    class Meta:
        model = OAuthClientPolicy
        fields = ("default_scopes",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["default_scopes"].choices = configured_scope_choices()
        if self.instance and self.instance.pk:
            self.initial["default_scopes"] = self.instance.default_scopes or []

    def clean_default_scopes(self):
        selected = self.cleaned_data["default_scopes"]
        return selected or None


class OAuthResourcePolicyForm(forms.ModelForm):
    scopes = forms.MultipleChoiceField(
        required=False,
        choices=(),
        widget=forms.SelectMultiple(attrs={"size": 8}),
        help_text="Permissions this OAuth client may request for the selected audience.",
    )

    class Meta:
        model = OAuthResourcePolicy
        fields = ("resource_uri", "scopes", "is_default")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["scopes"].choices = api_scope_choices()
        if self.instance and self.instance.pk:
            self.initial["scopes"] = self.instance.scopes