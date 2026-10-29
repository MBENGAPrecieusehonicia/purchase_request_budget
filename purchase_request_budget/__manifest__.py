# -*- coding: utf-8 -*-
# =============================================================================
# FICHIER : __manifest__.py
# RÔLE    : "Carte d'identité" de l'addon. Odoo lit ce fichier AVANT tout le
#           reste pour savoir :
#             - comment s'appelle le module et à quoi il sert ;
#             - de quels autres modules il dépend (ordre d'installation) ;
#             - quels fichiers de données (XML, CSV) charger, et dans quel ordre.
#           Ce fichier contient UN SEUL dictionnaire Python, sans code exécutable.
# =============================================================================
{
    # Nom affiché dans la liste des Applications d'Odoo.
    'name': 'Demandes d\'achat internes avec contrôle budgétaire',

    # Format de version recommandé par Odoo : <version Odoo>.<majeure>.<mineure>.<correctif>
    # "19.0" indique que le module cible Odoo 19 Community ; "1.0.0" est la version de NOTRE module.
    # Odoo s'en sert pour savoir s'il faut lancer des scripts de migration lors d'une mise à jour.
    'version': '19.0.1.0.0',

    # Catégorie utilisée pour classer le module dans le menu Applications.
    'category': 'Inventory/Purchase',

    # Résumé court (une ligne), affiché sous le nom du module.
    'summary': 'Demandes d\'achat internes : validation selon le montant, '
               'contrôle budgétaire par département, génération des demandes de prix',

    # Description longue, affichée dans la fiche du module.
    'description': """
Demandes d'achat internes
=========================
* Workflow en 6 états : Brouillon, Soumise, Attente Direction, Validée, Convertie, Refusée.
* Validation Direction uniquement si le total dépasse un seuil paramétrable par société.
* Budget par département sur une période (sans chevauchement) ; soumission bloquée
  si le budget restant est insuffisant ou absent.
* Génération des demandes de prix (RFQ), une par fournisseur suggéré.
* Sécurité hiérarchique : Demandeur -> Manager -> Direction, et Acheteur (groupe Achats standard).
    """,

    # Auteur du module (affiché dans la fiche).
    'author': 'Precieuse',

    # Licence obligatoire (exigée au §4.1). Odoo Community est sous LGPL-3 :
    # c'est le choix cohérent pour un module qui s'appuie uniquement sur des modules Community.
    'license': 'LGPL-3',

    # -------------------------------------------------------------------------
    # DÉPENDANCES : liste des modules qui DOIVENT être installés avant le nôtre.
    # Odoo les installe automatiquement s'ils ne le sont pas encore.
    # Cahier des charges §1 : UNIQUEMENT ces 5 modules, aucun module tiers.
    # -------------------------------------------------------------------------
    'depends': [
        'base',      # Noyau : utilisateurs, sociétés, devises, groupes de sécurité, paramètres.
        'mail',      # Chatter (suivi des changements d'état/total/motif) et activités « À valider ».
        'hr',        # Employés (hr.employee) et départements (hr.department) avec leur manager.
        'purchase',  # Demandes de prix (purchase.order), groupe « Utilisateur Achats », menu Achats.
        'product',   # Articles, prix d'achat (standard_price), unités de mesure, fournisseurs.
    ],

    # -------------------------------------------------------------------------
    # DATA : fichiers chargés à l'installation ET à chaque mise à jour du module.
    # L'ORDRE EST IMPORTANT : un fichier ne peut référencer que des éléments
    # déjà chargés par les fichiers qui le précèdent.
    #   1. Groupes et règles de sécurité (les droits d'accès CSV y font référence)
    #   2. Droits d'accès aux modèles (CSV)
    #   3. Données techniques (séquence DA/2026/0001, type d'activité, action planifiée)
    #   4. Assistants, puis vues et actions
    #   5. Menus EN DERNIER (ils pointent vers les actions définies dans les vues)
    #
    # Les lignes sont commentées pour l'instant : Odoo refuse d'installer un
    # module si un fichier listé ici n'existe pas. On les décommentera au fur
    # et à mesure de leur création.
    # -------------------------------------------------------------------------
    'data': [
        # 'security/purchase_request_security.xml',
        # 'security/ir.model.access.csv',
        # 'data/ir_sequence_data.xml',
        # 'data/mail_activity_type_data.xml',
        # 'data/ir_cron_data.xml',
        # 'wizard/purchase_request_refuse_wizard_views.xml',
        # 'views/purchase_request_views.xml',
        # 'views/department_budget_views.xml',
        # 'views/purchase_order_views.xml',
        # 'views/res_config_settings_views.xml',
        # 'views/menus.xml',
    ],

    # -------------------------------------------------------------------------
    # DEMO : fichiers chargés UNIQUEMENT si la base a été créée avec les
    # données de démonstration (§4.1 : 3 départements + managers, 3 budgets,
    # 5 demandes à des états variés dont une au-dessus du seuil).
    # Séparés de 'data' pour que le module s'installe aussi sur une base sans démo.
    # -------------------------------------------------------------------------
    'demo': [
        # 'demo/purchase_request_demo.xml',
    ],

    # True = le module apparaît comme une "Application" dans le menu Applications.
    'application': True,

    # True = le module peut être installé.
    'installable': True,
}
