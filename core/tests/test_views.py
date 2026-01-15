"""Unit tests """

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from core.models import (
    Users, Owners, Buildings, Units, Tenants, Tickets,
    Contractors, IssueCategories
)
from core.sla import get_sla_hours, calculate_sla_status, add_sla_to_tickets

class SLAFunctionsTests(TestCase):

    def setUp(self):
        self.now = timezone.now()
        self.owner = Owners.objects.create(
            name="Test Owner",
            email="owner@test.ch",
            created_at=self.now
        )
        self.building = Buildings.objects.create(
            owner=self.owner,
            name="Building Test",
            address="123 Test Street",
            created_at=self.now
        )
        self.unit = Units.objects.create(
            building=self.building,
            unit_number="101",
            created_at=self.now
        )
        self.tenant = Tenants.objects.create(
            unit=self.unit,
            first_name="Jean",
            last_name="Test",
            email="tenant@test.ch",
            has_keys=False,
            is_active=True,
            created_at=self.now
        )
        self.category = IssueCategories.objects.create(
            name="Test Category",
            sla_hours=24
        )

    def test_get_sla_hours_with_category(self):
        ticket = Tickets.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            category=self.category,
            title="Test",
            description="Test",
            severity="medium",
            status="open",
            created_at=self.now,
            updated_at=self.now
        )
        self.assertEqual(get_sla_hours(ticket), 24)

    def test_get_sla_hours_by_severity(self):
        severities = [('critical', 2), ('high', 8), ('medium', 24), ('low', 72)]
        for severity, expected_hours in severities:
            ticket = Tickets.objects.create(
                tenant=self.tenant,
                unit=self.unit,
                title="Test",
                description="Test",
                severity=severity,
                status="open",
                created_at=self.now,
                updated_at=self.now
            )
            self.assertEqual(get_sla_hours(ticket), expected_hours)

    def test_calculate_sla_status_ok(self):
        ticket = Tickets.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            category=self.category,
            title="Test",
            description="Test",
            severity="medium",
            status="open",
            created_at=self.now,
            updated_at=self.now
        )
        status, hours = calculate_sla_status(ticket)
        self.assertEqual(status, 'ok')

    def test_calculate_sla_status_warning(self):
        ticket = Tickets.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            category=self.category,
            title="Test",
            description="Test",
            severity="medium",
            status="open",
            created_at=self.now - timedelta(hours=20),
            updated_at=self.now
        )
        status, hours = calculate_sla_status(ticket)
        self.assertEqual(status, 'warning')

    def test_calculate_sla_status_breached(self):
        ticket = Tickets.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            category=self.category,
            title="Test",
            description="Test",
            severity="medium",
            status="open",
            created_at=self.now - timedelta(hours=30),
            updated_at=self.now
        )
        status, hours = calculate_sla_status(ticket)
        self.assertEqual(status, 'breached')

    def test_calculate_sla_status_resolved(self):
        ticket = Tickets.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            category=self.category,
            title="Test",
            description="Test",
            severity="medium",
            status="resolved",
            created_at=self.now - timedelta(hours=10),
            updated_at=self.now,
            resolved_at=self.now
        )
        status, hours = calculate_sla_status(ticket)
        self.assertEqual(status, 'ok')

    def test_add_sla_to_tickets(self):
        ticket = Tickets.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            category=self.category,
            title="Test",
            description="Test",
            severity="medium",
            status="open",
            created_at=self.now,
            updated_at=self.now
        )
        tickets = [ticket]
        add_sla_to_tickets(tickets)
        self.assertTrue(hasattr(tickets[0], 'sla_status'))


class AdminAuthTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.now = timezone.now()
        from django.contrib.auth.hashers import make_password
        self.admin = Users.objects.create(
            username="admin",
            email="admin@test.ch",
            password_hash=make_password("password123"),
            role="admin",
            is_active=True,
            created_at=self.now
        )

    def test_admin_login_page(self):
        response = self.client.get(reverse('admin_login'))
        self.assertEqual(response.status_code, 200)

    def test_admin_login_success(self):
        response = self.client.post(reverse('admin_login'), {
            'username': 'admin',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)

    def test_admin_login_wrong_password(self):
        response = self.client.post(reverse('admin_login'), {
            'username': 'admin',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)

    def test_admin_logout(self):
        session = self.client.session
        session['user_id'] = self.admin.user_id
        session.save()
        response = self.client.get(reverse('admin_logout'))
        self.assertEqual(response.status_code, 302)

    def test_admin_required_decorator(self):
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        
        session = self.client.session
        session['user_id'] = self.admin.user_id
        session.save()
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)


class AdminViewsTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.now = timezone.now()
        from django.contrib.auth.hashers import make_password
        self.admin = Users.objects.create(
            username="admin",
            email="admin@test.ch",
            password_hash=make_password("password123"),
            role="admin",
            is_active=True,
            created_at=self.now
        )
        self.owner = Owners.objects.create(
            name="Owner",
            email="owner@test.ch",
            created_at=self.now
        )
        self.building = Buildings.objects.create(
            owner=self.owner,
            name="Building",
            address="Address",
            created_at=self.now
        )
        self.unit = Units.objects.create(
            building=self.building,
            unit_number="101",
            created_at=self.now
        )
        self.tenant = Tenants.objects.create(
            unit=self.unit,
            first_name="Jean",
            last_name="Test",
            email="tenant@test.ch",
            has_keys=False,
            is_active=True,
            created_at=self.now
        )
        self.contractor = Contractors.objects.create(
            company_name="Test SA",
            contact_name="Contact",
            email="contractor@test.ch",
            phone="+41 00 000 00 00",
            specialties='{Plomberie}',
            is_active=True,
            created_at=self.now
        )
        self.ticket = Tickets.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            title="Test Ticket",
            description="Description",
            severity="medium",
            status="open",
            created_at=self.now,
            updated_at=self.now
        )
        session = self.client.session
        session['user_id'] = self.admin.user_id
        session.save()

    def test_admin_dashboard(self):
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_admin_tickets_list(self):
        response = self.client.get(reverse('admin_tickets'))
        self.assertEqual(response.status_code, 200)

    def test_admin_ticket_detail(self):
        response = self.client.get(
            reverse('admin_ticket_detail', args=[self.ticket.ticket_id])
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_contractors_list(self):
        response = self.client.get(reverse('admin_contractors'))
        self.assertEqual(response.status_code, 200)

    def test_admin_buildings_list(self):
        response = self.client.get(reverse('admin_buildings'))
        self.assertEqual(response.status_code, 200)

    def test_admin_reports(self):
        response = self.client.get(reverse('admin_reports'))
        self.assertEqual(response.status_code, 200)

    def test_assign_contractor(self):
        response = self.client.post(
            reverse('assign_contractor', args=[self.ticket.ticket_id]),
            {'contractor_id': self.contractor.contractor_id}
        )
        self.assertEqual(response.status_code, 302)

    def test_change_ticket_status(self):
        response = self.client.post(
            reverse('change_ticket_status', args=[self.ticket.ticket_id]),
            {'status': 'in_progress'}
        )
        self.assertEqual(response.status_code, 302)

    def test_admin_add_message(self):
        response = self.client.post(
            reverse('admin_add_message', args=[self.ticket.ticket_id]),
            {'message_text': 'Test message', 'is_internal': 'on'}
        )
        self.assertEqual(response.status_code, 302)

    def test_change_password(self):
        response = self.client.get(reverse('change_password'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.post(reverse('change_password'), {
            'current_password': 'password123',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        self.assertEqual(response.status_code, 302)

    def test_api_ticket_stats(self):
        response = self.client.get(reverse('api_ticket_stats'))
        self.assertEqual(response.status_code, 200)


class TenantAuthTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.now = timezone.now()
        from django.contrib.auth.hashers import make_password
        self.owner = Owners.objects.create(
            name="Owner",
            email="owner@test.ch",
            created_at=self.now
        )
        self.building = Buildings.objects.create(
            owner=self.owner,
            name="Building",
            address="Address",
            created_at=self.now
        )
        self.unit = Units.objects.create(
            building=self.building,
            unit_number="101",
            created_at=self.now
        )
        self.tenant = Tenants.objects.create(
            unit=self.unit,
            first_name="Jean",
            last_name="Test",
            email="tenant@test.ch",
            password_hash=make_password("password123"),
            has_keys=False,
            is_active=True,
            created_at=self.now
        )

    def test_tenant_login_page(self):
        response = self.client.get(reverse('tenant_login'))
        self.assertEqual(response.status_code, 200)

    def test_tenant_login_success(self):
        response = self.client.post(reverse('tenant_login'), {
            'email': 'tenant@test.ch',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)

    def test_tenant_login_wrong_password(self):
        response = self.client.post(reverse('tenant_login'), {
            'email': 'tenant@test.ch',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)

    def test_tenant_dashboard_requires_login(self):
        response = self.client.get(reverse('tenant_dashboard'))
        self.assertEqual(response.status_code, 302)


class TenantViewsTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.now = timezone.now()
        from django.contrib.auth.hashers import make_password
        self.owner = Owners.objects.create(
            name="Owner",
            email="owner@test.ch",
            created_at=self.now
        )
        self.building = Buildings.objects.create(
            owner=self.owner,
            name="Building",
            address="Address",
            created_at=self.now
        )
        self.unit = Units.objects.create(
            building=self.building,
            unit_number="101",
            created_at=self.now
        )
        self.tenant = Tenants.objects.create(
            unit=self.unit,
            first_name="Jean",
            last_name="Test",
            email="tenant@test.ch",
            password_hash=make_password("password123"),
            has_keys=False,
            is_active=True,
            created_at=self.now
        )
        self.category = IssueCategories.objects.create(
            name="Plomberie",
            sla_hours=24
        )
        session = self.client.session
        session['tenant_id'] = self.tenant.tenant_id
        session.save()

    def test_tenant_dashboard(self):
        response = self.client.get(reverse('tenant_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_tenant_tickets_list(self):
        response = self.client.get(reverse('tenant_tickets'))
        self.assertEqual(response.status_code, 200)

    def test_tenant_create_ticket(self):
        response = self.client.get(reverse('tenant_create_ticket'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.post(reverse('tenant_create_ticket'), {
            'title': 'Nouveau ticket',
            'description': 'Description du problème',
            'category': self.category.category_id,
            'severity': 'medium'
        })
        self.assertIn(response.status_code, [200, 302])

    def test_tenant_profile(self):
        response = self.client.get(reverse('tenant_profile'))
        self.assertEqual(response.status_code, 200)


class ContractorAuthTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.now = timezone.now()
        from django.contrib.auth.hashers import make_password
        self.contractor = Contractors.objects.create(
            company_name="Test SA",
            contact_name="Jean Test",
            email="contractor@test.ch",
            phone="+41 00 000 00 00",
            password_hash=make_password("password123"),
            specialties='{Plomberie}',
            is_active=True,
            created_at=self.now
        )

    def test_contractor_login_page(self):
        response = self.client.get(reverse('contractor_login'))
        self.assertEqual(response.status_code, 200)

    def test_contractor_login_success(self):
        response = self.client.post(reverse('contractor_login'), {
            'email': 'contractor@test.ch',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)

    def test_contractor_dashboard_requires_login(self):
        response = self.client.get(reverse('contractor_dashboard'))
        self.assertEqual(response.status_code, 302)


class ContractorViewsTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.now = timezone.now()
        from django.contrib.auth.hashers import make_password
        self.contractor = Contractors.objects.create(
            company_name="Test SA",
            contact_name="Jean Test",
            email="contractor@test.ch",
            phone="+41 00 000 00 00",
            password_hash=make_password("password123"),
            specialties='{Plomberie}',
            is_active=True,
            created_at=self.now
        )
        session = self.client.session
        session['contractor_id'] = self.contractor.contractor_id
        session.save()

    def test_contractor_dashboard(self):
        response = self.client.get(reverse('contractor_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_contractor_jobs_list(self):
        response = self.client.get(reverse('contractor_jobs'))
        self.assertEqual(response.status_code, 200)

    def test_contractor_profile(self):
        response = self.client.get(reverse('contractor_profile'))
        self.assertEqual(response.status_code, 200)


class EdgeCasesTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.now = timezone.now()
        from django.contrib.auth.hashers import make_password
        self.admin = Users.objects.create(
            username="admin",
            email="admin@test.ch",
            password_hash=make_password("password123"),
            role="admin",
            is_active=True,
            created_at=self.now
        )
        self.owner = Owners.objects.create(
            name="Owner",
            email="owner@test.ch",
            created_at=self.now
        )
        self.building = Buildings.objects.create(
            owner=self.owner,
            name="Building",
            address="Address",
            created_at=self.now
        )
        self.unit = Units.objects.create(
            building=self.building,
            unit_number="101",
            created_at=self.now
        )
        self.tenant = Tenants.objects.create(
            unit=self.unit,
            first_name="Jean",
            last_name="Test",
            email="tenant@test.ch",
            has_keys=False,
            is_active=True,
            created_at=self.now
        )
        self.ticket = Tickets.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            title="Test",
            description="Test",
            severity="medium",
            status="open",
            created_at=self.now,
            updated_at=self.now
        )
        session = self.client.session
        session['user_id'] = self.admin.user_id
        session.save()

    def test_ticket_detail_not_found(self):
        response = self.client.get(reverse('admin_ticket_detail', args=[99999]))
        self.assertIn(response.status_code, [302, 404])

    def test_assign_contractor_no_id(self):
        response = self.client.post(
            reverse('assign_contractor', args=[self.ticket.ticket_id]),
            {}
        )
        self.assertEqual(response.status_code, 302)

    def test_change_status_invalid(self):
        response = self.client.post(
            reverse('change_ticket_status', args=[self.ticket.ticket_id]),
            {'status': 'invalid_status'}
        )
        self.assertIn(response.status_code, [200, 302])
