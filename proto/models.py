from django.db import models
from django.contrib.auth.models import Group

class Prototype(models.Model):
    summary = models.CharField(max_length=200, blank=True)
    owner = models.ForeignKey(Group, null=True, blank=True)
    is_review = models.BooleanField(default=False)
    children = models.ManyToManyField('self', 
                                       symmetrical=False,
                                       related_name='parents',
                                       through="Nesting")

    def __unicode__(self):
        if self.owner is not None:
            owner_str = " [%s%s]" % (self.owner, ': r?' if self.is_review else '')
        else:
            owner_str = ""
        return "%s%s" % (self.summary, owner_str)

class ProtoTask(Prototype):
        
    def __unicode__(self):
        return "%s" % self.summary 

class Nesting(models.Model):
    parent = models.ForeignKey(Prototype, related_name="nestings_where_parent")
    child = models.ForeignKey(Prototype, related_name="nestings_where_child")
    order = models.PositiveIntegerField(null=True, blank=True)
    is_auto_activated = models.BooleanField(default=False)
    resolves_parent = models.BooleanField(default=False)
    repeat_if_failed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ('parent', 'order')
    
    def __unicode__(self):
       return "%s in %s" % (self.child, self.parent)
