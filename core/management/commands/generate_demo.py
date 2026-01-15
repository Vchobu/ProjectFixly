# Management Command to generate data for demo

import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password

from core.models import (
    Owners, Buildings, Units, Tenants, Contractors,
    IssueCategories, Tickets, Messages, Users, ContractorAssignments
)


class Command(BaseCommand):
    help = 'Génère des données de démo pour Fixly'

    def handle(self, *args, **options):
        self.stdout.write("Génération des données de démo...")

        # 1. Problems ccategories
        categories_data = [
            {"name": "Plomberie", "sla_hours": 24, "description": "Fuites, canalisations, robinets"},
            {"name": "Électricité", "sla_hours": 12, "description": "Pannes, prises, éclairage"},
            {"name": "Chauffage", "sla_hours": 8, "description": "Radiateurs, chaudière, thermostat"},
            {"name": "Serrurerie", "sla_hours": 4, "description": "Portes, serrures, clés"},
            {"name": "Vitrage", "sla_hours": 48, "description": "Fenêtres, double vitrage"},
            {"name": "Peinture", "sla_hours": 72, "description": "Murs, plafonds, retouches"},
            {"name": "Menuiserie", "sla_hours": 48, "description": "Portes, placards, parquet"},
            {"name": "Nuisibles", "sla_hours": 24, "description": "Insectes, rongeurs"},
        ]

        self.stdout.write("\nCatégories...")
        categories = {}
        for cat_data in categories_data:
            cat, created = IssueCategories.objects.get_or_create(
                name=cat_data["name"],
                defaults={"sla_hours": cat_data["sla_hours"], "description": cat_data["description"]}
            )
            categories[cat_data["name"]] = cat
            status = "[+]" if created else "[=]"
            self.stdout.write(f"  {status} {cat.name}")

        # 2. Owner

        self.stdout.write("\nPropriétaire...")
        owner, created = Owners.objects.get_or_create(
            email="proprietaire@fixly.ch",
            defaults={
                "name": "Régie Immobilière Genève SA",
                "phone": "+41 22 123 45 67",
                "created_at": timezone.now()
            }
        )
        status = "[+]" if created else "[=]"
        self.stdout.write(f"  {status} {owner.name}")

        # 3. Buildings

        buildings_data = [
            {"name": "Résidence du Lac", "address": "15 Quai du Mont-Blanc", "city": "Genève", "postal_code": "1201"},
            {"name": "Les Jardins de Champel", "address": "42 Avenue de Champel", "city": "Genève", "postal_code": "1206"},
            {"name": "Le Panorama", "address": "8 Rue de Lausanne", "city": "Genève", "postal_code": "1202"},
        ]

        self.stdout.write("\nImmeubles...")
        buildings = []
        for b_data in buildings_data:
            building, created = Buildings.objects.get_or_create(
                name=b_data["name"],
                defaults={
                    "owner": owner,
                    "address": b_data["address"],
                    "city": b_data["city"],
                    "postal_code": b_data["postal_code"],
                    "created_at": timezone.now()
                }
            )
            buildings.append(building)
            status = "[+]" if created else "[=]"
            self.stdout.write(f"  {status} {building.name}")


        # 4. Apartments

        self.stdout.write("\nUnités...")
        units = []
        for building in buildings:
            for floor in range(1, 5):
                for apt in ['A', 'B']:
                    unit_number = f"{floor}{apt}"
                    unit, created = Units.objects.get_or_create(
                        building=building,
                        unit_number=unit_number,
                        defaults={"floor": floor, "created_at": timezone.now()}
                    )
                    units.append(unit)
                    if created:
                        self.stdout.write(f"  [+] {building.name} - Apt {unit_number}")

        # 5. Tenants

        tenants_data = [
            {"first_name": "Marie", "last_name": "Dupont", "phone": "+41 79 123 45 01"},
            {"first_name": "Pierre", "last_name": "Martin", "phone": "+41 79 123 45 02"},
            {"first_name": "Sophie", "last_name": "Bernard", "phone": "+41 79 123 45 03"},
            {"first_name": "Jean", "last_name": "Dubois", "phone": "+41 79 123 45 04"},
            {"first_name": "Claire", "last_name": "Leroy", "phone": "+41 79 123 45 05"},
            {"first_name": "Thomas", "last_name": "Moreau", "phone": "+41 79 123 45 06"},
            {"first_name": "Emma", "last_name": "Petit", "phone": "+41 79 123 45 07"},
            {"first_name": "Lucas", "last_name": "Roux", "phone": "+41 79 123 45 08"},
        ]

        self.stdout.write("\nLocataires...")
        tenants = []
        password_hash = make_password("admin")

        for i, t_data in enumerate(tenants_data):
            if i < len(units):
                email = f"{t_data['first_name'].lower()}.{t_data['last_name'].lower()}@email.com"
                tenant, created = Tenants.objects.get_or_create(
                    email=email,
                    defaults={
                        "unit": units[i],
                        "first_name": t_data["first_name"],
                        "last_name": t_data["last_name"],
                        "phone": t_data["phone"],
                        "password_hash": password_hash,
                        "is_active": True,
                        "created_at": timezone.now()
                    }
                )
                tenants.append(tenant)
                status = "[+]" if created else "[=]"
                self.stdout.write(f"  {status} {tenant.first_name} {tenant.last_name} ({email})")

        # 6. Contractors
        
        contractors_data = [
            {"company_name": "Plomberie 1 SA", "contact_name": "Marc Fontaine", "specialties": "Plomberie", "phone": "+41 22 301 01 01"},
            {"company_name": "Plomberie 2 SA", "contact_name": "Jean Dupuis", "specialties": "Plomberie", "phone": "+41 22 301 02 02"},
            {"company_name": "Électricité 1 SA", "contact_name": "Julie Mercier", "specialties": "Électricité", "phone": "+41 22 302 01 01"},
            {"company_name": "Électricité 2 SA", "contact_name": "Paul Renard", "specialties": "Électricité", "phone": "+41 22 302 02 02"},
            {"company_name": "Chauffage 1 SA", "contact_name": "David Blanc", "specialties": "Chauffage", "phone": "+41 22 303 01 01"},
            {"company_name": "Serrurerie 1 SA", "contact_name": "Alain Rousseau", "specialties": "Serrurerie", "phone": "+41 22 304 01 01"},
            {"company_name": "Vitrage 1 SA", "contact_name": "Sophie Martin", "specialties": "Vitrage", "phone": "+41 22 305 01 01"},
            {"company_name": "Peinture 1 SA", "contact_name": "Pierre Morel", "specialties": "Peinture", "phone": "+41 22 306 01 01"},
            {"company_name": "Menuiserie 1 SA", "contact_name": "Claire Dubois", "specialties": "Menuiserie", "phone": "+41 22 307 01 01"},
            {"company_name": "Nuisibles 1 SA", "contact_name": "Thomas Leroy", "specialties": "Nuisibles", "phone": "+41 22 308 01 01"},
        ]

        self.stdout.write("\nContractors...")
        contractors = []
        for c_data in contractors_data:
            email = c_data["company_name"].lower().replace(" ", "").replace("é", "e")[:20] + "@contractor.ch"
            contractor, created = Contractors.objects.get_or_create(
                email=email,
                defaults={
                    "company_name": c_data["company_name"],
                    "contact_name": c_data["contact_name"],
                    "phone": c_data["phone"],
                    "password_hash": password_hash,
                    "specialties": c_data["specialties"],
                    "is_active": True,
                    "created_at": timezone.now()
                }
            )
            contractors.append(contractor)
            status = "[+]" if created else "[=]"
            self.stdout.write(f"  {status} {contractor.company_name}")

        # 7. Admin

        self.stdout.write("\nAdmin...")
        admin, created = Users.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@fixly.ch",
                "password_hash": make_password("admin"),
                "role": "admin",
                "is_active": True,
                "created_at": timezone.now()
            }
        )
        status = "[+]" if created else "[=]"
        self.stdout.write(f"  {status} admin (pwd: admin)")

        # 8. Tickets for demo
        
        tickets_data = [
            {
                "title": "Fuite d'eau importante sous l'évier",
                "description": "L'eau coule en permanence sous l'évier de la cuisine. Le sol est mouillé et ça risque d'abîmer le parquet. Urgent!",
                "category": "Plomberie",
                "severity": "critical",
                "status": "open",
                "days_ago": 3,
                "access_windows": "Jours: lundi, mardi, mercredi | Créneaux: matin (8h-12h) | Notes: Code entrée 1234"
            },
            {
                "title": "Plus de chauffage dans tout l'appartement",
                "description": "Depuis hier soir, plus aucun radiateur ne chauffe. Il fait très froid.",
                "category": "Chauffage",
                "severity": "critical",
                "status": "in_progress",
                "days_ago": 2,
                "assigned": True,
                "access_windows": "Jours: lundi, mardi, mercredi, jeudi, vendredi | Créneaux: matin (8h-12h), après-midi (14h-18h)"
            },
            {
                "title": "Panne électrique partielle - prises salon",
                "description": "Les prises du salon ne fonctionnent plus depuis ce matin.",
                "category": "Électricité",
                "severity": "high",
                "status": "open",
                "days_ago": 1,
                "access_windows": "Jours: mercredi, vendredi | Créneaux: soir (18h-20h)"
            },
            {
                "title": "Serrure de porte d'entrée difficile",
                "description": "La clé tourne difficilement dans la serrure.",
                "category": "Serrurerie",
                "severity": "medium",
                "status": "in_progress",
                "days_ago": 4,
                "assigned": True
            },
            {
                "title": "Robinet de douche qui goutte",
                "description": "Le robinet de la douche goutte en permanence.",
                "category": "Plomberie",
                "severity": "medium",
                "status": "in_progress",
                "days_ago": 5,
                "assigned": True
            },
            {
                "title": "Fenêtre du salon ne ferme plus correctement",
                "description": "La fenêtre ne se ferme plus hermétiquement.",
                "category": "Vitrage",
                "severity": "low",
                "status": "in_progress",
                "days_ago": 7,
                "assigned": True
            },
            {
                "title": "Ampoule grillée dans le couloir",
                "description": "L'ampoule du plafonnier a grillé.",
                "category": "Électricité",
                "severity": "low",
                "status": "resolved",
                "days_ago": 10,
                "resolved_days_ago": 2,
                "assigned": True
            },
            {
                "title": "Traces d'humidité au plafond",
                "description": "Des traces d'humidité sont apparues au plafond de la salle de bain.",
                "category": "Plomberie",
                "severity": "high",
                "status": "resolved",
                "days_ago": 14,
                "resolved_days_ago": 5,
                "assigned": True
            },
            {
                "title": "Porte de placard qui grince",
                "description": "La porte du placard grince fortement.",
                "category": "Menuiserie",
                "severity": "low",
                "status": "closed",
                "days_ago": 20,
                "resolved_days_ago": 12,
                "assigned": True
            },
            {
                "title": "Interphone ne fonctionne plus",
                "description": "L'interphone ne sonne plus.",
                "category": "Électricité",
                "severity": "medium",
                "status": "open",
                "days_ago": 0
            },
            {
                "title": "Tache au plafond après infiltration",
                "description": "Il reste une tache au plafond qui nécessite un rafraîchissement.",
                "category": "Peinture",
                "severity": "low",
                "status": "open",
                "days_ago": 2
            },
            {
                "title": "Cafards aperçus dans la cuisine",
                "description": "J'ai aperçu plusieurs cafards dans la cuisine.",
                "category": "Nuisibles",
                "severity": "high",
                "status": "in_progress",
                "days_ago": 1,
                "assigned": True,
                "access_windows": "Jours: lundi, mardi, mercredi, jeudi, vendredi | Créneaux: matin (8h-12h), après-midi (14h-18h)"
            },
            {
                "title": "Volet roulant bloqué",
                "description": "Le volet roulant de la chambre est bloqué en position fermée.",
                "category": "Menuiserie",
                "severity": "medium",
                "status": "open",
                "days_ago": 1
            },
            {
                "title": "Chasse d'eau qui coule en permanence",
                "description": "La chasse d'eau des toilettes coule sans arrêt.",
                "category": "Plomberie",
                "severity": "medium",
                "status": "resolved",
                "days_ago": 8,
                "resolved_days_ago": 3,
                "assigned": True
            },
            {
                "title": "Prise électrique fondue",
                "description": "Une prise électrique dans la cuisine semble avoir fondu.",
                "category": "Électricité",
                "severity": "critical",
                "status": "resolved",
                "days_ago": 5,
                "resolved_days_ago": 4,
                "assigned": True
            },
        ]

        self.stdout.write("\nTickets...")
        created_tickets = []
        now = timezone.now()

        for i, t_data in enumerate(tickets_data):
            tenant = tenants[i % len(tenants)]
            created_at = now - timedelta(days=t_data["days_ago"], hours=random.randint(0, 23))

            existing = Tickets.objects.filter(title=t_data["title"], tenant=tenant).first()
            if existing:
                self.stdout.write(f"  [=] {t_data['title'][:40]}...")
                created_tickets.append(existing)
                continue

            ticket = Tickets.objects.create(
                unit=tenant.unit,
                tenant=tenant,
                category=categories.get(t_data["category"]),
                title=t_data["title"],
                description=t_data["description"],
                severity=t_data["severity"],
                status=t_data["status"],
                access_windows=t_data.get("access_windows"),
                created_at=created_at,
                updated_at=created_at
            )

            if t_data.get("assigned"):
                contractor = random.choice(contractors)
                ticket.assigned_contractor = contractor
                ticket.assigned_at = created_at + timedelta(hours=random.randint(1, 12))
                ContractorAssignments.objects.create(
                    ticket=ticket,
                    contractor=contractor,
                    status='accepted',
                    created_at=ticket.assigned_at
                )

            if t_data.get("resolved_days_ago"):
                ticket.resolved_at = now - timedelta(days=t_data["resolved_days_ago"])

            ticket.save()
            created_tickets.append(ticket)
            self.stdout.write(f"  [+] #{ticket.ticket_id}: {t_data['title'][:40]}... ({t_data['status']})")

        # 9. Messages for demo

        self.stdout.write("\nMessages...")
        messages_samples = [
            ("tenant", "Bonjour, pouvez-vous me donner une estimation du délai d'intervention ?"),
            ("contractor", "Bonjour, je passerai demain matin entre 9h et 11h."),
            ("tenant", "Parfait, je serai présent. Merci !"),
            ("contractor", "Intervention terminée. Tout fonctionne maintenant."),
        ]

        for ticket in created_tickets[:5]:
            if ticket.status in ['in_progress', 'resolved', 'closed']:
                for sender, text in messages_samples[:random.randint(2, 4)]:
                    existing_msg = Messages.objects.filter(ticket=ticket, message_text=text).exists()
                    if not existing_msg:
                        if sender == "tenant":
                            Messages.objects.create(
                                ticket=ticket,
                                tenant_sender=ticket.tenant,
                                message_text=text,
                                is_internal=False,
                                created_at=ticket.created_at + timedelta(hours=random.randint(1, 48))
                            )
                        elif ticket.assigned_contractor:
                            Messages.objects.create(
                                ticket=ticket,
                                contractor_sender=ticket.assigned_contractor,
                                message_text=text,
                                is_internal=False,
                                created_at=ticket.created_at + timedelta(hours=random.randint(2, 72))
                            )

        self.stdout.write("  [+] Messages créés")
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("DONE"))
        self.stdout.write("=" * 50)
        self.stdout.write(f"""
Résumé:
   {IssueCategories.objects.count()} catégories
   {Buildings.objects.count()} immeubles  
   {Units.objects.count()} appartements
   {Tenants.objects.count()} locataires
   {Contractors.objects.count()} contractors
   {Tickets.objects.count()} tickets

Comptes (pwd: admin):
   Admin: admin
   Tenant: marie.dupont@email.com
   Contractor: plomberie1sa@contractor.ch
        """)