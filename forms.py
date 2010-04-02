from django import forms
from life.models import Locale
from todo.models import Actor, Project, Batch, Todo
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
    bug = forms.IntegerField()
    locale = forms.ModelChoiceField(queryset=Locale.objects.all(), required=True)
    project = forms.ChoiceField(required=True)
    batch = forms.ChoiceField(required=False)
    
    def __init__(self, *args, **kwargs):
        super(AddTodoFromProtoForm, self).__init__(*args, **kwargs)
        self.fields['project'].choices = self.projects_as_choices()
        self.fields['batch'].choices = self.batches_as_choices()

    def projects_as_choices(self):
        choices = [('', '---------')]
        projects = Project.objects.active().order_by('type')
        by_type = groupby(projects, lambda p: p.type)
        for t, projects_of_type in by_type:
            type_names = dict(Project._meta.get_field('type').flatchoices)
            choices.append((type_names[t], [(p.id, p.name) for p in projects_of_type]))
        return choices

    def batches_as_choices(self):
        choices = [('', '---------')]
        batches = Batch.objects.active().order_by('project')
        by_project = groupby(batches, lambda p: p.project)
        for project, batches_of_project in by_project:
            choices.append((project, [(b.id, b.name) for b in batches_of_project]))
        return choices

    def clean_project(self):
        project_id = self.cleaned_data['project']
        try:
            project = Project.objects.get(pk=project_id)
        except:
            raise forms.ValidationError("Please choose a project.")
        return project
        
    def clean_batch(self):
        batch_id = self.cleaned_data['batch']
        if batch_id == '':
            return None
        try:
            batch = Batch.objects.get(pk=batch_id)
        except:
            raise forms.ValidationError("If given, batch must be a valid Batch object.")
        return batch

class LocaleMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, locale):
        return "%s / %s" % (locale.code, locale.name)

class TasksFeedBuilderForm(forms.Form):
    locale = LocaleMultipleChoiceField(queryset=Locale.objects.all(), required=False)
    project = forms.ModelMultipleChoiceField(queryset=Project.objects.active(), required=False)

class NextActionsFeedBuilderForm(forms.Form):
    owner = forms.ModelMultipleChoiceField(queryset=Actor.objects.all(), required=False)
    locale = LocaleMultipleChoiceField(queryset=Locale.objects.all(), required=False)
    project = forms.ModelMultipleChoiceField(queryset=Project.objects.active(), required=False)
    task = forms.ModelMultipleChoiceField(queryset=Todo.tasks.active(), required=False)
