"""Relatórios são a visão histórica: incluem usuários e tasks removidos (soft delete)."""
from datetime import timedelta

from flask import jsonify

from middlewares.error_handler import NotFoundError
from models.category import Category
from models.task import Task
from models.user import User
from utils.constants import HIGH_PRIORITY_THRESHOLD, PRIORITY_LABELS, RECENT_ACTIVITY_DAYS, TASK_STATUSES
from utils.helpers import calculate_percentage
from utils.time import utc_now


def summary_report():
    now = utc_now()
    by_status = Task.count_by_status(include_deleted=True)
    by_priority = Task.count_by_priority(include_deleted=True)
    all_tasks = Task.all_tasks(include_deleted=True)
    overdue_tasks = [task for task in all_tasks if task.is_overdue(now)]
    since = now - timedelta(days=RECENT_ACTIVITY_DAYS)

    totals_by_user = Task.count_by_user(include_deleted=True)
    done_by_user = Task.count_done_by_user(include_deleted=True)
    user_productivity = []
    for user in User.all_users():
        total = totals_by_user.get(user.id, 0)
        completed = done_by_user.get(user.id, 0)
        user_productivity.append({
            'user_id': user.id,
            'user_name': user.name,
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': calculate_percentage(completed, total),
        })

    report = {
        'generated_at': str(now),
        'overview': {
            'total_tasks': len(all_tasks),
            'total_users': len(user_productivity),
            'total_categories': Category.count_all(),
        },
        'tasks_by_status': {status: by_status.get(status, 0) for status in TASK_STATUSES},
        'tasks_by_priority': {label: by_priority.get(priority, 0) for priority, label in PRIORITY_LABELS.items()},
        'overdue': {
            'count': len(overdue_tasks),
            'tasks': [{
                'id': task.id,
                'title': task.title,
                'due_date': str(task.due_date),
                'days_overdue': task.days_overdue(now),
            } for task in overdue_tasks],
        },
        'recent_activity': {
            'tasks_created_last_7_days': Task.count_created_since(since, include_deleted=True),
            'tasks_completed_last_7_days': Task.count_completed_since(since, include_deleted=True),
        },
        'user_productivity': user_productivity,
    }
    return jsonify(report), 200


def user_report(user_id):
    user = User.get_including_deleted(user_id)
    if user is None:
        raise NotFoundError('Usuário não encontrado')

    tasks = Task.all_tasks(include_deleted=True, user_id=user_id)
    now = utc_now()
    counts = {status: 0 for status in TASK_STATUSES}
    for task in tasks:
        if task.status in counts:
            counts[task.status] += 1
    total = len(tasks)

    report = {
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
        },
        'statistics': {
            'total_tasks': total,
            'done': counts['done'],
            'pending': counts['pending'],
            'in_progress': counts['in_progress'],
            'cancelled': counts['cancelled'],
            'overdue': sum(1 for task in tasks if task.is_overdue(now)),
            'high_priority': sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_THRESHOLD),
            'completion_rate': calculate_percentage(counts['done'], total),
        },
    }
    return jsonify(report), 200
