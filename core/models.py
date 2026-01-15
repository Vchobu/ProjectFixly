"""Django models based on DB"""

from django.db import models


class Attachments(models.Model):
    attachment_id = models.AutoField(primary_key=True)
    ticket = models.ForeignKey('Tickets', models.DO_NOTHING)
    tenant_uploader = models.ForeignKey('Tenants', models.DO_NOTHING, blank=True, null=True)
    contractor_uploader = models.ForeignKey('Contractors', models.DO_NOTHING, blank=True, null=True)
    user_uploader = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    file_name = models.CharField(max_length=255)
    file_path = models.TextField()
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'attachments'


class Buildings(models.Model):
    building_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey('Owners', models.DO_NOTHING)
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'buildings'


class ContractorAssignments(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    ticket = models.ForeignKey('Tickets', models.DO_NOTHING)
    contractor = models.ForeignKey('Contractors', models.DO_NOTHING)
    created_at = models.DateTimeField(blank=True, null=True)
    declined_at = models.DateTimeField(blank=True, null=True)
    decline_reason = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'contractor_assignments'


class Contractors(models.Model):
    contractor_id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    password_hash = models.CharField(max_length=255, blank=True, null=True)
    specialties = models.TextField(blank=True, null=True)  # This field type is a guess.
    is_active = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'contractors'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class IssueCategories(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=100)
    sla_hours = models.IntegerField()
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'issue_categories'


class Messages(models.Model):
    message_id = models.AutoField(primary_key=True)
    ticket = models.ForeignKey('Tickets', models.DO_NOTHING)
    tenant_sender = models.ForeignKey('Tenants', models.DO_NOTHING, blank=True, null=True)
    contractor_sender = models.ForeignKey(Contractors, models.DO_NOTHING, blank=True, null=True)
    user_sender = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    message_text = models.TextField()
    is_internal = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'messages'


class OnCallRoster(models.Model):
    roster_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('Users', models.DO_NOTHING)
    backup_user = models.ForeignKey('Users', models.DO_NOTHING, related_name='oncallroster_backup_user_set', blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'on_call_roster'


class Owners(models.Model):
    owner_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.CharField(unique=True, max_length=255)
    phone = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'owners'


class Parts(models.Model):
    part_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    source = models.CharField(max_length=50, blank=True, null=True)
    supplier = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'parts'


class RecurringPatterns(models.Model):
    pattern_id = models.AutoField(primary_key=True)
    building = models.ForeignKey(Buildings, models.DO_NOTHING, blank=True, null=True)
    unit = models.ForeignKey('Units', models.DO_NOTHING, blank=True, null=True)
    category = models.ForeignKey(IssueCategories, models.DO_NOTHING, blank=True, null=True)
    pattern_description = models.TextField()
    occurrence_count = models.IntegerField(blank=True, null=True)
    first_occurrence = models.DateTimeField(blank=True, null=True)
    last_occurrence = models.DateTimeField(blank=True, null=True)
    resolution_notes = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'recurring_patterns'


class Tenants(models.Model):
    tenant_id = models.AutoField(primary_key=True)
    unit = models.ForeignKey('Units', models.DO_NOTHING)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True, null=True)
    password_hash = models.CharField(max_length=255, blank=True, null=True)
    has_keys = models.BooleanField(blank=True, null=True)
    access_notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tenants'


class TicketCategoryHistory(models.Model):
    history_id = models.AutoField(primary_key=True)
    ticket = models.ForeignKey('Tickets', models.DO_NOTHING)
    old_category = models.ForeignKey(IssueCategories, models.DO_NOTHING, blank=True, null=True)
    new_category = models.ForeignKey(IssueCategories, models.DO_NOTHING, related_name='ticketcategoryhistory_new_category_set')
    changed_by_user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ticket_category_history'


class TicketLaborCosts(models.Model):
    labor_id = models.AutoField(primary_key=True)
    ticket = models.ForeignKey('Tickets', models.DO_NOTHING)
    contractor = models.ForeignKey(Contractors, models.DO_NOTHING)
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ticket_labor_costs'


class TicketParts(models.Model):
    ticket_part_id = models.AutoField(primary_key=True)
    ticket = models.ForeignKey('Tickets', models.DO_NOTHING)
    part = models.ForeignKey(Parts, models.DO_NOTHING)
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ticket_parts'


class TicketStatusHistory(models.Model):
    history_id = models.AutoField(primary_key=True)
    ticket = models.ForeignKey('Tickets', models.DO_NOTHING)
    old_status = models.CharField(max_length=50, blank=True, null=True)
    new_status = models.CharField(max_length=50)
    changed_by_user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    changed_by_role = models.CharField(max_length=50, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ticket_status_history'


class Tickets(models.Model):
    ticket_id = models.AutoField(primary_key=True)
    unit = models.ForeignKey('Units', models.DO_NOTHING)
    tenant = models.ForeignKey(Tenants, models.DO_NOTHING)
    parent_ticket = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    category = models.ForeignKey(IssueCategories, models.DO_NOTHING, blank=True, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    assigned_contractor = models.ForeignKey(Contractors, models.DO_NOTHING, blank=True, null=True)
    assigned_at = models.DateTimeField(blank=True, null=True)
    scheduled_start = models.DateTimeField(blank=True, null=True)
    scheduled_end = models.DateTimeField(blank=True, null=True)
    actual_start = models.DateTimeField(blank=True, null=True)
    actual_end = models.DateTimeField(blank=True, null=True)
    access_windows = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tickets'


class Units(models.Model):
    unit_id = models.AutoField(primary_key=True)
    building = models.ForeignKey(Buildings, models.DO_NOTHING)
    unit_number = models.CharField(max_length=50)
    floor = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'units'
        unique_together = (('building', 'unit_number'),)


class Users(models.Model):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(unique=True, max_length=100)
    email = models.CharField(unique=True, max_length=255)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'
