from django.db import models

class Actor(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    
    class Meta:
        app_label = 'todo'

    def __unicode__(self):
        return self.name
    
    @property
    def code(self):
        return self.slug
