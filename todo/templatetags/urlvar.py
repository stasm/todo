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
