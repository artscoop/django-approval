"""Signals sent by the application."""
from django.dispatch.dispatcher import Signal

# Sent just before an instance undergoes approval
pre_approval = Signal(["instance", "status"])

# Sent just after an instance undergoes approval
post_approval = Signal(["instance", "status"])
