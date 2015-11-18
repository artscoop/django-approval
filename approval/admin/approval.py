# coding: utf-8
from django.contrib.admin.options import ModelAdmin
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from approval.models.approval import ApprovedModel
from scoop.core.util.shortcuts import addattr


class ApprovalAdmin(ModelAdmin):
    """ Moderation of approval models """

    list_select_related = True
    list_display = ['id', 'source', 'moderator', 'approved', 'approval_date', 'draft', 'updated', 'get_sandbox_data']
    list_display_links = ['id']
    list_filter = ['approved', 'draft']
    actions = ['do_deny', 'do_approve']

    # Actions
    @addattr(short_description=_("Deny selected approval requests"))
    def do_deny(self, request, queryset):
        """ Refuse selected approval requests """
        for approval in queryset:
            approval.deny(user=request.user, save=True)
        self.message_user(request, _("Selected edits have been denied."))

    @addattr(short_description=_("Approve selected approval requests"))
    def do_approve(self, request, queryset):
        """ Accept selected approval requests """
        for approval in queryset:
            approval.approve(user=request.user, save=True)
        self.message_user(request, _("Selected edits have been accepted."))

    @addattr(short_description=_("Content"), allow_tags=True)
    def get_sandbox_data(self, obj):
        """ Return a human-readable version of the sandbox contents """
        output = obj.sandbox['fields']
        return render_to_string('approval/display/sandbox-data.html', {'fields': output})


class ApprovableAdmin(ModelAdmin):
    """ ModelAdmin mixin for approval-controlled objects """

    # Overrides
    def get_object(self, request, object_id, from_field=None):
        """ Return the desired object, augmented with a request attribute """
        obj = super().get_object(request, object_id)
        if isinstance(obj, ApprovedModel):
            obj.approval._update_source(update=False, save=False)
            obj.request = request
        return obj
