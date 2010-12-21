from django.shortcuts import render_to_response

from todo.forms.new import (CreateNewWizard, ChooseProjectLocaleForm,
                            ChoosePrototypeForm, ChooseParentFactory)

def new(request):
    wizard = CreateNewWizard([ChooseProjectLocaleForm,
                            ChooseParentFactory(),
                            ChoosePrototypeForm])
    return wizard(request)

def created(request):
    return render_to_response('todo/new_created.html')
