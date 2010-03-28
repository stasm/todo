statuses = {
    # int: (verb, adjective)
    1: ('created', 'new'),
    2: ('activated', 'active'),
    3: ('nexted', 'next'),
    4: ('put on hold', 'on hold'),
    5: ('resolved', 'resolved'),
}

STATUS_ADJ_CHOICES = tuple([(i, adj) for i, (verb, adj) in statuses.items()])
STATUS_VERB_CHOICES = tuple([(i, verb) for i, (verb, adj) in statuses.items()])

resolutions = {
    1: 'success',
    2: 'failure',
    3: 'incomplete',
}

RESOLUTION_CHOICES = tuple([(i, res) for i, res in resolutions.items()])