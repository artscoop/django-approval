# coding: utf-8
from django.apps.config import AppConfig
from django.utils.translation import gettext_noop

__version__ = (1, 2016, 1)

gettext_noop("Approval")


class ApprovalConfig(AppConfig):
    """ Configuration de l'application Dating """
    name = 'approval'
    label = 'approval'

    def ready(self):
        """ Le registre des applications est prêt """
        from approval import listeners

# Charger la configuration ci-dessus par défaut
default_app_config = 'approval.ApprovalConfig'
