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
    project_id = forms.IntegerField()

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
