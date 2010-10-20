from django import forms

class UpdateTodoForm(forms.Form):
    summary = forms.CharField(max_length=200, required=True)
    bug = forms.CharField(max_length=200, required=False)

    def clean_bug(self):
        # the input value is a string, because it may be an ID or an alias.
        # do the intelogent thing here, and convert the ID to an integer.
        bug = self.cleaned_data['bug']
        if not bug:
            return None
        try:
            bug = int(bug)
        except ValueError:
            # it's a string!
            pass
        return bug

class ResolveTaskForm(forms.Form):
    redirect_url = forms.CharField()
    project_code = forms.CharField()

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
