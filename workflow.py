# statuses
NEW = 1
ACTIVE = 2
NEXT = 3
ON_HOLD = 4
RESOLVED = 5

STATUS_CHOICES = (
    (NEW, 'new'),
    (ACTIVE, 'active'),
    (NEXT, 'next'),
    (ON_HOLD, 'on_hold'),
    (RESOLVED, 'resolved'),
)

# resolutions
COMPLETED = 1
FAILED = 2
INCOMPLETE = 3

RESOLUTION_CHOICES = (
    (COMPLETED, 'completed'),
    (FAILED, 'failed'),
    (INCOMPLETE, 'incomplete'),
)
