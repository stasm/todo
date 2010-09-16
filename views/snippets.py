from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.template import RequestContext
from django.core.urlresolvers import reverse

from todo.models import Tracker, Task

def task(request, task_id, redirect_view='todo.views.demo.task'):
    """A single task view snippet.

    This snippet is intended to be included on a page showing a single task.
    The template includes all the necessary JS code, too.

    Arguments:
    task_id -- an integer specifying task's ID
    redirect_view -- a string with the name of the view which will be used
                     to resolve the URL that the forms will redirect to.

    See todo.views.demo.task for an example of how to use this snippet.

    """
    task = get_object_or_404(Task, pk=task_id)
    redirect_url = reverse(redirect_view, args=[task.pk])
    return render_to_string('todo/snippet_task.html',
                            {'task': task,
                             'redirect_url': redirect_url,},
                            # RequestContext is needed for checking 
                            # the permissions of the user.
                            context_instance=RequestContext(request))

def combined(request, project, locale, task_view='todo.views.demo.task'):
    """A snippet to be included on the combined overview page.

    This snippet shows a short list of open tasks for a project+locale
    combination.

    Arguments:
    project -- an instance of todo.models.Project
    locale -- an instance of life.models.Locale

    See todo.views.demo.combined for an example of how to use this snippet.

    """
    return render_to_string('todo/snippet_combined.html',
                            {'tasks': project.open_tasks(locale),
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

    See todo.views.demo.tracker and todo.views.demo.trackers for examples of 
    how to use this snippet.

    """
    # FIXME: needs refactoring to reduce the number of queries.
    # Possible approach:
    #   start with a list of open tasks, via selected_related('parent')
    #   group them by parent
    #   get parents of the parents in a single query, again with 
    #     selected_related('parent')
    #   repeat until there's no parents left

    if tracker is not None:
        trackers = (tracker,)
    else:
        trackers = Tracker.objects
        # FIXME: Add tasks.
        if project is not None:
            trackers = trackers.filter(project=project)
        if locale is not None:
            # return top-most trackers for the locale
            trackers = trackers.filter(locale=locale, parent__locale=None)
        else:
            # return top-level trackers for the project
            trackers = trackers.filter(parent=None)

    facets = {
        'project': [],
        'locale': [],
        'status': [],
        'prototype': [],
        'bug': [],
        'trackers': [],
        'next_steps_owners': [],
        'next_steps': [],
    }
    tree, facets = _make_tree(trackers, [], [], facets) 

    return render_to_string('todo/snippet_tree.html',
                            {'tree': tree,
                             'facets': facets,
                             'task_view': task_view,
                             'tracker_view': tracker_view})

def _update_facets(facets, task_properties):
    "Update facet data with properties of a task."

    for prop, val in task_properties.iteritems():
        if type(val) is list:
            facets[prop].extend(val)
        else:
            facets[prop].append(val)
        facets[prop] = list(set(facets[prop])) # uniquify the list
    return facets

def _make_tree(trackers, tasks, tracker_chain, facets):
    """Construct the data tree about requested trackers.

    The function recursively iterates over the given list of trackers
    to create a data hierarchy with information about each tracker and
    task. This is done so that all the necessary data is avaiable before 
    the template is rendered, which in turn allows to populate the facets
    used to navigate the tracker tree.

    Arguments:
    trackers -- an iterable of todo.models.Tracker instances that that tree
                will be constructed for.
    tasks -- an iterable of todo.models.Tracker instances that that tree
             will be constructed for.
    tracker_chain -- a list of prototype names of tracker which were already
                     analyzed in the recursion. This is used to give tasks 
                     a 'path' of trackers above them.
    facets -- a dict with facet data.

    """
    # FIXME: The function works its way from the top to the bottom of the 
    # tracker structure, which results in tons of queries being made. 
    # A possible solution, as mentioned in todo.views.snippets.tree, might
    # be to start from the tasks and go up.

    tree = {'trackers': {}, 'tasks': {}}
    for tracker in trackers:
        subtree, facets = _make_tree(tracker.children.all(),
                                     tracker.tasks.all(),
                                     tracker_chain +
                                     [tracker.prototype.summary],
                                     facets)
        tree['trackers'].update({tracker: subtree}) 
    for task in tasks:
        task_properties = {
            'project': unicode(task.project),
            'locale': unicode(task.locale),
            'status': task.get_status_display(),
            'prototype': task.prototype.summary,
            'bug': task.bug,
            'trackers': tracker_chain,
            'next_steps': [unicode(step) for step in task.next_steps()],
            'next_steps_owners': [unicode(step.owner)
                                  for step in task.next_steps()],
        }
        tree['tasks'].update({task: task_properties})
        facets = _update_facets(facets, task_properties)
    return tree, facets
