import django.dispatch

todo_changed = django.dispatch.Signal(providing_args=['user', 'action'])
