# coding: utf-8
from django.apps.config import AppConfig
from django.utils.translation import gettext_noop

gettext_noop("Approval")


class ApprovalConfig(AppConfig):

    name = 'approval'
    label = 'approval'

    def ready(self):
        from django.conf import settings
        # You can disable automatic approval handling by disabling signals.
        if not getattr(settings, 'APPROVAL_DISABLE_SIGNALS', False):
            from approval import listeners


# Charger la configuration ci-dessus par défaut
default_app_config = 'approval.ApprovalConfig'
