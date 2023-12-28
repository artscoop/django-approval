from __future__ import annotations

from typing import Self
from uuid import UUID

from django.db import models


class EntrySet(models.QuerySet):
    """Content entry manager class."""

    def visible(self) -> Self:
        return self.filter(is_visible=True)

    def by_uuid(self, uuid: str | UUID) -> models.Model:
        return self.get(uuid=uuid)
