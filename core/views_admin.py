"""Views for admin's UI"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from functools import wraps

from .models import (
    Tickets, Users, Contractors, Buildings,
    IssueCategories, ContractorAssignments, Attachments, Messages
)
from .sla import get_sla_hours, calculate_sla_status, add_sla_to_tickets


def admin_required(view_func):
    """Decorator to verify that the user is an admin"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('admin_login')
        try:
            user = Users.objects.get(user_id=user_id, role='admin', is_active=True)
            request.current_user = user
        except Users.DoesNotExist:
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = Users.objects.get(username=username, role='admin', is_active=True)
            if check_password(password, user.password_hash):
                request.session['user_id'] = user.user_id
                request.session['username'] = user.username
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Mot de passe incorrect')
        except Users.DoesNotExist:
            messages.error(request, 'Utilisateur non trouvé')

    return render(request, 'admin_ui/login.html')


def admin_logout(request):
    request.session.flush()
    return redirect('admin_login')

def get_chart_data():
    """Get data for dashboard: tickets/month, tickets categories, by status and contractors performance"""
    now = timezone.now()
    
    months = []
    created_counts = []
    resolved_counts = []
    
    for i in range(5, -1, -1):
        month_start = (now - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i > 0:
            month_end = (now - timedelta(days=30*(i-1))).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            month_end = now
        
        month_name = month_start.strftime('%b')
        months.append(month_name)
        
        created = Tickets.objects.filter(
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        created_counts.append(created)
        
        resolved = Tickets.objects.filter(
            resolved_at__gte=month_start,
            resolved_at__lt=month_end
        ).count()
        resolved_counts.append(resolved)
    
    # Tickets par catégorie
    category_stats = IssueCategories.objects.annotate(
        ticket_count=Count('tickets')
    ).filter(ticket_count__gt=0).order_by('-ticket_count')[:8]
    
    categories = [cat.name for cat in category_stats]
    category_values = [cat.ticket_count for cat in category_stats]
    
    status_counts = {
        'Ouverts': Tickets.objects.filter(status='open').count(),
        'En cours': Tickets.objects.filter(status='in_progress').count(),
        'Résolus': Tickets.objects.filter(status='resolved').count(),
        'Fermés': Tickets.objects.filter(status='closed').count(),
    }
    
    contractor_stats = Contractors.objects.filter(is_active=True).annotate(
        completed=Count('tickets', filter=Q(tickets__status__in=['resolved', 'closed'])),
        pending=Count('tickets', filter=Q(tickets__status__in=['open', 'in_progress']))
    ).order_by('-completed')[:6]
    
    contractors = [c.company_name[:15] for c in contractor_stats]
    contractor_completed = [c.completed for c in contractor_stats]
    contractor_pending = [c.pending for c in contractor_stats]
    
    return {
        'months': json.dumps(months),
        'created': json.dumps(created_counts),
        'resolved': json.dumps(resolved_counts),
        'categories': json.dumps(categories),
        'category_values': json.dumps(category_values),
        'status_labels': json.dumps(list(status_counts.keys())),
        'status_values': json.dumps(list(status_counts.values())),
        'contractors': json.dumps(contractors),
        'contractor_completed': json.dumps(contractor_completed),
        'contractor_pending': json.dumps(contractor_pending),
    }

def get_recent_activities():
    """Get recent data, like recently created or resolved tickets"""
    activities = []
    now = timezone.now()
    
    recent_created = Tickets.objects.order_by('-created_at')[:3]
    for ticket in recent_created:
        time_diff = now - ticket.created_at
        if time_diff.days > 0:
            time_str = f"Il y a {time_diff.days}j"
        elif time_diff.seconds > 3600:
            time_str = f"Il y a {time_diff.seconds // 3600}h"
        else:
            time_str = f"Il y a {time_diff.seconds // 60}min"
        
        activities.append({
            'type': 'created',
            'title': f"#{ticket.ticket_id} créé",
            'time': time_str
        })
    
    recent_resolved = Tickets.objects.filter(
        resolved_at__isnull=False
    ).order_by('-resolved_at')[:2]
    
    for ticket in recent_resolved:
        time_diff = now - ticket.resolved_at
        if time_diff.days > 0:
            time_str = f"Il y a {time_diff.days}j"
        elif time_diff.seconds > 3600:
            time_str = f"Il y a {time_diff.seconds // 3600}h"
        else:
            time_str = f"Il y a {time_diff.seconds // 60}min"
        
        activities.append({
            'type': 'resolved',
            'title': f"#{ticket.ticket_id} résolu",
            'time': time_str
        })
    
    return activities[:5]

@admin_required
def admin_dashboard(request):
    """Admin's dashboard. Opened/In progress/Not assigned tickers
     + recent activity and other statistics"""
    now = timezone.now()

    active_tickets = Tickets.objects.filter(
        status__in=['open', 'in_progress']
    ).select_related('unit', 'unit__building', 'category')

    sla_breached_tickets = []
    urgent_tickets = []

    for ticket in active_tickets:
        sla_hours = get_sla_hours(ticket)
        deadline = ticket.created_at + timedelta(hours=sla_hours)
        remaining = deadline - now
        remaining_hours = remaining.total_seconds() / 3600

        address = f"{ticket.unit.building.address}" if ticket.unit and ticket.unit.building else "N/A"

        if remaining_hours < 0:
            sla_breached_tickets.append({
                'ticket': ticket,
                'address': address,
                'hours_late': int(abs(remaining_hours)),
            })
        elif remaining_hours < (sla_hours * 0.25):
            urgent_tickets.append({
                'ticket': ticket,
                'address': address,
                'hours_remaining': int(remaining_hours),
            })

    stats = {
        'new': Tickets.objects.filter(status='open').count(),
        'in_progress': Tickets.objects.filter(status='in_progress').count(),
        'sla_breached': len(sla_breached_tickets),
        'resolved': Tickets.objects.filter(
            status__in=['resolved', 'closed'],
            resolved_at__gte=now - timedelta(days=30)
        ).count(),
        'total': Tickets.objects.count(),
        'active_contractors': Contractors.objects.filter(is_active=True).count(),
    }

    unassigned_tickets = Tickets.objects.filter(
        status='open',
        assigned_contractor__isnull=True
    ).select_related('category').order_by('created_at')[:10]

    contractors = Contractors.objects.filter(is_active=True)
    
    chart_data = get_chart_data()
    
    recent_activities = get_recent_activities()

    context = {
        'stats': stats,
        'sla_breached_tickets': sla_breached_tickets,
        'urgent_tickets': urgent_tickets,
        'unassigned_tickets': unassigned_tickets,
        'contractors': contractors,
        'user': request.current_user,
        'chart_data': chart_data,
        'recent_activities': recent_activities,
    }

    return render(request, 'admin_ui/dashboard.html', context)


@admin_required
def admin_tickets(request):
    status_filter = request.GET.get('status', '')
    sla_filter = request.GET.get('sla', '')
    search = request.GET.get('search', '')

    tickets = Tickets.objects.select_related(
        'unit', 'unit__building', 'tenant', 'category', 'assigned_contractor'
    ).order_by('-created_at')

    if status_filter:
        tickets = tickets.filter(status=status_filter)

    if search:
        tickets = tickets.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(ticket_id__icontains=search)
        )

    tickets = list(tickets)
    add_sla_to_tickets(tickets)

    if sla_filter == 'breached':
        tickets = [t for t in tickets if t.sla_status == 'breached']

    contractors = Contractors.objects.filter(is_active=True)

    context = {
        'tickets': tickets,
        'status_filter': status_filter,
        'sla_filter': sla_filter,
        'search': search,
        'contractors': contractors,
        'user': request.current_user,
        'stats': {
            'new': Tickets.objects.filter(status='open').count(),
        }
    }

    return render(request, 'admin_ui/tickets.html', context)


@admin_required
def admin_ticket_detail(request, ticket_id):
    ticket = get_object_or_404(
        Tickets.objects.select_related(
            'unit', 'unit__building', 'tenant', 'category', 'assigned_contractor'
        ),
        ticket_id=ticket_id
    )

    contractors = Contractors.objects.filter(is_active=True)

    photos = Attachments.objects.filter(ticket=ticket)
    
    ticket_messages = Messages.objects.filter(ticket=ticket).select_related(
        'tenant_sender', 'contractor_sender', 'user_sender'
    ).order_by('created_at')

    sla_status, sla_hours = calculate_sla_status(ticket)
    ticket.sla_status = sla_status
    ticket.sla_remaining = f"{int(sla_hours)}h" if sla_hours is not None else None

    context = {
        'ticket': ticket,
        'contractors': contractors,
        'photos': photos,
        'ticket_messages': ticket_messages,
        'user': request.current_user,
    }

    return render(request, 'admin_ui/ticket_detail.html', context)


@admin_required
def admin_add_message(request, ticket_id):
    if request.method == 'POST':
        ticket = get_object_or_404(Tickets, ticket_id=ticket_id)
        message_text = request.POST.get('message_text', '').strip()
        is_internal = request.POST.get('is_internal') == 'on'
        
        if message_text:
            Messages.objects.create(
                ticket=ticket,
                user_sender=request.current_user,
                message_text=message_text,
                is_internal=is_internal,
                created_at=timezone.now()
            )
            messages.success(request, 'Message envoyé avec succès!')
        else:
            messages.error(request, 'Le message ne peut pas être vide.')
    
    return redirect('admin_ticket_detail', ticket_id=ticket_id)


@admin_required
def assign_contractor(request, ticket_id):
    if request.method == 'POST':
        ticket = get_object_or_404(Tickets, ticket_id=ticket_id)
        contractor_id = request.POST.get('contractor_id')

        if contractor_id:
            contractor = get_object_or_404(Contractors, contractor_id=contractor_id)
            ticket.assigned_contractor = contractor
            ticket.assigned_at = timezone.now()
            if ticket.status == 'open':
                ticket.status = 'in_progress'
            ticket.save()

            ContractorAssignments.objects.create(
                ticket=ticket,
                contractor=contractor,
                status='pending',
                created_at=timezone.now()
            )

            messages.success(request, f'Ticket #{ticket_id} assigné à {contractor.company_name}')

        return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))

    return redirect('admin_dashboard')


