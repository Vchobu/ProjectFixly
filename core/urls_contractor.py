# URLs which are connected to Contractors

from django.urls import path
from . import views_contractor

urlpatterns = [
    # Login/Logout
    path('login/', views_contractor.contractor_login, name='contractor_login'),
    path('logout/', views_contractor.contractor_logout, name='contractor_logout'),
    
    # Dashboard
    path('', views_contractor.contractor_dashboard, name='contractor_dashboard'),
    path('dashboard/', views_contractor.contractor_dashboard, name='contractor_dashboard'),
    
    # Jobs
    path('jobs/', views_contractor.contractor_jobs, name='contractor_jobs'),
    path('jobs/<int:ticket_id>/', views_contractor.contractor_job_detail, name='contractor_job_detail'),
    path('jobs/<int:ticket_id>/accept/', views_contractor.contractor_accept_job, name='contractor_accept_job'),
    path('jobs/<int:ticket_id>/refuse/', views_contractor.contractor_refuse_job, name='contractor_refuse_job'),
    path('jobs/<int:ticket_id>/status/', views_contractor.contractor_update_status, name='contractor_update_status'),
    path('jobs/<int:ticket_id>/message/', views_contractor.contractor_add_message, name='contractor_add_message'),
    
    # Profile
    path('profile/', views_contractor.contractor_profile, name='contractor_profile'),
    path('change-password/', views_contractor.contractor_change_password, name='contractor_change_password'),
]
