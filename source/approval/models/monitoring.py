import logging
from typing import Type, Optional, Iterable, Any
from uuid import uuid4

from annoying.fields import AutoOneToOneField
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.base import ModelBase
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from approval.models import MonitoredModel
from approval.signals import pre_approval, post_approval

logger = logging.getLogger("approval")


class SandboxMeta(ModelBase):
    """Metaclass to create a dynamic sandbox model."""

    def __new__(cls, name: str, bases: tuple, attrs: dict, **kwargs) -> Type:
        # Names
        source_model: Type[models.Model] = attrs.get("base", None)
        source_name: str = f"{source_model._meta.model_name}"
        source_app: str = f"{source_model._meta.app_label}"
        source_fqmn: str = f"{source_model._meta.app_label}.{source_model._meta.model_name}"
        reverse_name: str = f"moderated_{source_model._meta.model_name.lower()}_approval"
        table_name: str = f"{source_model._meta.db_table}_approval"
        source_verbose_name: str = source_model._meta.verbose_name
        permission_names: dict = {"moderate": f"moderate_{table_name}"}

        # Dynamic class replacing the original class.
        class DynamicSandbox(models.Model):
            """
            Base class model to monitor changes on a source Model.

            Notes:
                To define a model holding changes detected on a source model,
                the developer must declare a model class inheriting from
                `Approval`. For it to function properly, the developer must
                provide some configuration in the form of 5 attributes.
            """

            MODERATION_STATUS: tuple = (
                (None, pgettext_lazy("approval.moderation", "Pending")),
                (False, pgettext_lazy("approval.moderation", "Rejected")),
                (True, pgettext_lazy("approval.moderation", "Approved")),
            )
            DRAFT_STATUS: tuple = (
                (False, pgettext_lazy("approval.draft", "Draft")),
                (True, pgettext_lazy("approval.draft", "Waiting for moderation")),
            )

            base: Type[models.Model] = attrs.get("base", None)
            approval_fields: list[str] = attrs.get("approval_fields", [])
            approval_store_fields: list[str] = attrs.get("approval_store_fields", [])
            approval_default: dict[str, object] = attrs.get("approval_default", {})
            auto_approve_staff: bool = attrs.get("auto_approve_staff", True)
            auto_approve_new: bool = attrs.get("auto_approve_new", False)
            auto_approve_by_request: bool = attrs.get("auto_approve_by_request", True)

            uuid = models.UUIDField(default=uuid4, verbose_name=_("UUID"))
            source = AutoOneToOneField(
                source_fqmn, null=False, on_delete=models.CASCADE, related_name="approval"
            )
            sandbox = models.JSONField(
                default=dict,
                blank=False,
                encoder=DjangoJSONEncoder,
                verbose_name=pgettext_lazy("approval_entry", "Data"),
            )
            approved = models.BooleanField(
                default=None,
                null=True,
                choices=MODERATION_STATUS,
                verbose_name=pgettext_lazy("approval_entry", "Moderated"),
            )
            moderator = models.ForeignKey(
                settings.AUTH_USER_MODEL,
                default=None,
                blank=True,
                null=True,
                related_name=reverse_name,
                verbose_name=pgettext_lazy("approval_entry", "Moderated by"),
                on_delete=models.CASCADE,
            )
            draft = models.BooleanField(
                default=True,
                choices=DRAFT_STATUS,
                verbose_name=pgettext_lazy("approval_entry", "Draft"),
            )
            approval_date = models.DateTimeField(
                null=True, verbose_name=pgettext_lazy("approval_entry", "Moderated at")
            )
            info = models.TextField(blank=True, verbose_name=pgettext_lazy("approval", "Reason"))
            updated = models.DateTimeField(
                auto_now=True, verbose_name=pgettext_lazy("approval_entry", "Updated")
            )

            class Meta:
                abstract = False
                db_table = table_name
                app_label = source_app
                verbose_name = pgettext_lazy("approval", "{name} approval").format(
                    name=source_verbose_name
                )
                verbose_name_plural = pgettext_lazy("approval", "{name} approvals").format(
                    name=source_verbose_name
                )
                permissions = [[permission_names["moderate"], f"can moderate {source_name}"]]

            def save(self, **options):
                return super().save(**options)

            def __str__(self):
                return f"{self.source} approval status: {self.get_approved_display()}"

            def __repr__(self):
                return f"{self._meta.model_name}(uuid={self.uuid}, ...)"

            # API
            def _update_source(self, default: bool = False, save: bool = False) -> bool:
                """
                Validate pending changes and apply them to source instance.

                Keyword Args:
                    default:
                        If `True`, reset source fields with their default values, as
                        specified by the attribute `ApprovalModel.approval_default`.
                    save:
                        If `True`, the source instance is saved in the database.

                Returns:
                    `True` if source could be updated with no issue, meaning data set into
                    the fields in source is correct (correct type and values).
                    `False` if the data put into the source fields can not be validated
                    by Django.
                """
                original = dict()  # Revert to target values in case of failure
                if default is False:
                    for field in self._get_fields_data():
                        original[field] = getattr(self.source, field)
                        setattr(self.source, field, self.sandbox["fields"][field])
                    for field in self._get_store_fields_data():
                        original[field] = getattr(self.source, field)
                        setattr(self.source, field, self.sandbox["store"][field])
                    logger.debug(
                        pgettext_lazy("approval", f"Updated monitored object fields using sandbox.")
                    )
                else:
                    for field in self.approval_default.keys():
                        setattr(self.source, field, self.approval_default[field])
                    logger.debug(
                        pgettext_lazy(
                            "approval", f"Updated monitored object fields using default values."
                        )
                    )

                try:
                    self.source.clean_fields()  # use Django field validation on new values
                    if save:
                        self.source._ignore_approval = True
                        self.source.save()
                        logger.debug(
                            pgettext_lazy("approval", f"Updated monitored object was persisted.")
                        )
                    return True
                except ValidationError as exc:
                    for key in exc.message_dict:
                        logger.debug(
                            pgettext_lazy(
                                "approval", "Field {name} could not be persisted to model."
                            ).format(name=key)
                        )
                        if hasattr(self.source, key):
                            setattr(self.source, key, original[key])
                    if save:
                        self.source._ignore_approval = True
                        self.source.save()
                    return False

            def _update_sandbox(self, slot: str = None, source: MonitoredModel = None) -> None:
                """
                Copy source monitored field values into the sandbox.

                Keyword Args:
                    slot:
                        Field values can be saved in various slots of
                        the same approval instance. Slots are arbitrary names.
                        Default slot is `None`.
                    source:
                        Can be a reference of another object of the same model
                        as `self.source`, for example to use it as a template.
                """
                slot: str = slot or "fields"
                source: MonitoredModel = source or self.source
                # Save monitored fields into the defined slot.
                fields: list = self._get_field_names()
                values: dict[str, Any] = {
                    k: getattr(source, k) for k in fields if hasattr(source, k)
                }
                self.sandbox[slot] = values
                # Save store/restore fields into the "store" slot.
                fields: list[str] = self._get_store_field_names()
                values: dict[str, Any] = {
                    k: getattr(source, k) for k in fields if hasattr(source, k)
                }
                self.sandbox["store"] = values
                # Mark the changes as Pending
                self.approved = None
                self.save()
                logger.debug(
                    pgettext_lazy("approval", "Sandbox for {source} was updated.").format(
                        source=source
                    )
                )

            def _needs_approval(self) -> bool:
                """
                Get whether the status of the object really needs an approval.

                Returns:
                    `True` if the status of the object can be auto-approved, `False` otherwise.

                In this case, the diff is `None` when the target object was updated
                but none of the monitored fields was changed.
                """
                return self._get_diff() is not None

            @cached_property
            def _get_valid_fields(self) -> Optional[set[str]]:
                """
                Return the names of the data fields that can be used to update the source.

                Returns:
                    A list of field names that are relevant to the source (useful
                    when the original model changed after a migration).

                Without this method, applying values from the sandbox would fail
                if a monitored field was removed from the model.
                """
                fields = set(self._get_field_names())
                source_fields = set(self.source._meta.get_all_field_names())
                return fields.intersection(source_fields) or None

            def _get_field_names(self) -> list[str]:
                """Get the list of monitored field names."""
                return self.approval_fields

            def _get_store_field_names(self) -> list[str]:
                return self.approval_store_fields

            def _get_fields_data(self) -> dict[str, Any]:
                """
                Return a dictionary of the data in the sandbox.

                Returns:
                    A dictionary with field names as keys and their sandbox value as values.
                """
                return self.sandbox.get("fields", {})

            def _get_store_fields_data(self) -> dict[str, Any]:
                """
                Return a dictionary of the data in the sandbox store.

                Returns:
                    A dictionary with field names as keys and their sandbox value as values.
                """
                return self.sandbox.get("store", {})

            def _get_diff(self) -> Optional[list[str]]:
                """
                Get the fields that have been changed from source to sandbox.

                Returns:
                    A list of monitored field names that are different in the source.
                    `None` if no difference exists between the source and the sandbox.
                """
                data = self._get_fields_data()
                source_data = {
                    field: getattr(self.source, field) for field in self._get_field_names()
                }
                return [key for key in data.keys() if data[key] != source_data[key]] or None

            def _can_user_bypass_approval(self, user: AbstractUser) -> bool:
                """
                Get whether a user can bypass approval rights control.

                Args:
                    user:
                        The user instance to check against.
                """
                permission_name: str = f"{self.base._meta.app_label}.{permission_names['moderate']}"
                return user and user.has_perm(perm=permission_name)

            def _auto_process_approval(
                self, authors: Iterable = None, update: bool = False
            ) -> None:
                """
                Approve or deny edits automatically.

                This method denies or approves according to configuration of
                "auto_approve_..." fields.

                Args:
                    authors:
                        The list of users responsible for the change. If the instance
                        contains a `request` attribute, the connected user is considered the
                        author of the change.
                    update:
                        Is used to differentiate between new objects and updated ones.
                        Is set to `False` when the object is new, `True` otherwise.
                """
                authorized: bool = any(self._can_user_bypass_approval(author) for author in authors)
                optional: bool = not self._needs_approval()

                if authorized or optional or (self.auto_approve_new and not update):
                    self.approve(user=authors[0], save=True)
                if self.auto_approve_staff and any((u.is_staff for u in authors)):
                    self.approve(user=authors[0], save=True)
                self.auto_process_approval(authors=authors)

            def _get_authors(self) -> Iterable:
                """
                Get the authors of the source instance.

                Warnings:
                    This method *must* be overriden in the concrete model.
                """
                raise NotImplemented("You must define _get_authors() in your model.")

            def submit_approval(self) -> bool:
                """
                Sets the status of the object to Waiting for moderation.

                In other words, the monitored object will get moderated only
                after it's pulled from draft.
                """
                if self.draft:
                    self.draft = False
                    self.save()
                    logger.debug(
                        pgettext_lazy("approval", f"Set sandbox as waiting for moderation.")
                    )
                    return True
                return False

            def is_draft(self) -> bool:
                """Check whether the object is currently in draft mode."""
                return self.draft

            def approve(self, user=None, save: bool = False) -> None:
                """
                Approve pending edits.

                Args:
                    user:
                        Instance of user who moderated the content.
                    save:
                        If `True`, persist changes to the monitored object.
                        If `False`, apply sandbox to the monitored object, but don't save it.
                """
                pre_approval.send(self.base, instance=self.source, status=self.approved)
                self.approval_date = timezone.now()
                self.approved = True
                self.moderator = user
                self.draft = False
                self.info = pgettext_lazy(
                    "approval_entry", "Congratulations, your edits have been approved."
                )
                self._update_source(save=True)  # apply changes to monitored object
                if save:
                    super().save()
                post_approval.send(self.base, instance=self.source, status=self.approved)
                logger.debug(pgettext_lazy("approval", f"Changes in sandbox were approved."))

            def deny(self, user=None, reason: str = None, save: bool = False) -> None:
                """
                Reject pending edits.

                Args:
                    user:
                        Instance of user who moderated the content.
                    reason:
                        String explaining why the content was refused.
                    save:
                        If `True`, persist changes to the monitored object.
                        If `False`, apply sandbox to the monitored object, but don't save it.
                """
                pre_approval.send(self.base, instance=self.source, status=self.approved)
                self.moderator = user
                self.approved = False
                self.draft = False
                self.info = reason or pgettext_lazy(
                    "approval_entry", "Your edits have been refused."
                )
                if save:
                    self.save()
                post_approval.send(self.base, instance=self.source, status=self.approved)
                logger.debug(pgettext_lazy("approval", f"Changes in sandbox were rejected."))

            def auto_process_approval(self, authors: Iterable = None) -> None:
                """
                User-defined auto-processing, the developer should override this.

                Auto-processing is the choice of action regarding the author
                or the state of the changes. This method can choose to auto-approve
                for some users or auto-deny changes from inappropriate IPs.

                """
                return None

        return DynamicSandbox


