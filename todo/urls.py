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

from django.conf.urls.defaults import *

action_patterns = patterns('todo.views.actions',
    (r'^resolve/task/(?P<task_id>\d+)$', 'resolve_task'),
    (r'^resolve/step/(?P<step_id>\d+)$', 'resolve_step'),
)

# the API views return JSON responses
api_patterns = patterns('todo.views.api',
    (r'^step/(?P<step_id>\d+)/reset-time$', 'reset_time'),
    (r'^task/(?P<task_id>\d+)/update-snapshot$', 'update_snapshot'),
    (r'^task/(?P<task_id>\d+)/update-bugid$', 'update_bugid'),
    (r'^task/(?P<obj_id>\d+)/update$', 'update', {'obj': 'task'},
     'todo-api-update-task'),
    (r'^tracker/(?P<obj_id>\d+)/update$', 'update', {'obj': 'tracker'},
     'todo-api-update-tracker'),
)

new_patterns = patterns('',
    (r'^$', 'todo.views.new'),
    (r'^created$', 'todo.views.created'),
)

# demo views are used for testing and as an example for the real views
# that an application wishing to have todo needs to implement
demo_patterns = patterns('todo.views.demo',
    (r'^task/(?P<task_id>\d+)$', 'task'),
    (r'^showcase$', 'showcase'),
    (r'^tracker/(?P<tracker_id>\d+)$', 'tracker'),
    (r'^trackers$', 'trackers'),
)

urlpatterns = patterns('',
    # includes
    (r'^new/', include(new_patterns)),
    (r'^action/', include(action_patterns)),
    (r'^api/', include(api_patterns)),
    (r'^demo/', include(demo_patterns)),
)
