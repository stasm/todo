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

from django.template import Library
from django.template.defaulttags import URLNode

register = Library()

class URLVarNode(URLNode):
    def __init__(self, view_var, args, kwargs, asvar):
        self.view_var = view_var
        # URLNode's `view_name` is None because it will be only known
        # in a defined context. See `render` below.
        super(URLVarNode, self).__init__(None, args, kwargs, asvar)

    def render(self, context):
        self.view_name = self.view_var.resolve(context)
        return super(URLVarNode, self).render(context)

@register.tag
def urlvar(parser, token):
    """Returns an absolute URL matching given view with its parameters.

    The tag behaves almost exactly the same as django.template.defaulttags.url,
    with the only difference being that instead of a name of a view as the
    first argument, it takes a variable which will be resolved to a name of
    a view in the current context.

    This allows to use URL resolving on views whose name is unknown to the
    author of the template. It's useful for snippets which will be included
    in other apps' views.

    Example use:
        {% urlvar single_task_view task.id %}
        where `single_task_view` is a variable available in the context.

    """
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError("'%s' takes at least one argument"
                                  " (path to a view)" % bits[0])
    viewname = parser.compile_filter(bits[1])
    args = []
    kwargs = {}
    asvar = None

    if len(bits) > 2:
        bits = iter(bits[2:])
        for bit in bits:
            if bit == 'as':
                asvar = bits.next()
                break
            else:
                for arg in bit.split(","):
                    if '=' in arg:
                        k, v = arg.split('=', 1)
                        k = k.strip()
                        kwargs[k] = parser.compile_filter(v)
                    elif arg:
                        args.append(parser.compile_filter(arg))
    return URLVarNode(viewname, args, kwargs, asvar)
