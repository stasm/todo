# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla todo app.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Stas Malolepszy <stas@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

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
