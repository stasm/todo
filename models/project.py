from django.db import models
from django.template.defaultfilters import slugify

from itertools import chain

from shipping.models import AppVersion

class Project(models.Model):
    """ e.g. 'Firefox 4.0'
    """
    label = models.CharField(max_length=50)
    code = models.SlugField(max_length=50, blank=True, unique=True)
    codename = models.CharField(max_length=50, blank=True, null=True)
    # this could be moved to homepage.models.Project
    # see https://bugzilla.mozilla.org/show_bug.cgi?id=589786#c4
    shipping = models.OneToOneField(AppVersion, related_name="todo")

    class Meta:
        app_label = 'todo'

    def save(self):
        if not self.code:
            self.code = slugify(self.label)
        super(Project, self).save()

    def __unicode__(self):
        return '%s' % self.label

    def task_count(self, locale=None):
        if locale is not None:
            tasks = self.tasks.filter(locale=locale)
        else:
            tasks = self.tasks
        all = tasks.count()
        open = tasks.filter(status__lt=4).count()
        return {'all': all,
                'open': open,
                'completion': 100 * (all - open) / all if all != 0 else 0,
               }

    def open_tasks(self, locale):
        return self.tasks.filter(locale=locale, status__in=(1, 2))

    def iterchildren(self, locale, status=(1, 2)):
        """Get immediate children of a project.

        Returns an iterator with immediate children of a project, be it
        trackers or tasks, for a particular locale.

        An optional `status` argument can be passed in order to get trackers
        and tasks of the specified status. The default value will return new
        and active objects.

        """
        trackers = self.trackers.top_level().filter(locale=locale,
                                                    status__in=status)
        tasks = self.tasks.top_level().filter(locale=locale,
                                              status__in=status)
        return chain(trackers, tasks)
