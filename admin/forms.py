from django import forms 
from django.forms.models import BaseInlineFormSet, inlineformset_factory

from todo.models import Proto, Nesting

class BaseProtoTrackerSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        kwargs['queryset'] = Nesting.objects.filter(child=kwargs['instance'],
                                                    parent__type=1)
        super(BaseProtoTrackerSet, self).__init__(*args, **kwargs)

ProtoTrackerSet = inlineformset_factory(Proto,
                                        Nesting,
                                        fk_name="child",
                                        formset=BaseProtoTrackerSet)

class BaseProtoTaskSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        kwargs['queryset'] = Nesting.objects.filter(child=kwargs['instance'],
                                                    parent__type=2)
        super(BaseProtoTaskSet, self).__init__(*args, **kwargs)

ProtoTaskSet = inlineformset_factory(Proto,
                                     Nesting,
                                     fk_name="child",
                                     formset=BaseProtoTaskSet)

class BaseProtoStepSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        kwargs['queryset'] = Nesting.objects.filter(child=kwargs['instance'],
                                                    parent__type=3)
        super(BaseProtoStepSet, self).__init__(*args, **kwargs)

ProtoStepSet = inlineformset_factory(Proto,
                                     Nesting,
                                     fk_name="child",
                                     formset=BaseProtoStepSet)

class ProtoTrackerForm(forms.ModelForm):
    parent = forms.ModelChoiceField(Proto.objects.filter(type=1),
                                   label='Proto tracker')

    class Meta:
        model = Nesting
        fields = ['parent']

class ProtoTaskForm(forms.ModelForm):
    parent = forms.ModelChoiceField(Proto.objects.filter(type=2),
                                   label='Proto task')
    order = forms.IntegerField(label='Order', required=True)

    class Meta:
        model = Nesting
        fields = ['parent', 'order', 'is_auto_activated']

class ProtoStepForm(ProtoTaskForm):
    parent = forms.ModelChoiceField(Proto.objects.filter(type=3),
                                   label='Proto step')
