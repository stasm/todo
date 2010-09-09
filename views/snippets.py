from django.shortcuts import get_object_or_404, render_to_response
from django.template.loader import render_to_string

def combined_demo(request, project_code, locale_code):
    from todo.models import Project
    from life.models import Locale
    project = Project.objects.get(code=project_code)
    locale = Locale.objects.get(code=locale_code)
    return render_to_response('todo/snippet_combined.html',
                              {'tasks': project.open_tasks(locale),})

def combined(request, project, locale):
    return render_to_string('todo/snippet_combined.html',
                            {'tasks': project.open_tasks(locale),})
