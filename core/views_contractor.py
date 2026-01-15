"""Views for contractor's UI"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from functools import wraps

from .models import (
    Tickets, Contractors, ContractorAssignments,
    Messages, TicketStatusHistory, Attachments
)

def contractor_required(view_func):
    """Decorator to verify that the user is a contractor"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        contractor_id = request.session.get('contractor_id')
        if not contractor_id:
            return redirect('contractor_login')
        try:
            contractor = Contractors.objects.get(contractor_id=contractor_id, is_active=True)
            request.current_contractor = contractor
        except Contractors.DoesNotExist:
            request.session.flush()
            return redirect('contractor_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def contractor_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            contractor = Contractors.objects.get(email=email, is_active=True)
            if contractor.password_hash and check_password(password, contractor.password_hash):
                request.session['contractor_id'] = contractor.contractor_id
                request.session['contractor_name'] = contractor.company_name
                return redirect('contractor_dashboard')
            else:
                messages.error(request, 'Mot de passe incorrect')
        except Contractors.DoesNotExist:
            messages.error(request, 'Email non trouvé')
    
    return render(request, 'contractor_ui/login.html')


def contractor_logout(request):
    request.session.flush()
    return redirect('contractor_login')

@contractor_required
def contractor_dashboard(request):
    """ dashboard : current requests and details, tickets and other stats"""
    contractor = request.current_contractor
    
    assigned_tickets = Tickets.objects.filter(
        assigned_contractor=contractor
    ).select_related('category', 'unit', 'unit__building', 'tenant').order_by('-assigned_at')
    
    stats = {
        'total': assigned_tickets.count(),
        'pending': assigned_tickets.filter(status='open').count(),
        'in_progress': assigned_tickets.filter(status='in_progress').count(),
        'completed': assigned_tickets.filter(status__in=['resolved', 'closed']).count(),
    }
    
    pending_assignments = ContractorAssignments.objects.filter(
        contractor=contractor,
        status='pending'
    ).select_related('ticket', 'ticket__unit', 'ticket__unit__building')
    
    context = {
        'contractor': contractor,
        'assigned_tickets': assigned_tickets[:10],
        'pending_assignments': pending_assignments,
        'stats': stats,
    }
    
    return render(request, 'contractor_ui/dashboard.html', context)


@contractor_required
def contractor_jobs(request):
    contractor = request.current_contractor
    
    status_filter = request.GET.get('status', '')
    
    tickets = Tickets.objects.filter(
        assigned_contractor=contractor
    ).select_related('category', 'unit', 'unit__building', 'tenant').order_by('-assigned_at')
    
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    
    context = {
        'contractor': contractor,
        'tickets': tickets,
        'status_filter': status_filter,
    }
    
    return render(request, 'contractor_ui/jobs.html', context)


@contractor_required
def contractor_job_detail(request, ticket_id):
    contractor = request.current_contractor
    
    ticket = get_object_or_404(
        Tickets.objects.select_related(
            'category', 'unit', 'unit__building', 'tenant'
        ),
        ticket_id=ticket_id,
        assigned_contractor=contractor
    )
    
    ticket_messages = Messages.objects.filter(ticket=ticket).order_by('created_at')
    
    status_history = TicketStatusHistory.objects.filter(ticket=ticket).order_by('created_at')

    photos = Attachments.objects.filter(ticket=ticket)

    assignment = ContractorAssignments.objects.filter(
        ticket=ticket, contractor=contractor
    ).first()

    context = {
        'contractor': contractor,
        'ticket': ticket,
        'messages': ticket_messages,
        'status_history': status_history,
        'photos': photos,
        'assignment': assignment,
    }

    return render(request, 'contractor_ui/job_detail.html', context)


@contractor_required
def contractor_accept_job(request, ticket_id):
    contractor = request.current_contractor

    assignment = get_object_or_404(
        ContractorAssignments,
        ticket_id=ticket_id,
        contractor=contractor,
        status='pending'
    )

    assignment.status = 'accepted'
    assignment.save()

    ticket = assignment.ticket
    if ticket.status == 'open':
        old_status = ticket.status
        ticket.status = 'in_progress'
        ticket.save()

        TicketStatusHistory.objects.create(
            ticket=ticket,
            old_status=old_status,
            new_status='in_progress',
            changed_by_role='contractor',
            created_at=timezone.now()
        )

    messages.success(request, f'Job #{ticket_id} accepté!')
    return redirect('contractor_job_detail', ticket_id=ticket_id)


@contractor_required
def contractor_refuse_job(request, ticket_id):
    contractor = request.current_contractor

    assignment = get_object_or_404(
        ContractorAssignments,
        ticket_id=ticket_id,
        contractor=contractor,
        status='pending'
    )

    if request.method == 'POST':
        reason = request.POST.get('reason', '')

        assignment.status = 'declined'
        assignment.decline_reason = reason
        assignment.declined_at = timezone.now()
        assignment.save()

        ticket = assignment.ticket
        ticket.assigned_contractor = None
        ticket.assigned_at = None
        ticket.save()

        messages.warning(request, f'Job #{ticket_id} refusé. Le manager sera notifié.')
        return redirect('contractor_dashboard')

    return redirect('contractor_dashboard')

@contractor_required
def contractor_update_status(request, ticket_id):
    """Change status for ticket"""
    contractor = request.current_contractor

    ticket = get_object_or_404(
        Tickets,
        ticket_id=ticket_id,
        assigned_contractor=contractor
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status in ['in_progress', 'resolved']:
            old_status = ticket.status
            ticket.status = new_status

            if new_status == 'resolved':
                ticket.resolved_at = timezone.now()

            ticket.save()

            TicketStatusHistory.objects.create(
                ticket=ticket,
                old_status=old_status,
                new_status=new_status,
                changed_by_role='contractor',
                created_at=timezone.now()
            )

            messages.success(request, f'Statut mis à jour: {new_status}')

    return redirect('contractor_job_detail', ticket_id=ticket_id)


@contractor_required
def contractor_add_message(request, ticket_id):
    contractor = request.current_contractor

    ticket = get_object_or_404(
        Tickets,
        ticket_id=ticket_id,
        assigned_contractor=contractor
    )

    if request.method == 'POST':
        message_text = request.POST.get('message')

        if message_text:
            Messages.objects.create(
                ticket=ticket,
                contractor_sender=contractor,
                message_text=message_text,
                is_internal=False,
                created_at=timezone.now()
            )
            messages.success(request, 'Message envoyé!')

    return redirect('contractor_job_detail', ticket_id=ticket_id)


@contractor_required
def contractor_profile(request):
    contractor = request.current_contractor

    context = {
        'contractor': contractor,
    }

    return render(request, 'contractor_ui/profile.html', context)


@contractor_required
def contractor_change_password(request):
    contractor = request.current_contractor

    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not check_password(current_password, contractor.password_hash):
            messages.error(request, 'Mot de passe actuel incorrect')
            return redirect('contractor_change_password')

        if new_password != confirm_password:
            messages.error(request, 'Les mots de passe ne correspondent pas')
            return redirect('contractor_change_password')

        if len(new_password) < 6:
            messages.error(request, 'Minimum 6 caractères requis')
            return redirect('contractor_change_password')

        contractor.password_hash = make_password(new_password)
        contractor.save()

        messages.success(request, 'Mot de passe modifié!')
        return redirect('contractor_profile')

    context = {
        'contractor': contractor,
    }

    return render(request, 'contractor_ui/change_password.html', context)