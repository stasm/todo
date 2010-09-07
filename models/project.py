from django.db import models
from django.template.defaultfilters import slugify

class ProjectLine(models.Model):
    """ e.g. 'Firefox'
    """
    label = models.CharField(max_length=50)
    code = models.SlugField(max_length=50)

    class Meta:
        app_label = 'todo'

    def __unicode__(self):
        return self.label

class Project(models.Model):
    """ e.g. 'Firefox 4.0'
    """
    line = models.ForeignKey(ProjectLine)
    version = models.CharField(max_length=10)
    code = models.SlugField(max_length=20, blank=True)
    codename = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        app_label = 'todo'

    def save(self):
        if not self.code.startswith(self.line.code):
            code = self.code or slugify(self.version)
            self.code = '%s%s' % (self.line.code, code)
        super(Project, self).save()

    def __unicode__(self):
        return '%s %s' % (self.line.label, self.version)
