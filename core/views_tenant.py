"""Views for tenant's UI"""

import os
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from django.conf import settings
from functools import wraps

from .models import (
    Tickets, Tenants, IssueCategories, Messages, Attachments
)
from .sla import calculate_sla_status, add_sla_to_tickets

def tenant_required(view_func):
    """Decorator to verify that the user is a tenant"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        tenant_id = request.session.get('tenant_id')
        if not tenant_id:
            return redirect('tenant_login')
        try:
            tenant = Tenants.objects.get(tenant_id=tenant_id, is_active=True)
            request.current_tenant = tenant
        except Tenants.DoesNotExist:
            request.session.flush()
            return redirect('tenant_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def tenant_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            tenant = Tenants.objects.get(email=email, is_active=True)
            if tenant.password_hash and check_password(password, tenant.password_hash):
                request.session['tenant_id'] = tenant.tenant_id
                request.session['tenant_name'] = f"{tenant.first_name} {tenant.last_name}"
                return redirect('tenant_dashboard')
            else:
                messages.error(request, 'Mot de passe incorrect')
        except Tenants.DoesNotExist:
            messages.error(request, 'Email non trouvé')
    
    return render(request, 'tenant_ui/login.html')


def tenant_logout(request):
    request.session.flush()
    return redirect('tenant_login')

@tenant_required
def tenant_dashboard(request):
    """Dashboard : their tickets, sort, browse the history and statistics"""
    tenant = request.current_tenant
    
    tickets = Tickets.objects.filter(tenant=tenant).select_related(
        'category', 'assigned_contractor'
    ).order_by('-created_at')
    
    stats = {
        'total': tickets.count(),
        'open': tickets.filter(status='open').count(),
        'in_progress': tickets.filter(status='in_progress').count(),
        'resolved': tickets.filter(status__in=['resolved', 'closed']).count(),
    }
    
    tickets_list = list(tickets[:10])
    add_sla_to_tickets(tickets_list)
    
    context = {
        'tenant': tenant,
        'tickets': tickets_list,
        'stats': stats,
    }
    
    return render(request, 'tenant_ui/dashboard.html', context)


@tenant_required
def tenant_tickets(request):
    tenant = request.current_tenant
    
    status_filter = request.GET.get('status', '')
    
    tickets = Tickets.objects.filter(tenant=tenant).select_related(
        'category', 'assigned_contractor', 'unit', 'unit__building'
    ).order_by('-created_at')
    
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    
    tickets_list = list(tickets)
    add_sla_to_tickets(tickets_list)
    
    context = {
        'tenant': tenant,
        'tickets': tickets_list,
        'status_filter': status_filter,
    }
    
    return render(request, 'tenant_ui/tickets.html', context)


@tenant_required
def tenant_ticket_detail(request, ticket_id):
    tenant = request.current_tenant
    
    ticket = get_object_or_404(
        Tickets.objects.select_related(
            'category', 'assigned_contractor', 'unit', 'unit__building'
        ),
        ticket_id=ticket_id,
        tenant=tenant
    )
    
    status, hours = calculate_sla_status(ticket)
    ticket.sla_status = status
    ticket.sla_remaining = f"{int(hours)}h" if hours else None

    ticket_messages = Messages.objects.filter(ticket=ticket).exclude(is_internal=True).order_by('created_at')
    
    photos = Attachments.objects.filter(ticket=ticket)
    
    context = {
        'tenant': tenant,
        'ticket': ticket,
        'messages': ticket_messages,
        'photos': photos,
    }
    
    return render(request, 'tenant_ui/ticket_detail.html', context)

def handle_uploaded_photos(request, ticket, tenant):
    """Upload photos attaached to a ticket"""
    photos = request.FILES.getlist('photos')
    
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'tickets', str(ticket.ticket_id))
    os.makedirs(upload_dir, exist_ok=True)
    
    for photo in photos[:5]:
        if photo.size > 5 * 1024 * 1024:
            continue
        if not photo.content_type.startswith('image/'):
            continue
        
        ext = os.path.splitext(photo.name)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(upload_dir, filename)
        
        with open(filepath, 'wb+') as destination:
            for chunk in photo.chunks():
                destination.write(chunk)
        
        relative_path = f"tickets/{ticket.ticket_id}/{filename}"
        
        Attachments.objects.create(
            ticket=ticket,
            tenant_uploader=tenant,
            file_name=photo.name,
            file_path=relative_path,
            created_at=timezone.now()
        )


def build_access_windows(request):
    days = request.POST.getlist('days')
    times = request.POST.getlist('times')
    access_notes = request.POST.get('access_notes', '').strip()
    
    parts = []
    
    if days:
        parts.append(f"Jours: {', '.join(days)}")
    
    if times:
        parts.append(f"Créneaux: {', '.join(times)}")
    
    if access_notes:
        parts.append(f"Notes: {access_notes}")
    
    return " | ".join(parts) if parts else None


@tenant_required
def tenant_create_ticket(request):
    tenant = request.current_tenant
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        severity = request.POST.get('severity', 'medium')
        
        # Construire access_windows
        access_windows = build_access_windows(request)
        
        ticket = Tickets.objects.create(
            tenant=tenant,
            unit=tenant.unit,
            title=title,
            description=description,
            category_id=category_id if category_id else None,
            severity=severity,
            status='open',
            access_windows=access_windows,
            created_at=timezone.now(),
            updated_at=timezone.now()
        )
        
        if request.FILES.getlist('photos'):
            handle_uploaded_photos(request, ticket, tenant)
        
        messages.success(request, f'Ticket #{ticket.ticket_id} créé avec succès!')
        return redirect('tenant_ticket_detail', ticket_id=ticket.ticket_id)
    
    categories = IssueCategories.objects.all()
    
    context = {
        'tenant': tenant,
        'categories': categories,
    }
    
    return render(request, 'tenant_ui/create_ticket.html', context)


@tenant_required
def tenant_add_message(request, ticket_id):
    tenant = request.current_tenant
    
    ticket = get_object_or_404(Tickets, ticket_id=ticket_id, tenant=tenant)
    
    if request.method == 'POST':
        message_text = request.POST.get('message')
        
        if message_text:
            Messages.objects.create(
                ticket=ticket,
                tenant_sender=tenant,
                message_text=message_text,
                is_internal=False,
                created_at=timezone.now()
            )
            messages.success(request, 'Message envoyé!')
    
    return redirect('tenant_ticket_detail', ticket_id=ticket_id)


@tenant_required
def tenant_add_photo(request, ticket_id):
    tenant = request.current_tenant
    
    ticket = get_object_or_404(Tickets, ticket_id=ticket_id, tenant=tenant)
    
    if request.method == 'POST' and request.FILES.getlist('photos'):
        handle_uploaded_photos(request, ticket, tenant)
        messages.success(request, 'Photo(s) ajoutée(s)!')
    
    return redirect('tenant_ticket_detail', ticket_id=ticket_id)


@tenant_required
def tenant_profile(request):
    tenant = request.current_tenant
    
    context = {
        'tenant': tenant,
    }
    
    return render(request, 'tenant_ui/profile.html', context)


@tenant_required
def tenant_change_password(request):
    tenant = request.current_tenant
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not check_password(current_password, tenant.password_hash):
            messages.error(request, 'Mot de passe actuel incorrect')
            return redirect('tenant_change_password')
        
        if new_password != confirm_password:
            messages.error(request, 'Les mots de passe ne correspondent pas')
            return redirect('tenant_change_password')
        
        if len(new_password) < 6:
            messages.error(request, 'Minimum 6 caractères requis')
            return redirect('tenant_change_password')
        
        tenant.password_hash = make_password(new_password)
        tenant.save()
        
        messages.success(request, 'Mot de passe modifié!')
        return redirect('tenant_profile')
    
    context = {
        'tenant': tenant,
    }
    
    return render(request, 'tenant_ui/change_password.html', context)