@admin_required
def change_ticket_status(request, ticket_id):
    if request.method == 'POST':
        ticket = get_object_or_404(Tickets, ticket_id=ticket_id)
        new_status = request.POST.get('status')

        if new_status in ['open', 'in_progress', 'resolved', 'closed']:
            ticket.status = new_status
            if new_status == 'resolved':
                ticket.resolved_at = timezone.now()
            if new_status == 'closed':
                ticket.closed_at = timezone.now()
            ticket.save()
            messages.success(request, f'Statut mis à jour: {new_status}')

    return redirect('admin_ticket_detail', ticket_id=ticket_id)


@admin_required
def admin_contractors(request):
    contractors = Contractors.objects.annotate(
        active_tickets=Count('tickets', filter=Q(tickets__status__in=['open', 'in_progress'])),
        completed_tickets=Count('tickets', filter=Q(tickets__status__in=['resolved', 'closed']))
    ).order_by('company_name')

    context = {
        'contractors': contractors,
        'user': request.current_user,
        'stats': {'new': Tickets.objects.filter(status='open').count()}
    }

    return render(request, 'admin_ui/contractors.html', context)


@admin_required
def admin_buildings(request):
    buildings = Buildings.objects.annotate(
        units_count=Count('units'),
        open_tickets=Count('units__tickets', filter=Q(units__tickets__status='open'))
    ).select_related('owner').order_by('name')

    context = {
        'buildings': buildings,
        'user': request.current_user,
        'stats': {'new': Tickets.objects.filter(status='open').count()}
    }

    return render(request, 'admin_ui/buildings.html', context)


