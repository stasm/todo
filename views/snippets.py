from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.template import RequestContext
from django.core.urlresolvers import reverse

from todo.models import Task

def task(request, task_id, redirect_view):
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

def combined(request, project, locale, task_view):
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
