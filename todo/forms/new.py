# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla todo app.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Stas Malolepszy <stas@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import permission_required
from django import forms
from django.contrib.formtools.wizard import FormWizard
from django.db import transaction

from life.models import Locale
from todo.models import Project, ProtoTask, ProtoTracker, Tracker

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

class ChooseProjectFactory(object):
    """Factory class returning ChooseProjectForm instances.

    When an instance of this class is called, an instance of ChooseProjectForm 
    is returned.  See the docstring at `todo.forms.new.ChooseParentFactory` for 
    the explanation of why this is needed.

    """
    def __init__(self, projects=None):
        self.projects = projects or Project.objects.order_by('label')

    def __call__(self, *args, **kwargs):
        return ChooseProjectForm(self.projects, *args, **kwargs)

class ChooseProjectForm(forms.Form):
    """Actual choose-project form, instantiated by the factory.

    It only has one field, 'projects', which is set up dynamically when the 
    factory is called.

    """
    def __init__(self, projects, *args, **kwargs):
        super(ChooseProjectForm, self).__init__(*args, **kwargs)
        _projects = forms.ModelMultipleChoiceField(queryset=projects)
        self.fields['projects'] = _projects

class ChooseLocaleFactory(object):
    """Factory class returning ChooseLocaleFactory instances.

    When an instance of this class is called, an instance of ChooseLocaleForm 
    is returned.  See the docstring at `todo.forms.new.ChooseParentFactory` for 
    the explanation of why this is needed.

    """
    def __init__(self, locales=None):
        self.locales = locales or Locale.objects.order_by('code')

    def __call__(self, *args, **kwargs):
        return ChooseLocaleForm(self.locales, *args, **kwargs)

class ChooseLocaleForm(forms.Form):
    """Actual choose-locale form, instantiated by the factory.

    It only has one field, 'locales', which is set up dynamically when the 
    factory is called.

    """
    def __init__(self, locales, *args, **kwargs):
        super(ChooseLocaleForm, self).__init__(*args, **kwargs)
        _locales = LocaleMultipleChoiceField(queryset=locales)
        self.fields['locales'] = _locales

