from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.template import RequestContext
from django.core.urlresolvers import reverse

from todo.models import Tracker, Task, Step
from todo.workflow import NEXT

from itertools import groupby

def task(request, task, redirect_view='todo.views.demo.task'):
    """A single task view snippet.

    This snippet is intended to be included on a page showing a single task.
    The template includes all the necessary JS code, too.

    Arguments:
    task -- an instance of todo.models.Task
    redirect_view -- a string with the name of the view which will be used
                     to resolve the URL that the forms will redirect to.

    See todo.views.demo.task for an example of how to use this snippet.

    """
    redirect_url = reverse(redirect_view, args=[task.pk])
    return render_to_string('todo/snippet_task.html',
                            {'task': task,
                             'redirect_url': redirect_url,},
                            # RequestContext is needed for checking 
                            # the permissions of the user.
                            context_instance=RequestContext(request))

def showcase(request, project, locale, tasks_shown=5,
             task_view='todo.views.demo.task'):
    """A snippet to be included on the combined overview page.

    This snippet shows a short list of open tasks for a project+locale
    combination.

    Arguments:
    project -- an instance of todo.models.Project
    locale -- an instance of life.models.Locale
    tasks_shown -- a number of tasks to show
    task_view -- a string with the name of the `single task` view

    See todo.views.demo.combined for an example of how to use this snippet.

    """
    tasks = project.open_tasks(locale).order_by('-latest_resolution_ts')[:5]
    # get all next steps for the current tasks and group them by task
    next_steps = {}
    step_objects = Step.objects.select_related('task').order_by('task')
    flat_next_steps = step_objects.filter(task__in=tasks, status=NEXT)
    for task, steps in groupby(flat_next_steps, lambda s: s.task):
        next_steps[task] = list(steps)
    for task in tasks:
        task.next_steps = next_steps[task]
    return render_to_string('todo/snippet_showcase.html',
                            {'tasks': tasks,
                             'task_view': task_view})

def tree(request, tracker=None, project=None, locale=None,
         task_view='todo.views.demo.task',
         tracker_view='todo.views.demo.tracker'):
    """A snippet to be included on a single tracker page.

    Arguments:
    tracker -- an instance of todo.models.Tracker. If given, project and locale
               are ignored.
    project -- an instance of todo.models.Project. ANDed with locale.
    locale -- an instance of life.models.Locale. ANDed with project.
    task_view -- a string with the name of the `single task` view
    tracker_view -- a string with the name of the `single tracker` view

    See todo.views.demo.tracker and todo.views.demo.trackers for examples of 
    how to use this snippet.

    """
    tracker_objects = Tracker.objects.select_related('parent')
    task_objects = Task.objects.select_related('parent')
    step_objects = Step.objects.select_related('task').order_by('task')

    if tracker is not None:
        trackers = (tracker,)
        tasks = []
    else:
        # call `all` to get a new queryset to work with
        trackers = tracker_objects.all()
        tasks = task_objects.all()
        if project is not None:
            trackers = trackers.filter(projects=project)
            tasks = tasks.filter(projects=project)
        if locale is not None:
            # return top-most trackers for the locale
            trackers = trackers.filter(locale=locale, parent__locale=None)
            # return top-most tasks for the locale
            tasks = tasks.filter(locale=locale, parent__locale=None)
        else:
            # return top-level trackers for the project
            trackers = trackers.filter(parent=None)
            # return top-level tasks for the project
            tasks = tasks.filter(parent=None)

    cache = {}
    next_steps = {}
    depth = 0

    # 1. retrive all trackers and tasks in the tree and store them as flat
    #    lists; for each level in the tree, get next steps for tasks
    while trackers or tasks:
        for tracker in trackers:
            cache[tracker] = {
                'trackers': {},
                'tasks': {},
            }
        for task in tasks:
            cache[task] = {}
        # get all next steps for the current tasks and group them by task
        flat_next_steps = step_objects.filter(task__in=tasks, status=NEXT)
        for task, steps in groupby(flat_next_steps, lambda s: s.task):
            next_steps[task] = list(steps)
        # prepare for the loop's next run
        tasks = task_objects.filter(parent__in=trackers)
        trackers = tracker_objects.filter(parent__in=trackers)
        depth += 1

    # 2. iterate over the cache a couple of times and group retrived trackers
    #    and tasks into a tree-like structure
    tree = {
        'trackers': {},
        'tasks': {},
    }
    while depth:
        # The key to understanding how thos loop works is the fact that nothing
        # is removed from the `cache` at any point.  The `depth` variable makes
        # sure the loop runs enough times to include all relations in the
        # structure.
        keys = sorted(cache.keys(), key=lambda k: k.parent)
        for parent, children in groupby(keys, lambda k: k.parent):
            for child in children:
                # if there is no parent, store the child directly in `tree`
                parent_node = tree if parent is None else cache[parent]
                # put the child under its parent; the first time the loop 
                # executes, `cache[child]` is just an empty dict for all
                # children. In the following runs, however, it contains
                # a subtree of trackers and tasks grouped by the loop before.
                if isinstance(child, Tracker):
                    parent_node['trackers'][child] = cache[child]
                else:
                    parent_node['tasks'][child] = cache[child]
        depth -= 1

    # 3. recurse into the tree to retrieve the meta data about the tasks and
    #    store it in the tree (in corresponding task dicts) and as the facets
    facets = {
        'projects': [],
        'locales': [],
        'statuses': [],
        'prototypes': [],
        'bugs': [],
        'trackers': [],
        'next_steps_owners': [],
        'next_steps': [],
    }

    def _get_facet_data(tree, tracker_chain=[]):
        """Retrive meta data for every task in the tree.

        The function recurses into a tree of trackers and tasks and retrieves
        information about every task it finds.  The data gathered this way is
        then stored in corresponding tasks' dicts in the tree.  It is also used
        to prepare data for the faceted interface that will allow to filter the
        tree.

        Arguments:
            tree -- a tree-like structure of dicts representing a hierarchy of
                    trackers and tasks
            tracker_chain -- a list of prototype names of trackers which were
                             already analyzed in the recursion. This is used to
                             give tasks a breadcrumbs-like 'path' of trackers
                             above them.

        """
        for tracker, subtree in tree['trackers'].iteritems():
            subtree = _get_facet_data(subtree, tracker_chain + [tracker])
            tree['trackers'][tracker] = subtree 
        for task in tree['tasks'].keys():
            task_properties = {
                'projects': [unicode(p) for p in task.projects.all()],
                'locales': [task.locale_repr],
                'statuses': ['%s for %s' % 
                           (s.get_status_display(), unicode(s.project)) for s in
                           task.statuses.all()],
                'prototypes': [task.prototype_repr],
                'bugs': [task.bugid],
                'trackers': [t.summary for t in tracker_chain],
                'next_steps': [unicode(step) for step in next_steps[task]],
                'next_steps_owners': [step.owner_repr
                                      for step in next_steps[task]],
            }
            task.next_steps = next_steps[task]
            tree['tasks'][task] = task_properties
            # Update facet data with properties of the task.
            for prop, val in task_properties.iteritems():
                facets[prop].extend(val)
                facets[prop] = list(set(facets[prop])) # uniquify the list
        return tree

    tree = _get_facet_data(tree)

    return render_to_string('todo/snippet_tree.html',
                            {'tree': tree,
                             'facets': facets,
                             'task_view': task_view,
                             'tracker_view': tracker_view},
                            # RequestContext is needed for checking 
                            # the permissions of the user.
                            context_instance=RequestContext(request))
