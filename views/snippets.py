from django.shortcuts import get_object_or_404, render_to_response
from django.template.loader import render_to_string

def combined(request, project, locale):
    return render_to_string('todo/snippet_combined.html',
                            {'tasks': project.open_tasks(locale),})
