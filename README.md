# Fixly

Gestion de tickets pour régies immobilières. 3 interfaces : admin, locataire, contractor.

## Installation

```bash
pip install -r requirements.txt
python manage.py migrate
```

### Étape 1 : Générer les données

```bash
python manage.py generate_demo
```

### Étape 2 : Démarrer le serveur

```bash
python manage.py runserver
```

## Données générées

| Type         | Quantité | Détails                              |
|--------------|----------|--------------------------------------|
| Catégories   | 8        | Plomberie, Électricité, Chauffage... |
| Immeubles    | 3        | Résidences à Genève                  |
| Appartements | 24       | 8 par immeuble                       |
| Locataires   | 8        | Avec emails et téléphones            |
| Contractors  | 10       | Entreprises spécialisées             |
| Tickets      | 15       | Mix de statuts et urgences           |
| Messages     | 20       | conversations                        |

## Comptes de test

| Rôle       | Login                      | Password       |
|------------|----------------------------|----------------|
| Admin      | admin                      | admin          |
| AdminFixly | admin                      | admin          |
| Tenant     | marie.dupont@email.com     | admin          |
| Contractor | plomberie1sa@contractor.ch | admin          |
 
## Structure

```
core/
├── views_admin.py      # interface admin
├── views_tenant.py     # interface locataire  
├── views_contractor.py # interface contractor
├── models.py           # modèles Django (depuis PostgreSQL)
└── sla.py              # calcul des SLA
```

## URLs

- `/admin/` - Django admin
- `/fixly-admin/` - dashboard admin
- `/tenant/` - portail locataire
- `/contractor/` - portail contractor

## Tests

```bash
python manage.py test core.tests
python manage.py run_coverage  # avec rapport HTML
```

## Notes

- DB PostgreSQL requise (voir `.env.example`)
- SLA calculé dynamiquement selon sévérité ou catégorie
- Chart.js pour les graphiques du dashboard
