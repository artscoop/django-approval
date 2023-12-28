# `django-approval`

<img alt="Approval logo" height="128" src="../../approval-icon.svg" title="Django Approval" width="128"/>

*Manage changes to your model instances like a moderator.*

## How to install

You can install this package via `pip` or similar tools:

```bash
pip install django-approval
```

---

## What it does

This package allows a developer to make changes to some models subject to validation before they are
persisted and visible for the public. It works by changing how some model instances are saved.

If a model is marked as subject to validation, every change saved from instances of that model will be persisted
outside the model, so that a reviewer can validate the changes or not. Once it's validated, the changes are propagated to
the object visible to the public.

---

## How to use

To make a model monitorable, you must follow two things:

1. You make your model inherit from `approval.models.MonitoredModel`
2. You create a second model to hold moderation information for the original model, by creating a class inheriting from `approval.models.Sandbox` and using `approval.models.SandboxMeta` as a metaclass.

### Example model and approval config

```python
from approval.models import MonitoredModel, Sandbox, SandboxMeta
from django.conf import settings
from django.db import models

class Entry(MonitoredModel):
    """Example of content entry."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="entries")
    uuid = models.UUIDField(default=..., verbose_name="UUID")
    is_visible = models.BooleanField(default=True, verbose_name="visible")
    created = models.DateTimeField(auto_now_add=True, verbose_name="created date")
    description = models.TextField(blank=True, verbose_name="description")
    content = models.TextField(blank=False, verbose_name="content")
    ...

class EntryApproval(Sandbox, metaclass=SandboxMeta):
    """Content entry moderation sandbox."""
    base = Entry  # Model to monitor, mandatory
    approval_fields = ["description", "content"]  # fields to monitor
    approval_store_fields = ["is_visible"]  # fiels to not monitor, but to restore
    approval_default = {"is_visible": False, "description": ""}  # default values
    auto_approve_staff = False
    auto_approve_new = False
    auto_approve_by_request = False

    def _get_authors(self):
        return [self.source.user]  # source refers to the source Entry instance
```

### Attributes and methods

- `base`: **mandatory**, lets you define to which model the `ForeignKey` of the approval sandbox will point.
- `approval_fields`: **mandatory**, which fields should go to review upon change.
- `approval_store_fields`: which extra fields should be stored in the approval sandbox, even though they do not trigger an approval cycle by themselves. Default is `[]`.
- `approval_default`: dictionary of values that should be applied temporary for a new object until approval. Default is `dict()`
- `auto_approve_staff`: automatically approve changes if the instance author is staff. See `get_authors`. Default is `True`
- `auto_approve_new`: automatically approve changes for new instances. Default is `False`.
- `auto_approve_by_request`: if the instance gets a `request` attribute, use it to determine the author of the content. Default is `True`.

The `Sandbox` model must at least implement `_get_authors(self)`, that is used to know who
are the authors of your instance (since automatic validation can be bypassed if the author is staff, for example).

For the sake of creating new objects with moderation capabilities, **you should have a visibility
field in your monitored model**, and set its default value to `False` through the `approval_default` attribute
of the approval model. It should mark new objects as invisible as long as a moderator has not reviewed them.

---

### Use the connected user as the author of a change

You can use the currently authentified user to decide whether an object approval
status can be directly dismissed or approved. You just have to define a `request`
attribute on your `Entry` (or your own model) instance before saving it.

```python
from django.http import HttpRequest

def view_edit_entry(request: HttpRequest):
    """Fake view to illustrate how it works."""
    entry = ...
    entry.request = request
    entry.save()
```

Auto-approval will look for a `request` attribute in the instance and use the
logged-in user to test if the instance can be approved or not. To enable this behaviour, you need to 
define `auto_approve_by_request = True` in your sandbox class (`EntryApproval` in the above example)

### Disable automatic approval handling

Sometimes you want an environment where signals are not executed. You can disable
signals use for the approval application, and thus disable automatic handling of object
approval. You have to define `APPROVAL_DISABLE_SIGNALS` in your `settings` module:

```python
APPROVAL_DISABLE_SIGNALS = True
```

---

### Forms

When using Django forms to edit an instance with approval data, by default, you would get
a form initialized with the information of the actual instance. This is normally correct, but
with approval monitoring, your changes are not saved into the instance, but in a sandbox.
That means that everytime you would want to edit your instance, you would always see the same data
in the monitored fields.

In order to be able too see your pending changes everytime you edit your instance through a form, 
you have to add a mixin to your form as follows:

```python
from django import forms
from approval.forms import MonitoredForm


class BookForm(forms.ModelForm, MonitoredForm):
    class Meta:
        model = Entry
```

---

### Considerations for use

**Warning** : Monitored models should not be changed in a pre_save signal.
