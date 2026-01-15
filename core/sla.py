"""SLA functions for views"""

from django.utils import timezone
from datetime import timedelta


SLA_HOURS = {
    'critical': 2,
    'high': 8,
    'medium': 24,
    'low': 72,
}


def get_sla_hours(ticket):
    if ticket.category and ticket.category.sla_hours:
        return ticket.category.sla_hours
    return SLA_HOURS.get(ticket.severity, 24)


def calculate_sla_status(ticket):
    if ticket.status in ['resolved', 'closed']:
        return 'ok', None

    sla_hours = get_sla_hours(ticket)
    deadline = ticket.created_at + timedelta(hours=sla_hours)
    now = timezone.now()
    remaining = deadline - now
    remaining_hours = remaining.total_seconds() / 3600

    if remaining_hours < 0:
        return 'breached', abs(remaining_hours)
    elif remaining_hours < (sla_hours * 0.25):
        return 'warning', remaining_hours
    else:
        return 'ok', remaining_hours


def add_sla_to_tickets(tickets):
    for ticket in tickets:
        status, hours = calculate_sla_status(ticket)
        ticket.sla_status = status
        ticket.sla_remaining = f"{int(hours)}h" if hours is not None else None
    return tickets
