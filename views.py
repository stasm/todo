from django.shortcuts import render_to_response
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, permission_required
from django.core.urlresolvers import reverse
from django.template import Context, RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import simplejson
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

from life.models import Locale

from todo.models import Project, Batch, Todo
from todo.forms import ResolveTodoForm, ResolveReviewTodoForm, AddTodoFromProtoForm, TasksFeedBuilderForm, NextActionsFeedBuilderForm
from todo.workflow import statuses
from todo.feeds import build_feed

from itertools import groupby


def index(request):
    tasks_orderby_locale = Todo.tasks.active().select_related('locale').order_by('locale__code')
    tasks_by_locale = dict([ (loc, len(list(tasks))) for loc, tasks in groupby(tasks_orderby_locale, lambda t: t.locale)])
    locales = []
    for locale in Locale.objects.all().order_by('code'):
        try:
            locales.append((locale, tasks_by_locale[locale]))
        except KeyError:
            locales.append((locale, 0))

    active_projects= Project.objects.active().order_by('type')
    active_batches= Batch.objects.active().select_related('project').order_by('project')
    batches_by_project = dict([ (project, list(batches)) for project, batches in groupby(active_batches, lambda t: t.project)])

    ordered_tasks = Todo.tasks.select_related('project', 'batch').filter(project__in=active_projects).order_by('project', 'batch')
    tasks_by_project = dict([ (p, list(tasks)) for p, tasks in groupby(ordered_tasks, lambda t: t.project)])
    tasks_by_batch = dict([ (p, list(tasks)) for p, tasks in groupby(ordered_tasks, lambda t: t.batch)])
    
    projects_by_type = []
    for t, projects in groupby(active_projects, lambda p: p.type):
        projects_of_type = []
        type = dict(Project._meta.get_field('type').flatchoices)[t]
        for project in projects:
            batches = []
            if batches_by_project.has_key(project):
                for batch in batches_by_project[project]:
                    if tasks_by_batch.has_key(batch):
                        tasks = tasks_by_batch[batch]
                        all_tasks = len(tasks)
                        open_tasks = len([task for task in tasks if task.status_is('active')])
                        resolved_tasks = len([task for task in tasks if task.status_is('resolved')])
                        batches.append((batch, {'has_tasks': True,
                                                'open': open_tasks,
                                                'resolved': resolved_tasks,
                                                'percent': 100 * resolved_tasks / all_tasks}))
                    else:
                        batches.append((batch, {'has_tasks': False}))
            if tasks_by_project.has_key(project):
                tasks = tasks_by_project[project]
                all_tasks = len(tasks)
                open_tasks = len([task for task in tasks if task.status_is('active')])
                resolved_tasks = len([task for task in tasks if task.status_is('resolved')])
                projects_of_type.append((project, {'batches': batches,
                                                   'has_tasks': True,
                                                   'open': open_tasks,
                                                   'resolved': resolved_tasks,
                                                   'percent': 100 * resolved_tasks / all_tasks}))
            else:
                projects_of_type.append((project, {'batches': batches, 
                                                   'has_tasks': False}))
        projects_by_type.append((type, projects_of_type))

    return render_to_response('todo/index.html',
                              {'locales' : locales,
                               'projects_by_type' : projects_by_type},
                              context_instance=RequestContext(request))
    
