from django.conf import settings
from django.core import checks
from django.db import OperationalError, ProgrammingError
from oauth2_provider.models import AbstractApplication, Application


@checks.register(checks.Tags.models)
def check_oauth_signing_configuration(app_configs, **kwargs):
    issues = []
    try:
        applications = Application.objects.all()
        for application in applications:
            if application.algorithm == AbstractApplication.NO_ALGORITHM:
                # OAuth clients used only for APIs such as introspection do not
                # issue OIDC ID tokens and need no signing algorithm.
                continue

            if application.algorithm not in {
                AbstractApplication.RS256_ALGORITHM,
                AbstractApplication.HS256_ALGORITHM,
            }:
                issues.append(checks.Error(
                    f'OAuth application "{application.name}" ({application.client_id}) '
                    f'has unsupported signing algorithm {application.algorithm!r}.',
                    hint='Set the application algorithm to RS256 for OIDC clients.',
                    id='oauth.E001',
                ))
            elif (
                application.algorithm == AbstractApplication.RS256_ALGORITHM
                and not settings.OAUTH2_PROVIDER.get('OIDC_RSA_PRIVATE_KEY')
            ):
                issues.append(checks.Error(
                    f'OAuth application "{application.name}" ({application.client_id}) '
                    'uses RS256 but no OIDC RSA private key is configured.',
                    hint='Set OIDC_RSA_PRIVATE_KEY or OIDC_PRIVATE_KEY_PATH.',
                    id='oauth.E002',
                ))
    except (OperationalError, ProgrammingError):
        # The database may not exist yet during image builds or first migration.
        return issues
    return issues