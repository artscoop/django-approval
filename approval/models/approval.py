# coding: utf-8
""" Approval models. """
from django.conf import settings
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.db import models
from django.utils import timezone
from django.utils.translation import pgettext_lazy, ugettext_lazy as _
from picklefield.fields import PickledObjectField


def ApprovalModel(base):
    """
    Définir et enregistrer un modèle de modération d'un modèle de base.
    La fonction renvoie une classe héritée de Model et dont les attributs
    Meta sont dérivés de ceux de <base>.
    :type base: django.db.models.Model & ApprovedModel
    """
    table_name = '{0}_approval'.format(base._meta.db_table)
    table_app = base._meta.app_label
    name = base._meta.verbose_name
    name_plural = base._meta.verbose_name_plural

    class Approval(models.Model):
        """ Parametrized model """

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
        moderator = models.ForeignKey(settings.AUTH_USER_MODEL, default=None, null=True, verbose_name=pgettext_lazy('approval_entry', "Moderated by"))
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
        def update_source(self, force=True):
            """
            Update the target object with the current sandbox data
            :param force: update the object even if one or several sandboxed fields do not match the current schema
            :type force: bool
            """
            original = dict()
            for field in self.sandbox.get('fields', {}):
                original[field] = getattr(self.source, field)
                setattr(self.source, field, self.sandbox['fields'][field])
            try:
                self.source.clean_fields()  # will fail with ValidationError if there is a problem
                self.source.save()
            except ValidationError as exc:
                if force:
                    for key in exc.message_dict:
                        if hasattr(self.source, key):
                            setattr(self.source, key, original[key])
                    self.source.save()
                else:
                    raise

        def approve(self, user=None, save=False):
            """ Approve pending object state """
            self.approval_date = timezone.now()
            self.moderator = user
            self.info = pgettext_lazy('approval_entry', "Congratulations, your edits have been approved.")
            self.update_source()
            if save:
                self.save()

        def deny(self, user=None, reason=None, save=False):
            """ Deny pending edits on object """
            self.moderator = user
            self.info = reason or pgettext_lazy('approval_entry', "Your edits have been refused.")
            if save:
                self.save()

        def _auto_process(self):
            """ Approve or deny edits automatically. """
            user = self._get_user()
            if user is None or user.has_perm('approval.can_moderate_entries'):
                self.approve(user=user)

        # Overridable
        def _get_user(self):
            """ Return the author of the source instance. Override. """
            pass

        def auto_process(self):
            """ User-defined auto-processing """
            return None

        # Overrides
        def save(self, *args, **kwargs):
            return super().save(*args, **kwargs)

        # Metadata
        class Meta:
            abstract = False
            db_table = table_name
            app_label = table_app
            verbose_name = "{name} approval".format(name=name)
            verbose_name_plural = "{name} approval".format(name=name_plural)

    if issubclass(base, ApprovedModel):
        return Approval
    else:
        raise ImproperlyConfigured(_("Your base model must inherit from approval.models.ApprovedModel."))


class ApprovedModel(models.Model):
    """ Moderated table mixin """

    # Actions
    def _copy_to_sandbox(self, save=True):
        """
        Copy monitored fields to the sandbox
        :type self: django.db.models.Model
        """
        Model = self._meta.fields['approval'].model
        try:
            approval = getattr(self, 'approval', None)
        except Model.DoesNotExist:
            approval = Model.objects.create(source=self)
        fields = approval.get_sandbox_fields()
        values = {key: getattr(self, key) for key in fields if hasattr(self, key)}
        approval.sandbox['fields'] = values
        if save:
            approval.save()

    # Meta
    class Meta:
        abstract = True
