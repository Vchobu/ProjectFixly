-- CREATE DATABASE fixly_db;

-- Fixly
    -- Pour la tracabilité les tables ont des TIMESTAMP "created_at" ,
    -- des "is_active" ou des "ON DELETE SET NULL"
    -- Cela permet de ne pas supprimer les données et de savoir quand l'enregistrement a été fait

-- Stratégies ON DELETE utilisées:
    -- CASCADE: Suppr Parent --> Suppr enfants
    -- SET NULL: Garde l'enregistrement + met FK = NULL (on garde ainsi l'historique avec ref=NULL)
    -- RESTRICT: Empêche suppression si utilisé (conserve l'intégrité des données)
    -- les champs is_: soft-delete

-- traçabilité dans le temps
    -- created_at, updated_at, actual_, scheduled_

-- Stratégie de gestion des users
    -- Users = backoffice: URL: admin.resifix.ch, login fait dans la table users
    -- tenants = URL: app.resifix.ch, login fait dans table tenants
    -- contractors = URL: contractor.resifix.ch, login fait dans table contractors

CREATE TABLE django_session (
    session_key varchar(40) PRIMARY KEY,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);

-- Table Owener: Possèdent un ou many immeubles
CREATE TABLE owners (
    owner_id SERIAL PRIMARY KEY,

    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table buildings: à des owners
CREATE TABLE buildings (
    building_id SERIAL PRIMARY KEY,

    owner_id INT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100),
    postal_code VARCHAR(20),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- units = appartements: est dans un building
CREATE TABLE units (
    unit_id SERIAL PRIMARY KEY,

    building_id INT NOT NULL REFERENCES buildings(building_id) ON DELETE CASCADE,
    unit_number VARCHAR(50) NOT NULL,
    floor INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(building_id, unit_number) -- pour éviter les doublons d'appartement dans le meme building
);

-- User: Ce sont les utilisateurs de l'application A L'INTERNE
    -- Admin = tous les accès, Manager = accès pour opérations, Viewer = accès read-only
    -- /!\ les tenants et contractors n'ont pas un accès user /!\
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,

    role VARCHAR(50) DEFAULT 'viewer' CHECK (role IN ('admin', 'manager', 'viewer')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Locataires reporte et habite dans les appartements
CREATE TABLE tenants (
    tenant_id SERIAL PRIMARY KEY,
    unit_id INT NOT NULL REFERENCES units(unit_id) ON DELETE CASCADE,

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),

    -- pour l'accès au portail
    password_hash VARCHAR(255),

    has_keys BOOLEAN DEFAULT false,
    -- permission du locataire à ce que l'on intervient en son abscence
    access_notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Contractors: Répare les problèmes des tenants
CREATE TABLE contractors (
    contractor_id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,

    -- pour l'accès au portail
    password_hash VARCHAR(255),

    specialties TEXT[], -- on verra dans l'application, mais c'est pour distinguer un plombier, un électricien...
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Catégories de problèmes
    -- e.g. d'entrée: 1, fuite de gas, 1, Danger maximum.
CREATE TABLE issue_categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    sla_hours INT NOT NULL,  -- temps de réponse attendu en heure (e.g. 1h c'est urgent, 24h un peu moins)
    description TEXT
);

-- tickets: ticket créé par locataire (tenant) pour signaler un problème dans un appartement
CREATE TABLE tickets (

    ticket_id SERIAL PRIMARY KEY,

    -- un ticket n'exist pas sans les parents --> on delete cascade
    unit_id INT NOT NULL REFERENCES units(unit_id) ON DELETE CASCADE, -- FK2: Quel appartement est concerné
    tenant_id INT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE, -- FK3 Quel locataire a créé

    -- Permet de définir des attributs à un ticket
    -- Notamment lier un ticket à un ticket parent pour gérer le problème de "ticket récurrent ou dupliquer"
    parent_ticket_id INT REFERENCES tickets(ticket_id) ON DELETE SET NULL, -- FK1: self join manuel et optionel
    category_id INT REFERENCES issue_categories(category_id) ON DELETE SET NULL, -- FK4 quel type de problème

    -- Informations du problème
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL, -- Description du locataire

    -- donne une idée d’urgence du point de vue du locataire !=  SLA de issue_categories, mais peut aider à décider
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'emergency')),

    -- Statut et suivi des tickets (hardcoded car catégories classiques)
    -- Information demandé par PO et tracké par log ticket_status_history avec une trigger
    status VARCHAR(50) DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),

    -- Assignation du ticket
    -- un contractor est un acteur et n'a pas le ownership du ticket, donc
    -- "on delete d'un contractor" --> le ticket va avoir une référence NULL (n'a plus de contractor...)
    assigned_contractor_id INT REFERENCES contractors(contractor_id) ON DELETE SET NULL,
    assigned_at TIMESTAMP,

    -- On distint les scheduled VS actuals pour les statisiques d'efficacité des contractors
    scheduled_start TIMESTAMP,
    scheduled_end TIMESTAMP,
    actual_start TIMESTAMP,
    actual_end TIMESTAMP,

    -- disponibilités du locataire en json = flexible lors du dévelopement
        -- e.g. {"start": "18:00", "end": "21:00", "days": ["Lundi", "Mardi"]}
    access_windows JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- date de création du ticket
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- classique, updater par trigger

    resolved_at TIMESTAMP, -- quand le contractor termine le job
    closed_at TIMESTAMP -- manager ferme le ticket quand solved
);

-- Historique immutable pour audit --> tack le champ "statut"
-- Trigger sur le changement de statu d'un ticket --> ajoute une ligne
-- Stratégie: Partant du principte que Immutable signifie pas modif manuel != indescructible
    -- On accepte le "on delete cascade" car si un ticket est créé par erreur
    -- on veut quand meme supprimer l'history car il ne fera plus de sens
CREATE TABLE ticket_status_history (
    history_id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,

    -- log old et new val
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,

    -- tacker l'acteur et son role --> qui à changé
    changed_by_user_id INT REFERENCES users(user_id),
    changed_by_role VARCHAR(50), -- e.g. tenant, contractor...
    reason TEXT, -- clasique: commenter le changement
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Historique immutable pour audit --> tack le champ "category"
-- same PATTERN que pour le champ statue, mais 2 table, car la trigger (évenment qui déclanche) n'est pas le même
CREATE TABLE ticket_category_history (
    history_id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,

    old_category_id INT REFERENCES issue_categories(category_id),
    new_category_id INT NOT NULL REFERENCES issue_categories(category_id),

    changed_by_user_id INT REFERENCES users(user_id),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Les pièces: provenance et couts
CREATE TABLE parts (
    part_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    unit_cost DECIMAL(10, 2),
    -- requirement: on doit pouvoir tracker les sources
    source VARCHAR(50) CHECK (source IN ('van_inventory', 'central_store', 'external_supplier')),
    -- van_inventory = dans le bus, central store = entrepôt, externe = toutes autres sources
    supplier VARCHAR(255)
);

-- Table de correspondance entre: pièces utilisées <-> pour un ticket <-> coûts d'un pièce
CREATE TABLE ticket_parts (
    ticket_part_id SERIAL PRIMARY KEY,
    -- ON DELETE CASCADE: si un ticket est supprimé, les enregistrement de ticket_parts seront supprimés
    ticket_id INT NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    -- ON DELETE RESTRICT: empêche la suppression d'une pièce tant qu'elle est utilisée dans un enregistrement de ticket_parts
    part_id INT NOT NULL REFERENCES parts(part_id) ON DELETE RESTRICT,

    quantity INT NOT NULL DEFAULT 1,
    unit_cost DECIMAL(10, 2),
    total_cost DECIMAL(10, 2) GENERATED ALWAYS AS (quantity * unit_cost) STORED, -- champs automatique (optimisation)

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table de correspondance entre: contractors <-> ticket <-> coûts
CREATE TABLE ticket_labor_costs (
    labor_id SERIAL PRIMARY KEY,

    -- ON DELETE CASCADE: si un ticket est supprimé, les enregistrement de ticket_labor_costs seront supprimés
    ticket_id INT NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    contractor_id INT NOT NULL REFERENCES contractors(contractor_id) ON DELETE CASCADE,

    hours_worked DECIMAL(5, 2) NOT NULL,
    hourly_rate DECIMAL(10, 2) NOT NULL,
    total_cost DECIMAL(10, 2) GENERATED ALWAYS AS (hours_worked * hourly_rate) STORED,  -- champs automatique (optimisation+cohérences)

    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- **********************************************************************************************************************
-- Attachments et messages sont indépendants et liés au ticket (pas entre eux)
    -- car on veut avoir la flexibilité d'ajouter l'un sans l'autre: e.g. un locataire upload a photo...

-- Stratégie de suppression: ON DELETE SET NULL + trigger pour forcer un uploader lors de l'INSERT (=forcer un user_id à l'insertion)
    -- inconvéhient: on perd le lien vers ticket à la suppression --> on aurait pu faire un snapshot mais pas demandé par PO

-- Photos et documents joints aux tickets ( et pas au message...)
CREATE TABLE attachments (
    attachment_id SERIAL PRIMARY KEY,

    -- On a choisi comme lien commun est le ticket, pas un message (logique habituelle de ON DELETE CASCADE sur ticket)
    ticket_id INT NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,

    -- Par contre on mets un ON DELETE SET NULL (enregistrement conservé mais avec ref = NULL si delete parent)
    -- permet la suppression d'un parent sans bloquer sa suppression...
    tenant_uploader_id INT REFERENCES tenants(tenant_id) ON DELETE SET NULL,
    contractor_uploader_id INT REFERENCES contractors(contractor_id) ON DELETE SET NULL,
    user_uploader_id INT REFERENCES users(user_id) ON DELETE SET NULL,

    -- champs spécifiques à attachements
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Le check est simple: il faut 1 et seulement 1 uploader par enregistrement. + relaxation pour gérer la suppresion
    CONSTRAINT chk_attachments_one_uploader
        CHECK (
            -- c'est un tenant_uploader_id?
            (tenant_uploader_id IS NOT NULL AND contractor_uploader_id IS NULL AND user_uploader_id IS NULL) OR
            -- OU c'est un contractor?
            (tenant_uploader_id IS NULL AND contractor_uploader_id IS NOT NULL AND user_uploader_id IS NULL) OR
            -- Ou c'est un user?
            (tenant_uploader_id IS NULL AND contractor_uploader_id IS NULL AND user_uploader_id IS NOT NULL) OR
            -- relaxation de contrainte pour gérer les suppressions (compensé par une trigger pour l'ajout)
            (tenant_uploader_id IS NULL AND contractor_uploader_id IS NULL AND user_uploader_id IS NULL)
        )
);

-- Messages joints aux tickets = meme structure que attachment, mais 2 tables car:
    -- éviter les NULL (message sans attach...)
    -- logique métier différente: message afficher dans chat VS attachement affiché dans une galerie
CREATE TABLE messages (
    message_id SERIAL PRIMARY KEY,

    -- même logique que "attachements"
    ticket_id INT NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    tenant_sender_id INT REFERENCES tenants(tenant_id) ON DELETE SET NULL,
    contractor_sender_id INT REFERENCES contractors(contractor_id) ON DELETE SET NULL,
    user_sender_id INT REFERENCES users(user_id) ON DELETE SET NULL,

    -- champs spécifiques à message
    message_text TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT false, -- Pour notes internes managers ou visible par tous

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- même logique que "attachements"
    CONSTRAINT chk_messages_one_sender
        CHECK (
            (tenant_sender_id IS NOT NULL AND contractor_sender_id IS NULL AND user_sender_id IS NULL) OR
            (tenant_sender_id IS NULL AND contractor_sender_id IS NOT NULL AND user_sender_id IS NULL) OR
            (tenant_sender_id IS NULL AND contractor_sender_id IS NULL AND user_sender_id IS NOT NULL) OR
            -- relaxation de contrainte pour gérer les suppressions (compensé par une trigger pour l'ajout)
            (tenant_sender_id IS NULL AND contractor_sender_id IS NULL AND user_sender_id IS NULL)
        )
);

-- Assignement contractor (HISTORIQUE avec statuts)
-- ne pas confondre:
    -- tickets.assigned_contractor_id = actuellement en charge
    -- contractor_assignments = toutes les demandes d’assignation dans le temps
-- permet principalement de faire les statistiques demandées par PO, e.g.:
    -- tickets refusés au moins 2 fois,
    -- temps moyen avant que status passe en accepted
CREATE TABLE contractor_assignments (
    assignment_id SERIAL PRIMARY KEY,
    -- si un ticket ou contractor est supprimé, l'enregistrement est supprimé aussi
    ticket_id INT NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    contractor_id INT NOT NULL REFERENCES contractors(contractor_id) ON DELETE CASCADE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    declined_at TIMESTAMP,
    decline_reason TEXT,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined'))
);


-- Table des problèmes récurrents dans un immeuble ou un appartement
-- Un pattern peut être associé :
    -- à un immeuble entier (building_id sans unit_id → problème global)
    -- ou à un appartement précis (building_id + unit_id)...

-- La manière d'identifier un pattern récurrent sera définie dans la logique métier.
    -- example 1: même (building_id + unit_id + category_id) avec au moins 3 tickets
    -- example 2: au moins 2 tickets dans les 90 derniers jours pour des catégories différentes avec même type pour même appartement

CREATE TABLE recurring_patterns (
    -- 3 ids d'identification
    pattern_id SERIAL PRIMARY KEY,

    -- logique de on delete, car un patterns n'a pas de sense si un building ou unit n'existe plus
    building_id INT REFERENCES buildings(building_id) ON DELETE CASCADE,
    unit_id INT REFERENCES units(unit_id) ON DELETE CASCADE,

    --type de problème récurrent (ON DELETE SET NULL) car si la catégorie est supprimée, le pattern n'a plus de nom mais existe toujours
    -- pas de on delete cascade, car un pattern à du sense meme sans categories.
    category_id INT REFERENCES issue_categories(category_id) ON DELETE SET NULL,

    pattern_description TEXT NOT NULL,

    -- logique métier: 1 new ticket matching pattern --> +1 --> est-ce un pattern récurrent?
    occurrence_count INT DEFAULT 1,

    -- pour filtrer sur le temps
    first_occurrence TIMESTAMP,
    last_occurrence TIMESTAMP,

    -- proposer une résolution ou décrire un pattern
    resolution_notes TEXT
);

-- gestion des pickets
CREATE TABLE on_call_roster (
    roster_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE, -- FK vers users, car un roster est un user
    backup_user_id INT REFERENCES users(user_id) ON DELETE SET NULL,  -- Optionnel: backup manager
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    notes TEXT, -- champs pour mettre un raison par example
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (end_date >= start_date),
    CHECK (backup_user_id IS NULL OR user_id != backup_user_id) -- empêche d'être sont propore backup
);

-- ********************************************************************************************************
-- INDEXES pour optimisation des requêtes
-- On n'a pas fait d'index composite, car dans notre cas,
-- ce sont principalement des rêquet avec filtres sur 1 seule colonne dans le where

-- table ticket
CREATE INDEX idx_tickets_unit ON tickets(unit_id);
CREATE INDEX idx_tickets_status ON tickets(status); -- filtre
CREATE INDEX idx_tickets_created ON tickets(created_at); -- filtre
CREATE INDEX idx_tickets_contractor ON tickets(assigned_contractor_id);
CREATE INDEX idx_tickets_category ON tickets(category_id);

-- table sur les historiques
CREATE INDEX idx_status_history_ticket ON ticket_status_history(ticket_id);
CREATE INDEX idx_category_history_ticket ON ticket_category_history(ticket_id);

-- tables messages / attachments
CREATE INDEX idx_messages_ticket ON messages(ticket_id);
CREATE INDEX idx_attachments_ticket ON attachments(ticket_id);

-- talbes les PK de immeubles / unités / locataires
CREATE INDEX idx_units_building ON units(building_id);
CREATE INDEX idx_buildings_owner ON buildings(owner_id);
CREATE INDEX idx_tenants_unit ON tenants(unit_id);

-- cout
CREATE INDEX idx_ticket_parts_ticket ON ticket_parts(ticket_id);
CREATE INDEX idx_labor_costs_ticket ON ticket_labor_costs(ticket_id);
CREATE INDEX idx_contractor_assignments_ticket ON contractor_assignments(ticket_id);

-- ******************************************************************************************************
    -- Triggers

-- ***************** 1. Trigger "timestamp" BEFORE UPDATE on table tickets --> mets l'update date en auto *****************
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ***************** 2. Triggers de logs *****************

-- Trigger pour logger automatiquement les changements de statut
CREATE OR REPLACE FUNCTION log_ticket_status_change()
RETURNS TRIGGER AS $$
BEGIN
        -- sur l'enregistrement:  TG_OP = 'UPDATE' --> trigger
        -- sur le champ:  statut change réellement --> IS DISTINCT FROM (gère les nulls)
    IF (TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status) THEN
        INSERT INTO ticket_status_history (ticket_id, old_status, new_status)
        VALUES (NEW.ticket_id, OLD.status, NEW.status);
    END IF;
    RETURN NEW; -- trigger row-level
END;
$$ LANGUAGE plpgsql;

-- AFTER UPDATE
CREATE TRIGGER ticket_status_change_logger
    AFTER UPDATE ON tickets
    FOR EACH ROW
    EXECUTE FUNCTION log_ticket_status_change();

-- Trigger pour logger les changements de catégorie (même logique de log que ticket_status_change_logger)
CREATE OR REPLACE FUNCTION log_ticket_category_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE' AND OLD.category_id IS DISTINCT FROM NEW.category_id) THEN
        INSERT INTO ticket_category_history (ticket_id, old_category_id, new_category_id)
        VALUES (NEW.ticket_id, OLD.category_id, NEW.category_id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ticket_category_change_logger
    AFTER UPDATE ON tickets
    FOR EACH ROW
    EXECUTE FUNCTION log_ticket_category_change();


-- ***************** 3. Triggers de message and attachments *****************

-- force attachments to have a user on insert (suppr géré par ON DELETE SET NULL)
CREATE OR REPLACE FUNCTION attachments_Is_uploader_on_insert()
RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'INSERT'
     AND NEW.tenant_uploader_id IS NULL
     AND NEW.contractor_uploader_id IS NULL
     AND NEW.user_uploader_id IS NULL THEN
    RAISE EXCEPTION 'An attachment must have an uploader on INSERT';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_attachments_Is_uploader_on_insert
BEFORE INSERT ON attachments
FOR EACH ROW
EXECUTE FUNCTION attachments_Is_uploader_on_insert();

-- force messages to have a user on insert (suppr géré par ON DELETE SET NULL)
CREATE OR REPLACE FUNCTION messages_Is_uploader_on_insert()
RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'INSERT'
     AND NEW.tenant_sender_id IS NULL
     AND NEW.contractor_sender_id IS NULL
     AND NEW.user_sender_id IS NULL THEN
    RAISE EXCEPTION 'A message must have a sender on INSERT';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_messages_Is_uploader_on_insert
BEFORE INSERT ON messages
FOR EACH ROW
EXECUTE FUNCTION messages_Is_uploader_on_insert();


-- ***********************************************
    -- Mockup data (hash Django, pw Admin)

INSERT INTO owners (name, email, phone) VALUES
('Owner1', 'owner1@test.ch', '079 111 11 11'),
('Owner2', 'owner2@test.ch', '079 222 22 22');

INSERT INTO buildings (owner_id, name, address, city, postal_code) VALUES
(1, 'Building1', 'Rue Test 1', 'Sion', '1950'),
(2, 'Building2', 'Rue Test 2', 'Sierre', '3960');

INSERT INTO units (building_id, unit_number, floor) VALUES
(1, '1A', 1), (1, '2A', 2),
(2, '1', 0);

INSERT INTO users (username, email, password_hash, role) VALUES
('admin', 'admin@test.ch', 'pbkdf2_sha256$720000$abc123salt$8qJLxgKzL8K3xN3oQvVjW8Y6qKj8X6J5zK3xN3oQ=', 'admin'),
('manager1', 'manager1@test.ch', 'pbkdf2_sha256$720000$abc123salt$8qJLxgKzL8K3xN3oQvVjW8Y6qKj8X6J5zK3xN3oQ=', 'manager');

INSERT INTO tenants (unit_id, first_name, last_name, email, phone, password_hash, has_keys) VALUES
(1, 'Tenant1', 'Test', 'tenant1@test.ch', '076 111 11 11', 'pbkdf2_sha256$720000$abc123salt$8qJLxgKzL8K3xN3oQvVjW8Y6qKj8X6J5zK3xN3oQ=', true),
(2, 'Tenant2', 'Test', 'tenant2@test.ch', '076 222 22 22', 'pbkdf2_sha256$720000$abc123salt$8qJLxgKzL8K3xN3oQvVjW8Y6qKj8X6J5zK3xN3oQ=', false),
(3, 'Tenant3', 'Test', 'tenant3@test.ch', '076 333 33 33', 'pbkdf2_sha256$720000$abc123salt$8qJLxgKzL8K3xN3oQvVjW8Y6qKj8X6J5zK3xN3oQ=', true);

INSERT INTO contractors (company_name, contact_name, email, phone, password_hash, specialties) VALUES
('Plombier1', 'Contact1', 'plombier1@test.ch', '027 111 11 11', 'pbkdf2_sha256$720000$abc123salt$8qJLxgKzL8K3xN3oQvVjW8Y6qKj8X6J5zK3xN3oQ=', ARRAY['plumbing']),
('Electricien1', 'Contact2', 'elec1@test.ch', '027 222 22 22', 'pbkdf2_sha256$720000$abc123salt$8qJLxgKzL8K3xN3oQvVjW8Y6qKj8X6J5zK3xN3oQ=', ARRAY['electrical']);

INSERT INTO issue_categories (name, sla_hours, description) VALUES
('Fuite', 4, NULL),
('Chauffage', 8, NULL),
('Electricité', 12, NULL),
('Autre', 72, NULL);

INSERT INTO tickets (unit_id, tenant_id, category_id, title, description, severity, status) VALUES
(1, 1, 1, 'Fuite cuisine', 'ca coule sous levier', 'medium', 'open'),
(2, 2, 2, 'Radiateur froid', 'le radiateur marche plus', 'high', 'in_progress');

INSERT INTO parts (name, unit_cost, source) VALUES
('Joint', 2.00, 'van_inventory'),
('Vanne', 45.00, 'central_store');

INSERT INTO messages (ticket_id, tenant_sender_id, message_text) VALUES
(1, 1, 'dispo demain soir');

INSERT INTO contractor_assignments (ticket_id, contractor_id, status) VALUES
(2, 1, 'accepted');