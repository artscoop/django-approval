# coding: utf-8
""" Approval models. """
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.db import models
from django.utils import timezone
from django.utils.translation import pgettext_lazy, ugettext_lazy as _
from picklefield.fields import PickledObjectField


def ApprovalModel(base):
    """
    Define and record a moderation model from a base model.
    La fonction renvoie une classe héritée de Model et dont les attributs
    Meta sont dérivés de ceux de <base>.
    How to use:
    - Have your monitored model extend ApprovedModel
    - Make another model using ApprovalModel(Monitoredmodelname)
    - Make your model admin extend ApprovalAdmin
    - Your form logic may set instance.request = request.
    :type base: django.db.models.Model & ApprovedModel
    """
    table_name = '{0}_approval'.format(base._meta.db_table)
    table_app = base._meta.app_label
    table_model_name = base._meta.model_name
    name = base._meta.verbose_name
    name_plural = base._meta.verbose_name_plural

    class Approval(models.Model):
        """
        Parametrized model
        """

        # Configuration
        approval_fields = []
        auto_approve_staff = True
        auto_approve_empty_fields = True

        # Constants
        MODERATION = ((None, _("Pending")), (False, _("Refused")), (True, _("Approved")))
        DRAFT = ((False, _("Waiting for moderation")), (True, _("Draft")))

        # Fields
        source = models.OneToOneField(base, null=False, on_delete=models.CASCADE, related_name='approval')
        sandbox = PickledObjectField(default={}, blank=False, verbose_name=_("Data"))
        approved = models.NullBooleanField(default=None, choices=MODERATION, verbose_name=pgettext_lazy('approval_entry', "Moderated"))
        moderator = models.ForeignKey(settings.AUTH_USER_MODEL, default=None, blank=True, null=True, verbose_name=pgettext_lazy('approval_entry', "Moderated by"))
        approval_date = models.DateTimeField(null=True, verbose_name=pgettext_lazy('approval_entry', "Moderated at"))
        info = models.TextField(blank=True, verbose_name=_("Reason"))
        draft = models.BooleanField(default=True, choices=DRAFT, verbose_name=pgettext_lazy('approval_entry', "Draft"))
        updated = models.DateTimeField(auto_now=True, verbose_name=pgettext_lazy('approval_entry', "Updated"))

        # Getter
        def is_sandbox_valid(self):
            """ Return whether sandbox data is valid or not """
            for field in self.sandbox.get('fields', {}):
                if not hasattr(self.source, field):
                    return False
            return True

        def has_sandbox_diff(self):
            """ Is the object different in the sandbox from the public view ? """
            checked_fields = [field for field in self.sandbox.get('fields', {}) if hasattr(self.source, field)]
            for field in checked_fields:
                if self.sandbox['fields'][field] != getattr(self.source, field):
                    return True
            return False

        def get_sandbox_fields(self):
            return getattr(self, 'approval_fields', [])

        # Setter
        def update_source(self, force=True, empty_only=False):
            """
            Update the target object with the current sandbox data
            :param force: update the object even if one or several sandboxed fields do not match the current schema
            :type force: bool
            """
            original = dict()
            for field in self.sandbox.get('fields', {}):
                original[field] = getattr(self.source, field)
                if not empty_only or not self.sandbox['fields'][field]:
                    setattr(self.source, field, self.sandbox['fields'][field])
            try:
                self.source.clean_fields()  # will fail with ValidationError if there is a problem
                self.source._approval_done = True
                self.source.save()
            except ValidationError as exc:
                if force:
                    for key in exc.message_dict:
                        if hasattr(self.source, key):
                            setattr(self.source, key, original[key])
                    self.source._approval_done = True
                    self.source.save()
                else:
                    raise

        def approve(self, user=None, save=False):
            """ Approve pending object state """
            self.approval_date = timezone.now()
            self.approved = True
            self.moderator = user
            self.info = pgettext_lazy('approval_entry', "Congratulations, your edits have been approved.")
            self.update_source()
            if save:
                super().save()

        def deny(self, user=None, reason=None, save=False):
            """ Deny pending edits on object """
            self.moderator = user
            self.approved = False
            self.info = reason or pgettext_lazy('approval_entry', "Your edits have been refused.")
            if save:
                self.save()

        def _auto_process(self, user=None):
            """ Approve or deny edits automatically. """

            # Approve staff users with appropriate permissions
            users = self._get_users()
            users = list(users) if users else users
            if isinstance(users, (list, tuple, set)):
                for user in users:
                    if isinstance(user, AbstractUser):
                        if self.auto_approve_staff and user.has_perm('{0}.can_moderate_{1}'.format(table_app, table_model_name)):
                            self.approve(save=True)
                            return True
            # Approve empty fields
            if self.auto_approve_empty_fields:
                self.update_source(empty_only=True)

        # Overridable
        def _get_users(self):
            """
            Return the authors of the source instance. Override.
            :rtype: list | tuple | None
            """
            return None

        def auto_process(self, user=None):
            """ User-defined auto-processing """
            return None

        # Overrides
        def save(self, *args, **kwargs):
            """ Save object """
            return super().save(*args, **kwargs)

        def __str__(self):
            """ Return text representation of the object """
            return "{target} approval status: {status}".format(target=self.source, status=self.get_approved_display())

        # Metadata
        class Meta:
            abstract = True
            permissions = [['can_moderate_{0}'.format(table_model_name), "Can moderate {name}".format(name=name_plural)]]

    if not ApprovedModel in base.__bases__:
        base.__bases__ += (ApprovedModel,)
    if issubclass(base, ApprovedModel):
        return Approval
    else:
        raise ImproperlyConfigured(_("Your base model must inherit from approval.models.ApprovedModel."))


class ApprovedModel(models.Model):
    """ Moderated table mixin """

    # Getter
    def is_waiting_for_approval(self):
        Model = self._meta.get_field('approval').model
        try:
            return self.approval.draft is False
        except Model.DoesNotExist:
            return False

    # Actions
    def _copy_to_sandbox(self, save=True):
        """
        Copy monitored fields to the sandbox
        :type self: django.db.models.Model
        """
        Model = self._meta.get_field('approval').model
        try:
            approval = getattr(self, 'approval', None)
        except Model.DoesNotExist:
            approval = Model.objects.create(source=self, approved=False)
        fields = approval.get_sandbox_fields()
        values = {key: getattr(self, key) for key in fields if hasattr(self, key)}
        approval.sandbox['fields'] = values
        approval.approved = None
        if save:
            approval.save()

    def _copy_from_sandbox(self):
        """
        Copy sandboxed fields to the model
        """
        Model = self._meta.get_field('approval').model
        try:
            approval = getattr(self, 'approval')
            if approval.draft is True:
                fields = approval.get_sandbox_fields()
                for field in fields:
                    setattr(self, field, approval.sandbox['fields'][field])
        except Model.DoesNotExist:
            pass

    def _submit_to_approval(self):
        """ Undraft """
        Model = self._meta.get_field('approval').model
        try:
            approval = getattr(self, 'approval')
            if approval.draft is True:
                approval.draft = False
                approval.save()
                return True
        except Model.DoesNotExist:
            pass
        return False

    # Meta
    class Meta:
        abstract = True
