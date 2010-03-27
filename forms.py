from django import forms
from life.models import Locale
from todo.models import Project, Todo
from todo.proto.models import ProtoTask

from itertools import groupby

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
    project = forms.ChoiceField(required=False)
    
    def __init__(self, *args, **kwargs):
        super(AddTodoFromProtoForm, self).__init__(*args, **kwargs)
        self.fields['project'].choices = self.types_as_choices()

    def types_as_choices(self):
        choices = []
        projects = Project.objects.active().order_by('type')
        by_type = groupby(projects, lambda p: p.type)
        for t, projects_of_type in by_type:
            type_names = dict(Project._meta.get_field('type').flatchoices)
            choices.append((type_names[t], [(p.id, p.name) for p in projects_of_type]))
        return choices

    def clean_project(self):
        project_id = self.cleaned_data['project']
        try:
            project = Project.objects.get(pk=project_id)
        except:
            raise forms.ValidationError("Project must be a valid todo.models.Project")
        return project
        