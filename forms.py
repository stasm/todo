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

class AddTaskForm(forms.Form):
    prototype = forms.ModelChoiceField(queryset=ProtoTask.objects.all())
    summary = forms.CharField(label='Summary', max_length=200, required=False,
                              help_text="Leave empty to use the prototype's "
                                        "summary.")
    project = forms.ModelChoiceField(queryset=Project.objects.all())
    locale = forms.ModelChoiceField(queryset=Locale.objects.all())
    parent = TrackerChoiceField(label='Parent tracker',
                                queryset=Tracker.objects.all(),
                                help_text="For consistency's sake, if the "
                                          "parent tracker is specified, its "
                                          "project and locale (if present) "
                                          "will override the choices made "
                                          "above.")
    bugid = forms.IntegerField(label='Bug id', required=False)

class AddTrackerForm(forms.Form):
    prototype = forms.ModelChoiceField(queryset=ProtoTracker.objects.all())
    summary = forms.CharField(label='Summary', max_length=200, required=False,
                              help_text="Leave empty to use the prototype's "
                                        "summary.")
    project = forms.ModelChoiceField(queryset=Project.objects.all())
    locales = LocaleMultipleChoiceField(label='Locales',
                                        queryset=Locale.objects.all())
    # parent tracker
    bugid = forms.IntegerField(label='Bug id', required=False)


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
