# coding: utf-8
from __future__ import absolute_import


class Moderator(object):
    """ Moderator class, where you define moderation mechanisms for your models """
    model = None  # Model class to moderate
    fields = []

    # Getter
    def auto_moderate(self, obj):
        """
        Automoderate an object of the moderator model                                                                                                           
        :param obj: model instance to moderate
        :type obj: django.db.models.Model
        :returns: the moderation status for the object
        :rtype: bool
        """
        return True
