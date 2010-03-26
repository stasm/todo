from django import forms
from life.models import Locale
from todo.models import Project, Todo
from todo.proto.models import ProtoTask

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
        
class AddTodoFromProtoForm(forms.Form):
    prototype = forms.ModelChoiceField(queryset=ProtoTask.objects.all())
    summary = forms.CharField(max_length=200, required=False, help_text="Leave empty to use the prototype's summary.")
    locale = forms.ModelChoiceField(queryset=Locale.objects.all(), required=False)
    project = forms.ModelChoiceField(queryset=Project.objects.active(), required=False)