class Sandbox:
    """
    Class providing attributes to configure a Sandbox model.

    To use this class, you need to create a model class that inherits from
    this class, and use `SandboxBase` as a metaclass:

    ```python
    class EntryApproval(SandboxModel, metaclass=SandboxBase):
        base = Entry
        approval_fields = ["description", "content"]
        approval_store_fields = ["is_visible"]
        approval_default = {"is_visible": False, "description": ""}
        auto_approve_staff = False
        auto_approve_new = False
        auto_approve_by_request = False

        def _get_authors(self) -> Iterable:
            return [self.source.user]
    ```

    Attributes:
        base:
            Monitored model class.
        approval_fields (list[str]):
            List of model field names on the base model that should
            be monitored and should trigger the approval process.
        approval_default:
            When a new object is created and immediately needs approval,
            define the default values for the source while waiting for
            approval. For example, for a blog entry, you can set the default `published`
            attribute to `False`.
        approval_store_fields:
            List of model field names that should be stored in the approval
            state, even though the field is not monitored. Those fields will
            be restored to the object when approved. Generally contains
            fields used in approval_default.
        auto_approve_staff:
            If `True`, changes made by a staff member should be applied
            immediately, bypassing moderation.
        auto_approve_new:
            If `True`, a new object created would bypass the approval
            phase and be immediately persisted.
        auto_approve_by_request:
            If `True` the user in the object's request attribute, if any,
            is used to test if the object can be automatically approved.
            If `False`, use the default object author only.
    """

    base: Type[models.Model] = None
    approval_fields: list[str] = []
    approval_store_fields: list[str] = []
    approval_default: dict[str, object] = {}
    auto_approve_staff: bool = True
    auto_approve_new: bool = False
    auto_approve_by_request: bool = True
