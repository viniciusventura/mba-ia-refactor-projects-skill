from datetime import timedelta

from flask import jsonify

from middlewares.error_handler import NotFoundError
from models.category import Category
from models.task import Task
from models.user import User
from utils.constants import HIGH_PRIORITY_THRESHOLD, PRIORITY_LABELS, RECENT_ACTIVITY_DAYS, TASK_STATUSES
from utils.time import utc_now

# Relatórios são leituras históricas: incluem tasks, usuários e categorias removidos (soft delete).
HISTORICAL = {'include_deleted': True}


def summary_report():
    now = utc_now()
    by_status = Task.count_by(Task.status, **HISTORICAL)
    by_priority = Task.count_by(Task.priority, **HISTORICAL)

    overdue_tasks = [
        {'id': task.id, 'title': task.title, 'due_date': str(task.due_date), 'days_overdue': (now - task.due_date).days}
        for task in Task.list_all(**HISTORICAL) if task.is_overdue(now)
    ]

    since = now - timedelta(days=RECENT_ACTIVITY_DAYS)
    totals_by_user = Task.totals_by_user(**HISTORICAL)
    user_stats = []
    for user in User.list_all():
        total, completed = totals_by_user.get(user.id, (0, 0))
        user_stats.append({
            'user_id': user.id,
            'user_name': user.name,
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': Task.completion_rate(completed, total),
        })

    report = {
        'generated_at': str(now),
        'overview': {
            'total_tasks': Task.count(**HISTORICAL),
            'total_users': User.count(**HISTORICAL),
            'total_categories': Category.count(**HISTORICAL),
        },
        'tasks_by_status': {status: by_status.get(status, 0) for status in TASK_STATUSES},
        'tasks_by_priority': {label: by_priority.get(priority, 0) for priority, label in PRIORITY_LABELS.items()},
        'overdue': {'count': len(overdue_tasks), 'tasks': overdue_tasks},
        'recent_activity': {
            'tasks_created_last_7_days': Task.count_created_since(since, **HISTORICAL),
            'tasks_completed_last_7_days': Task.count_done_since(since, **HISTORICAL),
        },
        'user_productivity': user_stats,
    }
    return jsonify(report), 200


def user_report(user_id):
    user = User.find_by_id(user_id)
    if user is None:
        raise NotFoundError('Usuário não encontrado')

    tasks = Task.list_by_user(user_id, **HISTORICAL)
    now = utc_now()
    total = len(tasks)
    by_status = {status: sum(1 for task in tasks if task.status == status) for status in TASK_STATUSES}

    report = {
        'user': {'id': user.id, 'name': user.name, 'email': user.email},
        'statistics': {
            'total_tasks': total,
            'done': by_status['done'],
            'pending': by_status['pending'],
            'in_progress': by_status['in_progress'],
            'cancelled': by_status['cancelled'],
            'overdue': sum(1 for task in tasks if task.is_overdue(now)),
            'high_priority': sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_THRESHOLD),
            'completion_rate': Task.completion_rate(by_status['done'], total),
        },
    }
    return jsonify(report), 200
