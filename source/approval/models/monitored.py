from typing import List

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
import logging

from django.utils.translation import pgettext_lazy


logger = logging.getLogger("approval")


class MonitoredModel(models.Model):
    """
    Moderated table mixin.

    If you want to mark a model to make it subject to a moderation stage,
    you must make it inherit from ``MonitoredModel``. No need to make it
    also inherit from ``django.db.models.Model``, since it's already
    a parent class of the mixin.

    .. code-block:: python
        :linenos:

        from approval.models import MonitoredModel
        from django.db import models

        class Post(MonitoredModel):  # Inherit from MonitoredModel
            # Add your own fields. Having a visibility field is a good idea.
            user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="entries")
            is_visible = models.BooleanField(default=True, verbose_name="visible")
            content = models.TextField(blank=False, verbose_name="content")

    Inheriting from ``MonitoredModel`` allows provided ``pre-save`` and ``post-save`` signal
    hooks to automatically manage your model.
    """

    class Meta:
        abstract = True

    def _get_authors(self) -> List[models.Model]:
        """Get the authors of the current instance."""
        # Use user from request as author only if allowed
        if self.approval.auto_approve_by_request:
            if getattr(self, "request") and getattr(self.request, "user", None):
                logger.debug(pgettext_lazy("approval", f"Using request user as author of {self}."))
                return [self.request.user]
        return self.approval._get_authors()

    def _revert(self) -> bool:
        """
        Revert the instance to its last saved state.

        This method deletes unsaved changes on source model instance,
        by reloading what's stored in the database.

        Returns:
            `True` if revert was possible, `False` otherwise.
        """
        try:
            self.refresh_from_db()
            logger.debug(pgettext_lazy("approval", "Monitored {obj} was reverted to last DB state.").format(obj=self))
            return True
        except ObjectDoesNotExist:
            return False

