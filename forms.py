from django import forms
from todo.models import Todo
from todo.proto.models import ProtoTask

class ChangeTodoForm(forms.Form):
    resolved = forms.BooleanField()
    task_id = forms.IntegerField()

class AddTodoFromProtoForm2(forms.ModelForm):
    class Meta:
        model = Todo
        fields = ['prototype', 'summary']
        
class AddTodoFromProtoForm(forms.Form):
    prototype = forms.ModelChoiceField(queryset=ProtoTask.objects.all())
    summary = forms.CharField(max_length=200, required=False, help_text="Leave empty to use the prototype's summary.")
    # class Meta:
    #     model = Todo
    #     fields = ['summary']
        
        
        
        