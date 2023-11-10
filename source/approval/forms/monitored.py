"""Form mixins for approvable models."""
from django.utils.translation import pgettext_lazy

from ..models import MonitoredModel
import logging

logger = logging.getLogger("approval")


class MonitoredForm:
    """ModelForm mixin for monitored models."""

    def __init__(self, *args, **kwargs):
        """
        Form initializer for ApprovedModel.

        The form is initialized with the instance data fetched from the sandbox,
        so you can start editing the object from your last attempt.
        """
        instance = kwargs.get("instance", None)
        if instance and isinstance(instance, MonitoredModel):
            instance.approval._update_source()
            logger.debug(pgettext_lazy("approval", f"{self.__class__.__name__} fetched approval data for form."))
        super().__init__(*args, **kwargs)
