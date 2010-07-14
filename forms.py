from django import forms
from life.models import Locale
from todo.models import *

class LocaleMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, locale):
        return "%s / %s" % (locale.code, locale.name)

class ResolveTodoForm(forms.Form):
    task_id = forms.IntegerField()
    
class ResolveReviewTodoForm(forms.Form):    
    task_id = forms.IntegerField()
    success = forms.BooleanField(required=False)
    failure = forms.BooleanField(required=False)
    
    def clean(self):
        cleaned_data = self.cleaned_data
        success = cleaned_data.get("success")
        failure = cleaned_data.get("failure")
        if not success and not failure:
            raise forms.ValidationError("A resolution needs to be specified for review todos.")
        return cleaned_data
