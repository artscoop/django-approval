from django.apps.config import AppConfig
from django.utils.translation import pgettext_lazy


class ApprovalConfig(AppConfig):
    """AppConfig for Approval application."""
    name = "approval"
    label = "approval"
    verbose_name = pgettext_lazy("approval", "approval")
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Initialize application when Django is ready."""
        from django.conf import settings
        from . import settings as default
        # You can disable automatic approval handling by disabling signals.
        if not getattr(settings, "APPROVAL_DISABLE_SIGNALS", default.APPROVAL_DISABLE_SIGNALS):
            from . import listeners  # noqa
