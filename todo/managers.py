from django.db import models

class StatusManager(models.Manager):
    use_for_related_fields = True
    requestable_for_task = ('active', 'resolved', 'all', 'open')
    def open(self):
        return self.filter(status__in=(1, 2, 3))
    def new(self):
        return self.filter(status=1)
    def active(self):
        return self.filter(status__in=(2, 3))
    def next(self):
        return self.filter(status=3)
    def on_hold(self):
        return self.filter(status=4)
    def resolved(self):
        return self.filter(status=5)
    def top_level(self):
        return self.filter(parent=None)
