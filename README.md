# Moderation application for Django

`django-approval` is a tool to facilitate moderation of changes made to any model instance. 

This application supports Django 3.2 and above, and Python 3.10 and above.

<img src="./approval-icon.svg" height="64" alt="Approval logo"/>

This application lets you define a moderation pipeline on almost any model, that generally works as follows:

1. One user on your site makes a change on specific fields of some content
2. The user validates that his/her changes are suitable to get moderated (from draft)
3. While the changes are not checked by a moderator, nothing *new* will be visible on the front website
4. When the moderator accepts the changes, they are applied to the live data visible by the users.


## How to install

`django-approval` is best installed using `pip`:

```bash
pip install django-approval
```

## Documentation

See the [online documentation here](https://artscoop.github.io/django-approval/approval.html)
