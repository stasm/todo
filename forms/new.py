from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import permission_required
from django import forms
from django.contrib.formtools.wizard import FormWizard
from django.db.models import Q

from life.models import Locale
from todo.models import Project, ProtoTask, ProtoTracker, Tracker

class ProjectMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, project):
        return "%s (%s)" % (project.label, project.code)

class LocaleMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, locale):
        return "%s / %s" % (locale.code, locale.name)

class ProtoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, proto):
        if proto.suffix:
            return "%s (%s)" % (proto.summary, proto.suffix)
        return proto.summary

class TrackerChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, tracker):
        if tracker.is_generic():
            return "Generic %d: %s" % (tracker.pk, tracker.summary)
        return "%d: %s" % (tracker.pk, tracker.summary)

class ChooseProjectLocaleForm(forms.Form):
    projects = ProjectMultipleChoiceField(queryset=Project.objects.all())
    locales = LocaleMultipleChoiceField(queryset=Locale.objects.all())

class ChoosePrototypeForm(forms.Form):
    tracker_proto = ProtoChoiceField(queryset=ProtoTracker.objects.all(),
                                     required=False)
    task_proto = ProtoChoiceField(queryset=ProtoTask.objects.all(),
                                  required=False)
    summary = forms.CharField(label='Summary', max_length=200, required=False,
                              help_text="Leave empty to use the prototype's "
                              "summary.")
    alias = forms.CharField(label='Alias', max_length=16, required=False,
                            help_text="Leave empty to use the prototype's "
                            "alias.")

    def clean(self):
        clean = self.cleaned_data
        if ((clean['tracker_proto'] and clean['task_proto']) or
            (not clean['tracker_proto'] and not clean['task_proto'])):
            raise forms.ValidationError('Please choose either a tracker or '
                                        'a task prototype.')
        return clean

class ChooseParentForm(forms.Form):
    parent_summary = forms.CharField(label='Parent Summary', max_length=200,
                                     required=False)
    parent_alias = forms.SlugField(label='Parent Alias', max_length=16,
                                   required=False)

    def __init__(self, projects, locales, *args, **kwargs):
        """Init the form given a list of accepted projects and locales.

        The __init__ method dynamically adds a `parent_tracker` field on the
        ChooseParentForm form given a list of projects and locales that will be
        used to narrow down the list of available parent trackers.

        For a given list of projects, the trackers available in this field will
        belong to all of them.

        For a list of locales, if there's only one locale in the list, the
        filtered trackers will be related to this locale.  If there's more
        locales in the list the filtered trackers will only be the generic
        trackers which are not assigned to any projects/locales. This is
        because in the latter case many per-locale trackers will be created as
        the result and they mustn't be grouped under a tracker that is already
        related to a locale (for constency's sake it is required that the
        decendants of a tracker be related to the same projects/locales as the
        tracker).

        """
        super(ChooseParentForm, self).__init__(*args, **kwargs)
        (locale,) = locales if len(locales) == 1 else (None,)
        _q = Tracker.objects.select_related('locale')
        _q = _q.filter(Q(locale=locale) | Q(locale=None),
                       Q(projects=projects) | Q(projects=None))
        parent = TrackerChoiceField(label='Existing parent tracker',
                                    queryset=_q, required=False)
        self.fields['parent_tracker'] = parent

    def clean(self):
        clean = self.cleaned_data
        if clean['parent_summary'] and clean['parent_tracker']:
            raise forms.ValidationError('Please either choose an existing '
                                        'tracker or create a new one.')
        return clean

class ChooseParentFactory(object):
    """Factory class returning ChooseParentForm instances.

    When an instance of this class is called, an instance of ChooseParentForm
    is returned. 

    This is because FormWizard.get_form(step) returns an instance of a form
    assuming that FormWizard.form_list[step] is a form class. In order to
    dynamically pre-configure the ChooseParentForm based on project and locale
    choices made earlier the 3rd step of the wizard is not a class, but an
    instance of ChooseParentFactory which knows how to instantiate
    ChooseParentForm.

    """
    def __init__(self, projects=None, locales=None):
        self.projects = projects
        self.locales = locales

    def __call__(self, *args, **kwargs):
        return ChooseParentForm(self.projects, self.locales, *args, **kwargs)

class CreateNewWizard(FormWizard):
    def get_template(self, step):
        return 'todo/new_%d.html' % step

    def process_step(self, request, form, step):
        clean = {}
        if form.is_valid():
            clean = form.cleaned_data
        if clean and step == 0:
            projects = clean['projects']
            locales = clean['locales']
            self.form_list[1] = ChooseParentFactory(projects, locales)
            self.extra_context.update({
                'locale_code': (locales[0].code if len(locales) == 1
                                else 'ab-CD'),
            })
        if clean and step == 1:
            parent_tracker = clean['parent_tracker']
            parent_alias = clean['parent_alias']
            self.extra_context.update({
                'parent_alias': (parent_tracker.alias if parent_tracker
                                 else parent_alias),
                'parent_locale': (parent_tracker.locale if parent_tracker 
                                  else None),
            })
    
    @permission_required('todo.create_tracker')
    @permission_required('todo.create_task')
    def done(self, request, form_list):
        clean = {}
        for form in form_list:
            if form.is_valid():
                clean.update(form.cleaned_data)
        parent = clean.pop('parent_tracker')
        if parent is None and clean['parent_summary']:
            # user wants to create a new generic tracker which will be the
            # parent
            parent = Tracker(summary=clean.pop('parent_summary'),
                             alias=clean.pop('parent_alias'))
            parent.save()
            parent.activate(request.user)
        clean['parent'] = parent
        # If the parent exists the desired outcome is for created todo objects'
        # aliases to be appended to the parent's alias.  Suffix (set on child
        # trackers) works exactly this way. If there is no parent, `suffix`
        # will behave like `alias` (cf. `Task.__init__` and `Tracker.__init__`)
        clean['suffix'] = clean.pop('alias', None)
        tracker_proto = clean.pop('tracker_proto')
        task_proto = clean.pop('task_proto')
        prototype = tracker_proto or task_proto
        if prototype.clone_per_locale is True:
            for todo in prototype.spawn_per_locale(request.user, **clean):
                todo.activate(request.user)
        else:
            todo = prototype.spawn(request.user, **clean) 
            todo.activate(request.user)
        return HttpResponseRedirect(reverse('todo.views.created'))
