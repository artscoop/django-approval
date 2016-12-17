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

    class Book(models.Model):
        """ Book """
        title = models.CharField(max_length=255)
        body = models.TextField()
        published = models.BooleanField(default=True)
        publish = models.DateTimeField(default=None, null=True)


    class BookApproval(ApprovalModel(Book)):
        """
        Approval data for content

        Adds an approval 1:1 reverse relation to the Content model
        """
        approval_fields = ['body', 'published', 'publish']
        approval_default = {'published': False, 'publish': None}

        # Getter
        def _get_authors(self):
            """ Mandatory method to implement """
            return self.source.get_authors()

This will change the book model so it is aware of approval data. An
`approval` attribute will be accessible on every `Book` instance,
allowing to check field values for the underlying `Approval` instance.

*Warning* : Monitored models should not be changed in a pre_save signal.
