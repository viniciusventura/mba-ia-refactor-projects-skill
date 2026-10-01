TASK_STATUSES = ('pending', 'in_progress', 'done', 'cancelled')
CLOSED_TASK_STATUSES = ('done', 'cancelled')
DEFAULT_TASK_STATUS = 'pending'

MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_THRESHOLD = 2          # prioridade <= 2 conta como "alta" no relatório do usuário
PRIORITY_LABELS = {1: 'critical', 2: 'high', 3: 'medium', 4: 'low', 5: 'minimal'}

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
DUE_DATE_FORMAT = '%Y-%m-%d'

USER_ROLES = ('user', 'admin', 'manager')
DEFAULT_ROLE = 'user'
ADMIN_ROLE = 'admin'
MIN_PASSWORD_LENGTH = 4
EMAIL_PATTERN = r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$'

DEFAULT_COLOR = '#000000'

RECENT_ACTIVITY_DAYS = 7