def dashboard(request, locale_code=None, project_slug=None, bug_id=None):
    
    def _get_feeds(objs, filter_name, for_string):
        feeds = []
        for items in ('tasks', 'next'):
            feeds.append(build_feed(items, {filter_name: objs}, for_string=for_string))
        return feeds
    feeds = []
    title = 'Tasks'
    order = ['.project', '.batch', '.locale']
    show_resolved = request.GET.get('show_resolved', 0)
    query = request.GET.copy()
    query['show_resolved'] = 1
    args = [('show_resolved', show_resolved)]
    if request.GET.has_key('snapshot'):
        args.append(('snapshot', 1))
    if locale_code is not None:
        locales = locale_code.split(',')
        locales = Locale.objects.filter(code__in=locales)
        locale_names = [unicode(locale) for locale in locales]
        locale_ids = locales.values_list('code', flat=True)
        if locales:
            args += [('locale', loc_id) for loc_id in locale_ids]
            for_string = ' for %s' % ', '.join(locale_names)
            title += for_string
            feeds += _get_feeds(locales, 'locale', for_string)
            order.remove('.locale')
    if project_slug is not None:
        projects = project_slug.split(',')
        projects = Project.objects.filter(slug__in=projects)
        projects_names = [unicode(project) for project in projects]
        project_slugs = projects.values_list('slug', flat=True)
        if projects:
            args += [('project', project_slug) for project_slug in project_slugs]
            for_string = ' for %s' % ', '.join(projects_names)
            title += for_string
            feeds += _get_feeds(projects, 'project', for_string)
            order.remove('.project')
    if bug_id is not None:
        bug_ids = bug_id.split(',')
        bugs = [int(b) for b in bug_ids]
        if bugs:
            args += [('bug', bug) for bug in bugs]
            for_string = ' for bug %s' % ', '.join(bug_ids)
            title += for_string
            feeds += _get_feeds(bugs, 'bug', for_string)
            order = ['.locale']
    
    return render_to_response('todo/dashboard.html',
                              {'title' : title,
                               'feeds' : feeds,
                               'order' : ', '.join(order),
                               'args' : mark_safe(urlencode(args)),
                               'snapshot' : request.GET.has_key('snapshot'),
                               'show_resolved_path' : request.path + '?' + query.urlencode()},
                              context_instance=RequestContext(request))
    
def task(request, task_id):
    task = Todo.objects.get(pk=task_id)
    return render_to_response('todo/details.html',
                              {'task' : task},
                              context_instance=RequestContext(request))
                        
@require_POST
@permission_required('todo.change_todo')
def resolve(request, todo_id):
    error_message = "Incorrect data"
    try:
        todo = Todo.objects.get(pk=todo_id)
    except KeyError:
        error_message = "Todo %s doesn't exist." % todo_id
    else:
        if not todo.is_review:
            form = ResolveTodoForm(request.POST)
            if form.is_valid():
                task_id = form.cleaned_data['task_id']
                todo.resolve()
                return HttpResponseRedirect(reverse('todo.views.task', 
                                                    args=(task_id,)))
        else:
            form = ResolveReviewTodoForm(request.POST)
            if form.is_valid():
                task_id = form.cleaned_data['task_id']
                success = form.cleaned_data['success']
                resolution = 1 if success else 2
                todo.resolve(resolution)
                return HttpResponseRedirect(reverse('todo.views.task', 
                                                    args=(task_id,)))
        
    return HttpResponse("%s" % error_message)

@login_required
def new(request):
    error_message = None
    form = AddTodoFromProtoForm()
    return render_to_response('todo/new.html', 
                              {'form' : form,
                               'error_message' : error_message},
                              context_instance=RequestContext(request))

@require_POST
@login_required
def create(request):
    form = AddTodoFromProtoForm(request.POST)
    if form.is_valid():
        prototype = form.cleaned_data.pop('prototype')
        custom_fields = form.cleaned_data
        task = Todo.proto.create(prototype, **custom_fields)
        task.activate()
        return HttpResponseRedirect(reverse('todo.views.task', 
                                            args=(task.id,)))
    else:
        error_message = "Incorrect data"
        return render_to_response('todo/new.html', {'form' : form,
                                                    'error_message' : error_message})
def feed_builder(request):
    task_form = TasksFeedBuilderForm()
    next_form = NextActionsFeedBuilderForm()
    return render_to_response('todo/feed_builder.html',
                              {'task_form': task_form,
                               'next_form': next_form},
                              context_instance=RequestContext(request))

@require_POST
def redirect_to_feed(request):
    items = request.POST.get('items')
    if items == 'tasks':
        form = TasksFeedBuilderForm(request.POST)
    else:
        form = NextActionsFeedBuilderForm(request.POST)
    if form.is_valid():
        feed = build_feed(items, form.cleaned_data)
        return HttpResponseRedirect(feed[1])
