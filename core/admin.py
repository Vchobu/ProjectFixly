# Add models to Django Admin

from django.contrib import admin
from .models import (
    Owners, Buildings, Units,
    Users, Tenants, Contractors,
    IssueCategories, Tickets,
    Messages, Attachments,
    Parts, TicketParts, TicketLaborCosts,
    ContractorAssignments, RecurringPatterns, OnCallRoster,
    TicketStatusHistory, TicketCategoryHistory
)

admin.site.register(Owners)
admin.site.register(Buildings)
admin.site.register(Units)
admin.site.register(Users)
admin.site.register(Tenants)
admin.site.register(Contractors)
admin.site.register(IssueCategories)
admin.site.register(Tickets)
admin.site.register(Messages)
admin.site.register(Attachments)
admin.site.register(Parts)
admin.site.register(TicketParts)
admin.site.register(TicketLaborCosts)
admin.site.register(ContractorAssignments)
admin.site.register(RecurringPatterns)
admin.site.register(OnCallRoster)
admin.site.register(TicketStatusHistory)
admin.site.register(TicketCategoryHistory)