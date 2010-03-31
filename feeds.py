from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Atom1Feed
from django.contrib.auth.models import Group

from life.models import Locale
from todo.models import Project, Todo

class Lens(object):
    locale = None
    project = None
    owner = None
    
    def __init__(self, args):
        self.locale = Locale.objects.get(code=args['locale']) if args.has_key('locale') else None
        self.project = Project.objects.get(slug=args['project']) if args.has_key('project') else None
        self.owner = Group.objects.get(name=args['owner']) if args.has_key('owner') else None
    
    def for_string(self, prop):
        return " for %s" % getattr(self, prop) if getattr(self, prop) is not None else ''

    def url_string(self, prop):
        return "%s:%s" % (prop, getattr(self, prop).code) if getattr(self, prop) is not None else ''

    def filter_queryset(self, q):
        if self.locale:
            q = q.filter(locale=self.locale)
        if self.project:
            q = q.filter(project=self.project)
        if self.owner:
            q = q.filter(owner=self.owner)
        return q
        
class NewTasksFeed(Feed):
    feed_type = Atom1Feed
    
    def get_object(self, bits):
        args = dict( [ bit.split(':') for bit in bits] )
        return Lens(args)

    def title(self, lens):
        title = "New tasks"
        title += lens.for_string('locale')
        title += lens.for_string('project')
        return title
        
    def subtitle(self, lens):
        subtitle = "New l10n tasks (product and web)" 
        subtitle += lens.for_string('locale')
        subtitle += lens.for_string('project')
        return subtitle

    def link(self, lens):
        url = '/todo/feed/tasks/'
        url += lens.url_string('locale')
        url += lens.url_string('project')
        return url

    def item_link(self, task):
        return task.get_absolute_url()

    def items(self, lens):
        tasks = Todo.tasks.active()
        tasks = lens.filter_queryset(tasks)
        return tasks.order_by('-pk')[:30]

class NewNextActionsFeed(NewTasksFeed):
    pass