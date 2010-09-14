from django.shortcuts import get_object_or_404, render_to_response
from django.utils.safestring import mark_safe

from todo.views import snippets

def task(request, task_id):
    task_div = snippets.task(request, task_id,
                             redirect_view='todo.views.demo.task')
    task_div = mark_safe(task_div)
    return render_to_response('todo/demo_task.html',
                              {'task_div': task_div,})

def combined(request):
    from todo.models import Project
    from life.models import Locale
    if ('project' not in request.GET or
        'locale' not in request.GET):
        raise Exception("No project and/or locale passed as query args.")
    project = get_object_or_404(Project, code=request.GET['project'])
    locale = get_object_or_404(Locale, code=request.GET['locale'])
    open_tasks_div = snippets.combined(request, project, locale,
                                       task_view='todo.views.demo.task')
    open_tasks_div = mark_safe(open_tasks_div)
    return render_to_response('todo/demo_combined.html',
                              {'open_tasks_div': open_tasks_div,})
