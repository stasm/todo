from django.shortcuts import get_object_or_404, render_to_response
from django.utils.safestring import mark_safe

from todo.views import snippets

def task(request, task_id):
    from todo.models import Task
    task = get_object_or_404(Task, pk=task_id)
    task_snippet = snippets.task(request, task,
                                 redirect_view='todo.views.demo.task')
    return render_to_response('todo/demo_task.html',
                              {'task_snippet': task_snippet,})

def showcase(request):
    from todo.models import Project
    from life.models import Locale
    if ('project' not in request.GET or
        'locale' not in request.GET):
        raise Exception("No project and/or locale passed as query args.")
    project = get_object_or_404(Project, code=request.GET['project'])
    locale = get_object_or_404(Locale, code=request.GET['locale'])
    open_tasks = snippets.showcase(request, project, locale,
                                   task_view='todo.views.demo.task')
    return render_to_response('todo/demo_showcase.html',
                              {'open_tasks': open_tasks,})

def tracker(request, tracker_id):
    from todo.models import Tracker
    tracker = get_object_or_404(Tracker, pk=tracker_id)
    tree = snippets.tree(request, tracker=tracker,
                         project=None, locale=None,
                         task_view='todo.views.demo.task',
                         tracker_view='todo.views.demo.tracker')
    return render_to_response('todo/demo_tree.html',
                              {'tree': tree,})

def trackers(request):
    from todo.models import Project
    from life.models import Locale
    if ('project' not in request.GET and
        'locale' not in request.GET):
        raise Exception("No project and/or locale passed as query args.")
    project = locale = None
    if 'project' in request.GET:
        project = get_object_or_404(Project, code=request.GET['project'])
    if 'locale' in request.GET:
        locale = get_object_or_404(Locale, code=request.GET['locale'])
    tree = snippets.tree(request, tracker=None,
                         project=project, locale=locale,
                         task_view='todo.views.demo.task',
                         tracker_view='todo.views.demo.tracker')
    return render_to_response('todo/demo_tree.html',
                              {'tree': tree,})
