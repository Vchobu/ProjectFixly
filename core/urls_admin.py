# URLs which are connected to Admin

from django.urls import path
from . import views_admin

urlpatterns = [
    # Login/Logout
    path('login/', views_admin.admin_login, name='admin_login'),
    path('logout/', views_admin.admin_logout, name='admin_logout'),
    
    # Dashboard
    path('', views_admin.admin_dashboard, name='admin_dashboard'),
    path('dashboard/', views_admin.admin_dashboard, name='admin_dashboard'),
    
    # Tickets
    path('tickets/', views_admin.admin_tickets, name='admin_tickets'),
    path('tickets/<int:ticket_id>/', views_admin.admin_ticket_detail, name='admin_ticket_detail'),
    path('tickets/<int:ticket_id>/assign/', views_admin.assign_contractor, name='assign_contractor'),
    path('tickets/<int:ticket_id>/status/', views_admin.change_ticket_status, name='change_ticket_status'),
    path('tickets/<int:ticket_id>/message/', views_admin.admin_add_message, name='admin_add_message'),
    
    # Contractors
    path('contractors/', views_admin.admin_contractors, name='admin_contractors'),
    
    # Buildings
    path('buildings/', views_admin.admin_buildings, name='admin_buildings'),
    
    # Reports
    path('reports/', views_admin.admin_reports, name='admin_reports'),
    
    # API
    path('api/stats/', views_admin.api_ticket_stats, name='api_ticket_stats'),
    
    # Profile
    path('change-password/', views_admin.change_password, name='change_password'),
]
