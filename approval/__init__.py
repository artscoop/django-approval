# coding: utf-8
from django.apps.config import AppConfig
from django.utils.translation import gettext_noop
import logging

gettext_noop("Approval")
logger = logging.getLogger("approval")


class ApprovalConfig(AppConfig):

    name = "approval"
    label = "approval"

    def ready(self):
        from django.conf import settings

        # You can disable automatic approval handling by disabling signals.
        if not getattr(settings, "APPROVAL_DISABLE_SIGNALS", False):
            from approval import listeners

            logger.debug("Approval signals are enabled.")
        else:
            logger.warn("Approval signals are disabled.")


# Charger la configuration ci-dessus par défaut
default_app_config = "approval.ApprovalConfig"
