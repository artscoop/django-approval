from django.contrib import admin
from approval.admin import MonitoredAdmin, SandboxAdmin
from ..models import EntryApproval, Entry


@admin.register(Entry)
class EntryAdmin(MonitoredAdmin):
    list_display = ["uuid", "user", "is_visible", "created", "description", "content", "get_approval_status"]
    list_filter = ["is_visible", "approval__approved"]


@admin.register(EntryApproval)
class EntryApprovalAdmin(SandboxAdmin):
    pass
