"""
Django Admin configuration for approval.

Attributes:
    SandboxAdmin:
        The `ApprovalAdmin` class configures the Administration interface
        to help admins monitor all the changed still pending in every
        approval-enabled model.
"""
from django.contrib.admin import display
from django.contrib.admin.options import ModelAdmin
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


class SandboxAdmin(ModelAdmin):
    """Moderation of approval sandboxes."""

    list_select_related = True
    list_display = ["id", "source", "moderator", "approved", "draft", "updated", "get_sandbox_data"]
    readonly_fields = ["source"]
    list_display_links = ["id"]
    list_filter = ["approved", "draft", "updated", "moderator__is_superuser"]
    actions = ["do_deny", "do_approve"]

    # Actions
    @display(description=_("Deny selected approval requests"))
    def do_deny(self, request, queryset):
        """Refuse selected approval requests."""
        for approval in queryset:
            approval.deny(user=request.user, save=True)
        self.message_user(request, _("Selected edits have been denied."))

    @display(description=_("Approve selected approval requests"))
    def do_approve(self, request, queryset):
        """Accept selected approval requests."""
        for approval in queryset:
            approval.approve(user=request.user, save=True)
        self.message_user(request, _("Selected edits have been accepted."))

    # Getter
    @display(description=_("Content"))
    def get_sandbox_data(self, obj) -> str:
        """Return a human-readable version of the sandbox contents."""
        fields = obj.sandbox.get("fields", {})
        store = obj.sandbox.get("store", {})
        return mark_safe(
            render_to_string(
                "approval/display/sandbox-data.html", {"fields": fields, "store": store}
            )
        )
