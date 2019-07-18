# coding: utf-8
"""Approval models."""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import pgettext_lazy

from approval.util.signals import post_approval, pre_approval


class ApprovalModel:
    """
    Moderation sandbox mixin.

    How to use:
    - Have your monitored model extend ApprovedModel
    - Make another model extending ApprovalModel(Monitoredmodelname)
    - Make your model admin extend ApprovalAdmin
    - Your form logic may set instance.request = request.

    """

    def __new__(cls, base: [ApprovedModel, models.Model], **extra):
        """Allows use of class call to return a class derived from Approval."""
        table_name = extra.pop("db_table", "{0}_approval".format(base._meta.db_table))
        table_app = base._meta.app_label
        table_model_name = base._meta.model_name
        name = base._meta.verbose_name
        name_plural = base._meta.verbose_name_plural
        reverse_name = "moderated_{0}_approval".format(base._meta.model_name)

        class Approval(models.Model):
            """
            Parametrized model.

            Attributes:
                approval_fields: the list of model fields on the source that should
                    trigger the approval process.
                approval_default: when an object is created and immediately needs
                    approval, define the default values for the source. For example,
                    for a blog entry, you can set the default `published` attribute
                    to `False`.

            """

            # Configuration
            approval_fields: List[str] = []
            approval_default: Dict[str, object] = {}
            auto_approve_staff: bool = True
            auto_approve_new: bool = False

            # Constants
            MODERATION = (
                (None, pgettext_lazy("approval.moderation", "Pending")),
                (False, pgettext_lazy("approval.moderation", "Refused")),
                (True, pgettext_lazy("approval.moderation", "Approved")),
            )
            DRAFT = (
                (False, pgettext_lazy("approval.draft", "Waiting for moderation")),
                (True, pgettext_lazy("approval.draft", "Draft")),
            )

            # Fields
            source = models.OneToOneField(  # type: models.Model
                base,
                null=False,
                on_delete=models.CASCADE,
                related_name="approval"
            )
            sandbox = JSONField(  # type: dict
                default=dict,
                blank=False,
                encoder=DjangoJSONEncoder,
                verbose_name=pgettext_lazy("approval_entry", "Data"),
            )
            approved = models.NullBooleanField(
                default=None,
                choices=MODERATION,
                verbose_name=pgettext_lazy("approval_entry", "Moderated"),
            )
            moderator = models.ForeignKey(
                settings.AUTH_USER_MODEL,
                default=None,
                blank=True,
                null=True,
                related_name=reverse_name,
                verbose_name=pgettext_lazy("approval_entry", "Moderated by"),
                on_delete=models.CASCADE
            )
            approval_date = models.DateTimeField(
                null=True, verbose_name=pgettext_lazy("approval_entry", "Moderated at")
            )
            info = models.TextField(
                blank=True, verbose_name=pgettext_lazy("approval", "Reason")
            )
            draft = models.BooleanField(
                default=True,
                choices=DRAFT,
                verbose_name=pgettext_lazy("approval_entry", "Draft"),
            )
            updated = models.DateTimeField(
                auto_now=True, verbose_name=pgettext_lazy("approval_entry", "Updated")
            )

            # Metadata
            class Meta:
                abstract = True
                db_table = table_name
                app_label = "approval"
                verbose_name = pgettext_lazy("approval", "{name} approval").format(
                    name=name
                )
                verbose_name_plural = pgettext_lazy(
                    "approval", "{name} approvals"
                ).format(name=name_plural)
                permissions = [
                    [f"moderate_{table_model_name}", f"Can moderate {name_plural}"]
                ]

            def save(self, **kwargs):
                return super().save(**kwargs)

            def __str__(self):
                return f"{self.source} approval status: {self.get_approved_display()}"

            # API
            def _update_source(self, default: bool = False, save: bool = False) -> bool:
                """
                Updates fields of the source to reflect the state of the moderation queue.

                Or in other words, applies pending changes to the actual object.

                Keyword Args:
                    default: If `True`, reset source fields with their default values, as
                        specified by the attribute `ApprovalModel.approval_default`.
                    save: If `True`, the source instance is saved in the database.

                """
                original = dict()  # Revert to target values in case of failure
                if default is False:
                    for field in self._get_fields_data():
                        original[field] = getattr(self.source, field)
                        setattr(self.source, field, self.sandbox["fields"][field])
                else:
                    for field in self.approval_default.keys():
                        setattr(self.source, field, self.approval_default[field])

                try:
                    self.source.clean_fields()  # will fail with ValidationError if there is a
                    # problem
                    if save:
                        self.source._ignore_approval = True
                        self.source.save()
                    return True
                except ValidationError as exc:
                    for key in exc.message_dict:
                        if hasattr(self.source, key):
                            setattr(self.source, key, original[key])
                    if save:
                        self.source._ignore_approval = True
                        self.source.save()
                    return True

            def _update_sandbox(
                self, slot: str = None, source: ApprovedModel = None
            ) -> None:
                """
                Updates fields of the sandbox to reflect the state of the source.

                Or in other words, creates a pending status identical to the one of the actual
                object.

                """
                slot = slot or "fields"
                source = source or self.source
                fields = self._get_fields()
                values = {
                    key: getattr(source, key) for key in fields if hasattr(source, key)
                }
                self.sandbox[slot] = values
                self.approved = None
                self.save()

            def submit_approval(self) -> bool:
                """
                Sets the status of the object to waiting for moderation.

                In other words, the object will moderated only after it's pulled from draft.

                """
                if self.draft is True:
                    self.draft = False
                    self.save()
                    return True
                return False

            def is_draft(self) -> bool:
                """
                Returns if the object is submitted for approval or not
                :returns: True if not submitted, False if waiting for approval
                """
                return self.draft

            def _needs_approval(self) -> bool:
                """
                Returns whether the status of the object really needs an approval.

                Returns:
                    `True` if the status of the object can be auto-approved, `False` otherwise.

                """
                if self._get_diff() is None:
                    return True
                return False

            @cached_property
            def _get_valid_fields(self) -> Optional[List[str]]:
                """
                Returns the names of the data fields that can be used to update the source.

                Returns:
                    A list of field names that are relevant to the source (useful
                    when the original model changed after a migration).

                """
                fields = self._get_fields()
                source_fields = self.source._meta.get_all_field_names()
                return [field for field in fields if field in source_fields] or None

            def _get_fields(self) -> List[str]:
                """Returns the list of monitored field names."""
                return self.approval_fields

            def _get_fields_data(self) -> Dict[str, object]:
                """
                Returns a dictionary of the data in the sandbox.

                Returns:
                    A dictionary with field names as keys and their sandbox value as values.
                    
                """
                return self.sandbox.get("fields", {})

            def _get_diff(self) -> Optional[List[str]]:
                """
                Returns the difference between the approval data and the source.

                Returns:
                    A list of monitored field names that are different in the source.

                """
                data = self._get_fields_data()
                source_data = {
                    field: getattr(self.source, field) for field in self._get_fields()
                }
                return [
                    key for key in data.keys() if data[key] != source_data[key]
                ] or None

            def _can_user_bypass_approval(self, user) -> bool:
                """
                Returns whether a user can bypass approval rights control

                Args:
                    user: The user to check against.

                """
                if user:
                    if user.has_perm(
                        "{0}.can_moderate_{1}".format(table_app, table_model_name)
                    ):
                        return True
                return False

            def _auto_process_approval(
                self, authors: Iterable = None, update: bool = False
            ):
                """
                Approves or denies edits automatically.

                This method denies or approves according to configuration of
                "auto_approve_..." fields.

                Args:
                    authors: The list of users responsible for the change. If the instance
                        contains a `request` attribute, the connected user is considered the
                        author of the change.
                    update: Is used to differentiate between new objects and updated ones.
                        Is set to `False` when the object is new, `True` otherwise.

                """
                authorized: bool = any(
                    self._can_user_bypass_approval(authors) for author in authors
                ) or not self._needs_approval()
                if authorized or (self.auto_approve_new and not update):
                    self.approve(user=authors[0], save=True)
                if self.auto_approve_staff and any(
                    filter(lambda u: u.is_staff, authors)
                ):
                    self.approve(user=authors[0], save=True)
                self.auto_process_approval(authors=authors)

            # Actions
            def approve(self, user=None, save: bool = False) -> None:
                """Approves pending edits."""
                pre_approval.send(base, instance=self.source, status=self.approved)
                self.approval_date = timezone.now()
                self.approved = True
                self.moderator = user
                self.draft = False
                self.info = pgettext_lazy(
                    "approval_entry", "Congratulations, your edits have been approved."
                )
                self._update_source(save=True)
                if save:
                    super().save()
                post_approval.send(base, instance=self.source, status=self.approved)

            def deny(self, user=None, reason: str = None, save: bool = False):
                """Deny pending edits on object."""
                pre_approval.send(base, instance=self.source, status=self.approved)
                self.moderator = user
                self.approved = False
                self.draft = False
                self.info = reason or pgettext_lazy(
                    "approval_entry", "Your edits have been refused."
                )
                if save:
                    self.save()
                post_approval.send(base, instance=self.source, status=self.approved)

            # Overridable
            def auto_process_approval(self, authors: Iterable = None) -> None:
                """
                User-defined auto-processing, the developer should override this.

                Auto-processinf is the choice of action regarding the author
                or the state of the changes. This method can choose to auto-approve
                for some users or auto-deny changes from inappropriate IPs.

                """
                return None

            def _get_authors(self) -> Iterable:
                """
                Returns the authors of the source instance.

                Warnings:
                    This method *must* be overriden.

                """
                raise NotImplemented("You must define _get_authors() in your model.")

        # Try to make the base model an ApprovedModel automagically
        if ApprovedModel not in base.__bases__:
            base.__bases__ += (ApprovedModel,)
        if issubclass(base, ApprovedModel):
            return Approval
        else:
            raise ImproperlyConfigured(
                pgettext_lazy(
                    "approval",
                    "Your base model must inherit from approval.models.ApprovedModel.",
                )
            )


class ApprovedModel(models.Model):
    """Moderated table mixin."""

    # Getter
    def _get_authors(self) -> Iterable:
        """Returns the authors of the object."""
        if hasattr(self, "request"):
            return [self.request.user]
        return self.approval._get_authors()

    # Actions
    def _revert(self) -> bool:
        """
        Reverts the instance to its last saved state.

        This method deletes unsaved changes on source model instance.

        Returns:
            `True` if revert was possible, `False` otherwise.

        """
        model = self._meta.model
        try:
            self.refresh_from_db()
            return True
        except model.DoesNotExist:
            return False
