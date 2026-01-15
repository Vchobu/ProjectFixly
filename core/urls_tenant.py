# URLs which are connected to Tenants

from django.urls import path
from . import views_tenant

urlpatterns = [
    # Login/Logout
    path('login/', views_tenant.tenant_login, name='tenant_login'),
    path('logout/', views_tenant.tenant_logout, name='tenant_logout'),
    
    # Dashboard
    path('', views_tenant.tenant_dashboard, name='tenant_dashboard'),
    path('dashboard/', views_tenant.tenant_dashboard, name='tenant_dashboard'),
    
    # Tickets
    path('tickets/', views_tenant.tenant_tickets, name='tenant_tickets'),
    path('tickets/new/', views_tenant.tenant_create_ticket, name='tenant_create_ticket'),
    path('tickets/<int:ticket_id>/', views_tenant.tenant_ticket_detail, name='tenant_ticket_detail'),
    path('tickets/<int:ticket_id>/message/', views_tenant.tenant_add_message, name='tenant_add_message'),
    path('tickets/<int:ticket_id>/photo/', views_tenant.tenant_add_photo, name='tenant_add_photo'),
    
    # Profile
    path('profile/', views_tenant.tenant_profile, name='tenant_profile'),
    path('change-password/', views_tenant.tenant_change_password, name='tenant_change_password'),
]
