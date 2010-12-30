from django.db import models

from todo.workflow import NEW, ACTIVE, NEXT, ON_HOLD

class Project(models.Model):
    """ e.g. 'Firefox 4.0'
    """
    label = models.CharField(max_length=50)

    class Meta:
        app_label = 'todo'

    def __unicode__(self):
        return '%s' % self.label

    def task_count(self, locale=None):
        if locale is not None:
            tasks = self.tasks.filter(locale=locale)
        else:
            tasks = self.tasks
        all = tasks.count()
        # status and resolution are kept on the intermediary `TaskInProject`
        # model
        open = tasks.filter(statuses__status__lt=ON_HOLD).distinct().count()
        return {'all': all,
                'open': open,
                'completion': 100 * (all - open) / all if all != 0 else 0,
               }

    def open_tasks(self, locale):
        return self.tasks.filter(locale=locale,
                                 statuses__status__in=(NEW, ACTIVE, NEXT))
