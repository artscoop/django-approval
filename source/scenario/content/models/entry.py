from typing import Iterable
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils.translation import pgettext_lazy

from approval.models import MonitoredModel, Sandbox, SandboxMeta
from ..querysets import EntrySet


class Entry(MonitoredModel):
    """Content entry."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="entries")
    uuid = models.UUIDField(default=uuid4, verbose_name="UUID")
    is_visible = models.BooleanField(default=True, verbose_name="visible")
    created = models.DateTimeField(auto_now_add=True, verbose_name="created date")
    description = models.TextField(blank=True, verbose_name="description")
    content = models.TextField(blank=False, verbose_name="content")
    objects = EntrySet.as_manager()

    class Meta:
        verbose_name = pgettext_lazy("content", "entry")
        verbose_name_plural = pgettext_lazy("content", "entries")
        indexes = [models.Index(fields=["created"], name="idx_created")]

    def __str__(self):
        return f"Entry {self.uuid}"


class EntryApproval(Sandbox, metaclass=SandboxMeta):
    """Entry moderation model."""
    base = Entry
    approval_fields = ["description", "content"]
    approval_store_fields = ["is_visible"]
    approval_default = {"is_visible": False, "description": ""}
    auto_approve_staff = False
    auto_approve_new = False
    auto_approve_by_request = False

    def _get_authors(self) -> Iterable:
        return [self.source.user]

