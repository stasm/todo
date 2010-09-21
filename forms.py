from django import forms
from life.models import Locale
from todo.models import Project, ProtoTask, ProtoTracker, Tracker

class LocaleMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, locale):
        return "%s / %s" % (locale.code, locale.name)

class TrackerChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, tracker):
        return "%d: %s (%s + %s)" % (tracker.pk, tracker.summary,
                                     tracker.project, tracker.locale)

class ChooseParentForm(forms.Form):
    "Form used to choose an existing parent tracker or create a new one."

    _q = Tracker.objects.select_related('project', 'locale').all()
    tracker = TrackerChoiceField(label='Existing parent tracker',
                                queryset=_q, required=False,
                                help_text="OR create a new one:")
    parent_summary = forms.CharField(label='Summary', max_length=200,
                                     required=False)
    parent_project = forms.ModelChoiceField(queryset=Project.objects.all(),
                                     required=False)
    parent_locale = forms.ModelChoiceField(queryset=Locale.objects.all(),
                                    required=False)
    parent_suffix = forms.SlugField(label='Alias suffix', max_length=8,
                                    required=False, help_text="Will be "
                                    "appended to parent's or project's alias. "
                                    "Good example: '-search'")

    def clean(self):
        clean = self.cleaned_data
        if clean['parent_summary'] and not clean['parent_project']:
            raise forms.ValidationError("Specify at least a summary and a "
                                        "project to create a new tracker.")
        return clean

class AddTasksForm(forms.Form):
    prototype = forms.ModelChoiceField(queryset=ProtoTask.objects.all())
    summary = forms.CharField(label='Summary', max_length=200, required=False,
                              help_text="Leave empty to use the prototype's "
                              "summary.")
    suffix = forms.SlugField(label='Alias suffix', max_length=8,
                             required=False, help_text="Will be appended to "
                             "parent's or project's alias. Good example: "
                             "'-search'. Leave empty to use the prototype's "
                             "suffix.")
    project = forms.ModelChoiceField(queryset=Project.objects.all())
    locales = LocaleMultipleChoiceField(queryset=Locale.objects.all(),
                                        required=False)
    bugid = forms.IntegerField(label='Bug id', required=False)

class AddTrackersForm(AddTasksForm):
    prototype = forms.ModelChoiceField(queryset=ProtoTracker.objects.all())

class ResolveTaskForm(forms.Form):
    redirect_url = forms.CharField()

class ResolveSimpleStepForm(forms.Form):
    redirect_url = forms.CharField()
    
class ResolveReviewStepForm(forms.Form):    
    redirect_url = forms.CharField()
    success = forms.BooleanField(required=False)
    failure = forms.BooleanField(required=False)
    
    def clean(self):
        cleaned_data = self.cleaned_data
        success = cleaned_data.get("success")
        failure = cleaned_data.get("failure")
        if not success and not failure:
            raise forms.ValidationError("A resolution needs to be specified"
                                        "for review todos.")
        return cleaned_data
