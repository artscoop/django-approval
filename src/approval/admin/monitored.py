from django.contrib import messages
from django.contrib.admin import display
from django.contrib.admin.options import ModelAdmin
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import pgettext_lazy

from ..models import MonitoredModel


class MonitoredAdmin(ModelAdmin):
    """
    ModelAdmin mixin for approval-controlled objects.

    This class should not be registered into the admin.
    Instead, developers should create a `ModelAdmin` class derived from this
    class.
    """

    def get_object(self, request, object_id, from_field: str = None) -> MonitoredModel:
        """Return the desired object, augmented with a request attribute."""
        obj: MonitoredModel = super().get_object(request, object_id)
        if isinstance(obj, MonitoredModel):
            # Only display approval warning if the object has not been approved.
            if getattr(obj, "approval", None) and obj.approval.approved is None:
                obj.approval._update_source(default=False, save=False)
                obj.request = request
                if obj.approval.approved is None:
                    self.message_user(
                        request,
                        pgettext_lazy(
                            "approval", "This form is showing changes currently pending."
                        ),
                        level=messages.WARNING,
                    )
            return obj
        else:
            raise ImproperlyConfigured(f"No approval model was declared for this model.")

    @display(description=pgettext_lazy("approval", "status"), ordering="approval__approved")
    def get_approval_status(self, obj):
        if isinstance(obj, MonitoredModel) and hasattr(obj, "approval") and obj.approval:
            return obj.approval.get_approved_display()
        return pgettext_lazy("approval", "Unavailable")