@admin_required
def admin_reports(request):
    category_stats = IssueCategories.objects.annotate(
        ticket_count=Count('tickets')
    ).order_by('-ticket_count')[:10]

    building_stats = Buildings.objects.annotate(
        ticket_count=Count('units__tickets')
    ).order_by('-ticket_count')[:10]

    contractor_stats = Contractors.objects.annotate(
        completed=Count('tickets', filter=Q(tickets__status__in=['resolved', 'closed']))
    ).order_by('-completed')[:10]

    context = {
        'category_stats': category_stats,
        'building_stats': building_stats,
        'contractor_stats': contractor_stats,
        'user': request.current_user,
        'stats': {'new': Tickets.objects.filter(status='open').count()}
    }

    return render(request, 'admin_ui/reports.html', context)


@admin_required
def api_ticket_stats(request):
    stats = {
        'new': Tickets.objects.filter(status='open').count(),
        'in_progress': Tickets.objects.filter(status='in_progress').count(),
        'waiting': Tickets.objects.filter(status='open', assigned_contractor__isnull=True).count(),
        'resolved': Tickets.objects.filter(status__in=['resolved', 'closed']).count(),
    }
    return JsonResponse(stats)


@admin_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        user = request.current_user

        if not check_password(current_password, user.password_hash):
            messages.error(request, 'Mot de passe actuel incorrect')
            return redirect('change_password')

        if new_password != confirm_password:
            messages.error(request, 'Les nouveaux mots de passe ne correspondent pas')
            return redirect('change_password')

        if len(new_password) < 6:
            messages.error(request, 'Le mot de passe doit contenir au moins 6 caractères')
            return redirect('change_password')

        user.password_hash = make_password(new_password)
        user.save()

        messages.success(request, 'Mot de passe modifié avec succès!')
        return redirect('admin_dashboard')

    return render(request, 'admin_ui/change_password.html', {'user': request.current_user})
