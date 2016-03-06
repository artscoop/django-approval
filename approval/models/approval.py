# coding: utf-8
""" Approval models. """
from annoying.fields import AutoOneToOneField
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy
from picklefield.fields import PickledObjectField


def ApprovalModel(base):
    """
    Define and record a moderation model from a base model.

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
    reverse_name = 'moderated_{0}_approval'.format(base._meta.model_name)

    class Approval(models.Model):
        """
        Parametrized model
        """

        # Configuration
        approval_fields = []
        approval_default = {}
        auto_approve_staff = True
        auto_approve_new = False

        # Constants
        MODERATION = ((None, _("Pending")), (False, _("Refused")), (True, _("Approved")))
        DRAFT = ((False, _("Waiting for moderation")), (True, _("Draft")))

        # Fields
        source = AutoOneToOneField(base, null=False, on_delete=models.CASCADE, related_name='approval')
        sandbox = PickledObjectField(default={}, blank=False, verbose_name=_("Data"))
        approved = models.NullBooleanField(default=None, choices=MODERATION, verbose_name=pgettext_lazy('approval_entry', "Moderated"))
        moderator = models.ForeignKey(settings.AUTH_USER_MODEL, default=None, blank=True, null=True,
                                      related_name=reverse_name, verbose_name=pgettext_lazy('approval_entry', "Moderated by"))
        approval_date = models.DateTimeField(null=True, verbose_name=pgettext_lazy('approval_entry', "Moderated at"))
        info = models.TextField(blank=True, verbose_name=_("Reason"))
        draft = models.BooleanField(default=True, choices=DRAFT, verbose_name=pgettext_lazy('approval_entry', "Draft"))
        updated = models.DateTimeField(auto_now=True, verbose_name=pgettext_lazy('approval_entry', "Updated"))

        # API
        def _update_source(self, default=False, save=False):
            """
            Update fields of the source to reflect the state of the moderation queue
            :param default: change the source with the approval_default values only
            :param save: must we change the source status permanently
            """
            original = dict()  # Revert to target values in case of failure
            if default is False:
                for field in self._get_fields_data():
                    original[field] = getattr(self.source, field)
                    setattr(self.source, field, self.sandbox['fields'][field])
            else:
                for field in self.approval_default.keys():
                    setattr(self.source, field, self.approval_default[field])

            try:
                self.source.clean_fields()  # will fail with ValidationError if there is a problem
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

        def _update_sandbox(self, slot=None, source=None):
            """
            Update fields of the sandbox to reflect the state of the source
            """
            slot = slot or "fields"
            source = source or self.source
            fields = self._get_fields()
            values = {key: getattr(source, key) for key in fields if hasattr(source, key)}
            self.sandbox[slot] = values
            self.approved = None
            self.save()

        def submit_approval(self):
            """
            Set the status of the object to waiting for moderation
            """
            if self.draft is True:
                self.draft = False
                self.save()
                return True
            return False

        def is_draft(self):
            """
            Returns if the object is submitted for approval or not
            :returns: True if not submitted, False if waiting for approval
            """
            return self.draft

        def _can_bypass_approval(self):
            """
            Returns whether the status of the object really needs an approval
            :returns: True if the status is not potentially harmful.
            """
            if self._get_diff() is None:
                return None
            return False

        def _get_invalid_fields(self):
            """
            Returns the names of the data fields that cannot be used
            to update the source.
            :returns: a list of field names
            :rtype: list | None
            """
            fields = self._get_fields()
            source_fields = self.source._meta.get_all_field_names()
            return [field for field in fields if field in source_fields] or None

        def _get_fields(self):
            """
            Returns the list of monitored field names
            :returns: a list of strings
            """
            return self.approval_fields

        def _get_fields_data(self):
            """
            Returns a dictionary of the data in the sandbox
            :return: a dict
            """
            return self.sandbox.get('fields', {})

        def _get_diff(self):
            """
            Return the difference between the approval data and the source
            :returns: a list of field names that are different in the source
            :rtype: list | None
            """
            data = self._get_fields_data()
            source_data = {field: getattr(self.source, field) for field in self._get_fields()}
            return [key for key in data.keys() if data[key] != source_data[key]] or None

        def _is_authorized(self, user):
            """
            Returns whether an user has approval bypass rights
            :param user: user or list of users, or even None
            """
            if user:
                users = [user] if not isinstance(user, list) else user
                for user in users:
                    if user.has_perm('{0}.can_moderate_{1}'.format(table_app, table_model_name)):
                        return user
            return False

        def _auto_process(self, authors=None, update=False):
            """
            Approve or deny edits automatically.
            :param author: author or list of authors or None
            :param update: define if the process is an update
            """
            authorized = self._is_authorized(authors) or self._can_bypass_approval()
            if authorized is not False or (self.auto_approve_new and not update):
                self.approve(user=authorized, save=True)
            self.auto_process(authors=authors)

        # Actions
        def approve(self, user=None, save=False):
            """ Approve pending object state """
            self.approval_date = timezone.now()
            self.approved = True
            self.moderator = user
            self.draft = False
            self.info = pgettext_lazy('approval_entry', "Congratulations, your edits have been approved.")
            self._update_source(save=True)
            if save:
                super().save()

        def deny(self, user=None, reason=None, save=False):
            """ Deny pending edits on object """
            self.moderator = user
            self.approved = False
            self.draft = False
            self.info = reason or pgettext_lazy('approval_entry', "Your edits have been refused.")
            if save:
                self.save()

        # Overridable
        def auto_process(self, authors=None):
            """ User-defined auto-processing, the developer should override this """
            return None

        def _get_authors(self):
            """
            Return the authors of the source instance. Override.

            :rtype: list | tuple | None
            """
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
            db_table = table_name
            app_label = 'content'
            verbose_name = "{name} approval".format(name=name)
            verbose_name_plural = "{name} approval".format(name=name_plural)
            permissions = [['can_moderate_{0}'.format(table_model_name), "Can moderate {name}".format(name=name_plural)]]

    if ApprovedModel not in base.__bases__:
        base.__bases__ += (ApprovedModel,)
    if issubclass(base, ApprovedModel):
        return Approval
    else:
        raise ImproperlyConfigured(_("Your base model must inherit from approval.models.ApprovedModel."))


class ApprovedModel(models.Model):
    """ Moderated table mixin """

    # Getter
    def _get_authors(self):
        """
        Returns the authors of the object
        """
        if hasattr(self, 'request'):
            return [self.request.user]
        return self.approval._get_authors()

    # Actions
    def _revert(self):
        """
        Revert the instance to its last saved state
        :return: True if revert was possible, else False
        """
        Model = self._meta.model
        try:
            self = Model.objects.get(self.pk)
            return True
        except Model.DoesNotExist:
            return False

    def _submit_approval(self):
        """ Undraft """
        return self.approval.submit_approval()

    # Meta
    class Meta:
        abstract = True