class ChoosePrototypeForm(forms.Form):
    tracker_proto = ProtoChoiceField(queryset=ProtoTracker.objects.all(),
                                     required=False)
    task_proto = ProtoChoiceField(queryset=ProtoTask.objects.all(),
                                  required=False)
    summary = forms.CharField(label='Summary', max_length=200, required=False,
                              help_text="Leave empty to use the prototype's "
                              "summary.")
    alias = forms.SlugField(label='Alias', max_length=16, required=False,
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
        trackers = Tracker.objects.select_related('locale')
        # always show the generic trackers, no matter what; `statuses=None` is 
        # like `projects=None` but avoids an unnecessary JOIN
        possible_parents = trackers.filter(locale=None, statuses=None)
        # make sure they're displayed on top of the list (`statuses` will be 
        # None for them)
        possible_parents = possible_parents.order_by('statuses', 'pk')
        if len(locales) == 1:
            # if there's only one locale selected, we also want to show regular 
            # trackers related to this locale and to the exactly same set of 
            # projects
            (locale,) = locales
            specific = trackers.filter(locale=locale)
            for p in projects:
                # If the form is embedded in another application, `p` is not an 
                # instance of `todo.models.Project` and instead points to an 
                # instance of that other application's equivalent of a project.
                project = getattr(p, 'todo', None) or p
                # Every project narrows down the list of possible parents; the 
                # objective is to end with a list of trackers that are related 
                # to all selected projects (IN would match any, not all).
                specific = specific.filter(projects=project)
            # concatenate generic and specific trackers into a single QuerySet
            possible_parents = possible_parents | specific
        parent = TrackerChoiceField(label='Existing parent tracker',
                                    queryset=possible_parents,
                                    required=False)
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

    This is because FormWizard.get_form(step) returns an instance of the 
    step-th form by calling FormWizard.form_list[step]() as if it always was 
    a form class.  In order to be able to dynamically pre-configure the 
    ChooseParentForm form based on project and locale choices made in the 
    previous steps, the 3rd form of the wizard is not a class, but instead is 
    an instance of ChooseParentFactory which knows how to instantiate 
    ChooseParentForm when called.

    """
    def __init__(self, projects=None, locales=None):
        self.projects = projects
        self.locales = locales

    def __call__(self, *args, **kwargs):
        return ChooseParentForm(self.projects, self.locales, *args, **kwargs)

class CreateNewWizard(FormWizard):

    def __init__(self, **config):
        formlist = [
            # set up the first step according to the config
            ChooseProjectFactory(config.get('projects', None)),
            ChooseLocaleFactory(),
            ChooseParentFactory(),
            ChoosePrototypeForm,
        ]
        super(CreateNewWizard, self).__init__(formlist)
        # save the rest of the config
        self.locale_filter = config.get('locale_filter', None)
        self.get_template = config.get('get_template', self.get_template)
        self.task_view = config.get('task_view', None)
        self.tracker_view = config.get('tracker_view', None)
        self.thankyou_view = config.get('thankyou_view', 'todo.views.created')

    def get_template(self, step):
        """Return the name of the template to use for the given step.

        Given a zero-based index of the step, return a string with the name 
        of the template to use for this step.

        Note that this method can be overwritten by specifying a custom 
        `get_template` function in the config, when initializing the wizard.

        Arguments:
            step - a zero-based index of the step (integer)

        Returns:
            a string - the name of the template to use for the step

        """
        return 'todo/new_%d.html' % step

    def process_step(self, request, form, step):
        """Process the previous or the current step.

        Every time the FormWizard's URL is hit, this method is run first for 
        all previous steps (for i in range(current_step), and then for the 
        current step as well.  This allows to process all earlier input and 
        transfer the user's choices from one step to another.  It's also 
        possible to dynamically modify the FormWizard's state here, depending 
        on the choices made in previous steps.

        Arguments:
            request -- the current request object,
            form -- the form object to process,
            step -- a zero-based index of the form to process in the wizard's 
                    form_list.

        """
        clean = {}
        if form.is_valid():
            clean = form.cleaned_data

        if clean and step == 0:
            self.projects = clean['projects']
            # see what locales are available for those projects and set up the 
            # next step accordingly
            locales = Locale.objects.order_by('code')
            if callable(self.locale_filter):
                # if the todo-enabled app doesn't define its own filter 
                # function, don't bother running a default
                for p in self.projects:
                    # the QuerySets are AND-ed
                    locales = locales & self.locale_filter(p)
            self.form_list[1] = ChooseLocaleFactory(locales)
        if clean and step == 1:
            self.locales = clean['locales']
            # with projects and locales already chosen before, see which 
            # trackers could be potential parents for the whole batch
            self.form_list[2] = ChooseParentFactory(self.projects,
                                                    self.locales)
            self.extra_context.update({
                'locale_code': (self.locales[0].code if len(self.locales) == 1
                                else 'ab-CD'),
            })
        if clean and step == 2:
            # the data gathering is almost complete.  let the user see how the 
            # final outcome will look like based on the previous choices.
            parent_tracker = clean['parent_tracker']
            parent_alias = clean['parent_alias']
            self.extra_context.update({
                'parent_alias': (parent_tracker.alias if parent_tracker
                                 else parent_alias),
                'parent_locale': (parent_tracker.locale if parent_tracker 
                                  else None),
            })

    def get_redirect_url(self, spawned_items, type_is_tracker, parent):
        """Return the URL to redirect to after a successful POST.

        Given the list of spawned items, their type and the parent, look at the 
        configuration settings of the wizard and figure out the best URL to 
        redirect to after a successful POST.

        Arguments:
            spawned_items -- a list of todo items spawned from a prototype,
            type_is_tracker -- a boolean; True if the prototype used was 
                               a ProtoTracker, False if it was a ProtoTask,
            parent -- a tracker that is the parent of the items in 
                      spawned_items.

        Returns:
            a string -- the URL to redirect to (to be used in 
                        a HttpResponseRedirect)

        """
        if parent and self.tracker_view:
            # if the parent tracker exists, always redirect to it
            return reverse(self.tracker_view, args=[parent.pk])
        view = self.tracker_view if type_is_tracker else self.task_view
        if view and len(spawned_items) == 1:
            # we have one item that we can redirect to
            return reverse(view, args=[spawned_items[0].pk])
        # fall back to the generic 'thank you' page
        return reverse(self.thankyou_view)
    
    @permission_required('todo.create_tracker')
    @permission_required('todo.create_task')
    @transaction.commit_on_success
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
        # finally, make sure the projects passed to the prototype are instances 
        # of `todo.models.Project`
        clean['projects'] = [getattr(p, 'todo', None) or p 
                             for p in clean['projects']]
        if prototype.clone_per_locale:
            # spawn_per_locale is a generator
            spawned = list(prototype.spawn_per_locale(request.user, **clean))
        else:
            spawned = [prototype.spawn(request.user, **clean)]
        redirect_url = self.get_redirect_url(spawned,
                                             prototype == tracker_proto,
                                             parent)
        return HttpResponseRedirect(redirect_url)
