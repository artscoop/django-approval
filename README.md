# django-approval
Easy moderation of changes made to models. Django 1.8+ and Python 3.4+

## Installation
1. Download the application and run `python setup.py`
2. or install via pip using `pip install django-approval`

## How to use
### Register an approval model
First, you need to create a model to track changes to your base model.
For example, you create a model named `Book`, that you want to track.
You thus create a model derived from `approval.approvalmodel`, like so:

```python
from typing import Iterable, List
from django.db import models
from approval.models import ApprovalModel, ApprovedModel


class Book(ApprovedModel):
    """A fictitious book model."""
    title = models.CharField(max_length=255)
    author = models.ForeignKey('auth.User')
    body = models.TextField(blank=False)
    published = models.BooleanField(default=True)
    publish = models.DateTimeField(default=None, null=True)
    
    def auto_process_approval(self, authors: Iterable):
        """Optional method to auto-approve or auto-deny content."""
        if self.author.username == "forbidden_author":
            self.deny()
        elif len(authors) == 1 and authors[0].username == "allowed_submitter":
            self.approve(user=authors[0], save=True)
        


class BookApproval(ApprovalModel(Book)):
    """
    Approval data for content.

    Also adds an `approval` reverse attribute to the Book model.
    
    """
    approval_fields = ['body', 'published', 'publish']
    approval_default = {'published': False, 'publish': None}

    def _get_authors(self):
        """Mandatory method to implement."""
        return [self.source.author]
```

An `approval` attribute will be accessible on every `Book` instance,
allowing to check field values for the underlying `Approval` instance.
`approval_fields` is the list of model fields that trigger an approval process
when changed.
`approval_default` is a list of values to apply to a new content while it's
waiting for approval.

### Use the connected user as the author of a change

You can use the currently connected user to decide whether an object approval
status can be directly dismissed or approved. You just have to define a `request`
attribute on your `Book` instance before saving it.

```python
def edit_book(request):
    book.instance = request
    book.save()
```

### Disable automatic approval handling

Sometimes you want an environment where signals are not executed. You can disable
signals use for the approval application, and thus disable automatic handling of object
approval. You have to define `APPROVAL_DISABLE_SIGNALS`:

```python
APPROVAL_DISABLE_SIGNALS = True
```

### Forms

When using Django forms to edit an instance with approval data, by default, you would get
a form initialized with the information of the actual instance. This is normally correct, but
with approval monitoring, your changes are not saved into the instance, but in a sandbox.
That means that everytime you would want to edit your instance, you would always see the same data
in the monitored fields.

In order to be able too see your pending changes everytime you edit your instance, you have
to add a mixin to your form as follows:
```python
from django import forms
from approval.forms import ApprovableFormMixin


class BookForm(forms.ModelForm, ApprovableFormMixin):
    class Meta:
        model = Book

```

### Considerations for use

**Warning** : Monitored models should not be changed in a pre_save signal.
