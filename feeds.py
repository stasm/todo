from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Atom1Feed

from life.models import Locale
from todo.models import Actor, Project, Todo

class Lens(object):
    def __init__(self, args, allowed=('locale', 'project')):
        self.locale = None
        self.project = None
        self.owner = None
        self._props = []
        
        if 'owner' in allowed and args.has_key('owner'):
            self.owner = Actor.objects.filter(slug__in=args['owner'].split(','))
            self._props.append('owner')
        if 'locale' in allowed and args.has_key('locale'):
            self.locale = Locale.objects.filter(code__in=args['locale'].split(','))
            self._props.append('locale')
        if 'project' in allowed and args.has_key('project'):
            self.project = Project.objects.filter(slug__in=args['project'].split(','))
            self._props.append('project')
    
    def get_for_string(self):
        string = ''
        for prop in self._props:
            string += " for %s" % ', '.join([unicode(v) for v in getattr(self, prop)])
        return string
        
    def get_url_string(self):
        string = ''
        for prop in self._props:
            string += "%s:%s" % (prop, ','.join([v.code for v in getattr(self, prop)]))
        return string

    def filter_queryset(self, q, rel_string='%s'):
        filter_dict = {}
        for prop in self._props:
            if prop == 'owner':
                filter_dict.update({'%s__in' % prop: getattr(self, prop)})
            else:
                filter_dict.update({'%s__in' % (rel_string % prop): getattr(self, prop)})
        return q.filter(**filter_dict)
        
class NewTasksFeed(Feed):
    feed_type = Atom1Feed
    
    def get_object(self, bits):
        args = dict( [bit.split(':') for bit in bits] )
        return Lens(args, ('locale', 'project'))

    def title(self, lens):
        title = "New tasks"
        title += lens.get_for_string()
        return title
        
    def subtitle(self, lens):
        subtitle = "New l10n tasks (product and web)" 
        subtitle += lens.get_for_string()
        return subtitle

    def link(self, lens):
        url = '/todo/feed/tasks/'
        url += lens.get_url_string()
        return url

    def item_link(self, task):
        return task.get_absolute_url()

    def items(self, lens):
        tasks = Todo.tasks.active()
        tasks = lens.filter_queryset(tasks)
        return tasks.order_by('-pk')[:30]

class NewNextActionsFeed(NewTasksFeed):
    
    def get_object(self, bits):
        args = dict( [bit.split(':') for bit in bits] )
        return Lens(args, ('owner', 'locale', 'project'))
        
    def title(self, lens):
        title = "Next actions"
        title += lens.get_for_string()
        return title
        
    def subtitle(self, lens):
        subtitle = "Next actions" 
        subtitle += lens.get_for_string()
        return subtitle

    def link(self, lens):
        url = '/todo/feed/next/'
        url += lens.get_url_string()
        return url

    def item_link(self, todo):
        return todo.task.get_absolute_url()

    def items(self, lens):
        tasks = Todo.objects.next().select_related('task')
        tasks = lens.filter_queryset(tasks, 'task__%s')
        return tasks.order_by('-pk')[:30]
