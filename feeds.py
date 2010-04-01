from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Atom1Feed
from django.core.urlresolvers import reverse

from life.models import Locale
from todo.models import Actor, Project, Todo

class Lens(object):
    def __init__(self, kwargs, allowed=('locale', 'project')):
        """
        kwargs should be a dict with keys: locale, project, owner, task. The values of this dict
        can either be a list of corresponding objects (e.g. locale=[<Locale>, <Locale>]) or
        a comma-separated string of codes (slugs) (e.g. locale='fr,de').
        """
        self.locale = []
        self.project = []
        self.owner = []
        self.task = []
        self._props = []
        
        if 'owner' in allowed and kwargs.has_key('owner'):
            self.owner = kwargs['owner'] if not isinstance(kwargs['owner'], basestring) else Actor.objects.filter(slug__in=kwargs['owner'].split(','))
            if self.owner: self._props.append('owner')
        if 'locale' in allowed and kwargs.has_key('locale'):
            self.locale = kwargs['locale'] if not isinstance(kwargs['locale'], basestring) else Locale.objects.filter(code__in=kwargs['locale'].split(','))
            if self.locale: self._props.append('locale')
        if 'project' in allowed and kwargs.has_key('project'):
            self.project = kwargs['project'] if not isinstance(kwargs['project'], basestring) else Project.objects.filter(slug__in=kwargs['project'].split(','))
            if self.project: self._props.append('project')
        if 'task' in allowed and kwargs.has_key('task'):
            self.task = kwargs['task'] if not isinstance(kwargs['task'], basestring) else Todo.tasks.filter(pk__in=kwargs['task'].split(','))
            if self.task: self._props.append('task')
    
    def get_for_string(self):
        string = ''
        for prop in self._props:
            string += " for %s" % ', '.join([unicode(v) for v in getattr(self, prop)])
        return string
        
    def get_url_string(self):
        strings = []
        for prop in self._props:
            strings.append("%s:%s" % (prop, ','.join([v.code for v in getattr(self, prop)])))
        return '/'.join(strings)

    def filter_queryset(self, q, rel_string='%s'):
        filter_dict = {}
        for prop in self._props:
            if prop in ('owner', 'task'):
                filter_dict.update({'%s__in' % prop: getattr(self, prop)})
            else:
                filter_dict.update({'%s__in' % (rel_string % prop): getattr(self, prop)})
        return q.filter(**filter_dict)
        
class NewTasksFeed(Feed):
    feed_type = Atom1Feed
    slug = 'tasks'
    
    def get_object(self, bits):
        kwargs = dict( [bit.split(':') for bit in bits] )
        return Lens(kwargs, allowed=('locale', 'project'))

    def title(self, lens):
        title = "New tasks"
        title += lens.get_for_string()
        return title
        
    def subtitle(self, lens):
        subtitle = "New l10n tasks (product and web)" 
        subtitle += lens.get_for_string()
        return subtitle

    def link(self, lens):
        url = '%s/%s' % (self.slug, lens.get_url_string)
        return reverse('django.contrib.syndication.views.feed', kwargs={'url': url})

    def item_link(self, task):
        return task.get_absolute_url()

    def items(self, lens):
        tasks = Todo.tasks.active()
        tasks = lens.filter_queryset(tasks)
        return tasks.order_by('-pk')[:30]

class NewNextActionsFeed(NewTasksFeed):
    slug = 'next'
    
    def get_object(self, bits):
        kwargs = dict( [bit.split(':') for bit in bits] )
        return Lens(kwargs, allowed=('owner', 'locale', 'project', 'task'))
        
    def title(self, lens):
        title = "Next actions"
        title += lens.get_for_string()
        return title
        
    def subtitle(self, lens):
        subtitle = "Next actions" 
        subtitle += lens.get_for_string()
        return subtitle

    def item_link(self, todo):
        return todo.task.get_absolute_url()

    def items(self, lens):
        tasks = Todo.objects.next().select_related('task')
        tasks = lens.filter_queryset(tasks, 'task__%s')
        return tasks.order_by('-pk')[:30]

def build_feed(items, kwargs, for_string=None):
    lens = Lens(kwargs, allowed=('owner', 'locale', 'project', 'task'))
    url = '%s/%s' % (items, lens.get_url_string())
    feed_url = reverse('django.contrib.syndication.views.feed', kwargs={'url': url})
    if for_string is None: for_string = lens.get_for_string()
    if items == 'tasks': 
        feed_name = "Todo: new tasks" + for_string
    elif items == 'next': 
        feed_name = "Todo: new next actions" + for_string
    else:
        feed_name = "Todo: items" + for_string
    return (feed_name, feed_url)
    