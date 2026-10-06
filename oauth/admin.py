from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _
from oauth2_provider.admin import ApplicationAdmin

from .forms import OAuthClientPolicyForm, OAuthResourcePolicyForm
from .models import OAuthClientPolicy, OAuthResourcePolicy


class OAuthClientPolicyInline(admin.StackedInline):
    model = OAuthClientPolicy
    form = OAuthClientPolicyForm
    extra = 0
    max_num = 1
    can_delete = False
    verbose_name = _("Client default scopes")
    verbose_name_plural = _("Client default scopes")


class BaseOAuthResourcePolicyInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        active_forms = [
            form
            for form in self.forms
            if hasattr(form, "cleaned_data")
            and form.cleaned_data
            and not form.cleaned_data.get("DELETE", False)
        ]
        resources = [form.cleaned_data["resource_uri"] for form in active_forms]
        defaults = [form for form in active_forms if form.cleaned_data.get("is_default", False)]

        if len(resources) != len(set(resources)):
            raise ValidationError(_("A resource URI can only be listed once for this OAuth client."))
        if len(defaults) > 1:
            raise ValidationError(_("Select at most one default audience for this OAuth client."))


class OAuthResourcePolicyInline(admin.TabularInline):
    model = OAuthResourcePolicy
    form = OAuthResourcePolicyForm
    formset = BaseOAuthResourcePolicyInlineFormSet
    extra = 0
    fields = ("resource_uri", "scopes", "is_default")
    verbose_name = _("Allowed API resource")
    verbose_name_plural = _("Allowed API resources and scopes")


class OAuthApplicationAdmin(ApplicationAdmin):
    inlines = (OAuthClientPolicyInline, OAuthResourcePolicyInline)
