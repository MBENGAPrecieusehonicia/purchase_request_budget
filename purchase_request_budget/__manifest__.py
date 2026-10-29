# -*- coding: utf-8 -*-
# =============================================================================
# FICHIER : __manifest__.py
# RÔLE    : "Carte d'identité" du module. Odoo lit ce fichier AVANT tout le
#           reste pour savoir :
#             - comment s'appelle le module et à quoi il sert ;
#             - de quels autres modules il dépend (ils seront installés avant) ;
#             - quels fichiers XML / CSV charger, et dans quel ordre.
#           Ce fichier ne contient qu'un seul dictionnaire Python.
# =============================================================================
{
    # Nom affiché dans le menu Applications d'Odoo.
    'name': "Demandes d'achat internes",

    # Résumé d'une ligne, affiché sous le nom du module.
    'summary': "Demandes d'achat internes : validation selon le montant, "
               "contrôle budgétaire par département, génération des demandes de prix",

    # Description longue, affichée dans la fiche du module.
    'description': """
Demandes d'achat internes
=========================
* Workflow en 6 états : Brouillon, Soumise, Attente Direction, Validée, Convertie, Refusée.
* Validation Direction uniquement si le total dépasse un seuil paramétrable par société.
* Budget par département sur une période (sans chevauchement) ; la soumission est
  bloquée si le budget restant est insuffisant ou s'il n'y a pas de budget.
* Génération des demandes de prix (une par fournisseur suggéré).
* Sécurité hiérarchique : Demandeur -> Manager -> Direction, plus l'Acheteur (groupe Achats standard).
    """,

    'author': "MBENGA MVOUMBI Precieuse Honicia",

    # Catégorie utilisée pour ranger le module dans la liste des Applications.
    'category': 'Supply Chain/Purchase',

    # Format conseillé par Odoo : <version d'Odoo>.<version du module>.
    # "19.0" = Odoo 19 ; "1.0.0" = version de NOTRE module.
    'version': '19.0.1.0.0',

    # Licence obligatoire (cahier des charges §4.1). LGPL-3 = même licence
    # qu'Odoo Community, cohérent car on ne dépend que de modules Community.
    'license': 'LGPL-3',

    # -------------------------------------------------------------------------
    # DÉPENDANCES : modules qui doivent être installés AVANT le nôtre.
    # Le cahier des charges n'autorise que ces 5 modules.
    # -------------------------------------------------------------------------
    'depends': [
        'base',      # Noyau : utilisateurs, sociétés, devises, groupes de sécurité.
        'mail',      # Chatter (historique) et activités « À valider ».
        'hr',        # Employés (hr.employee) et départements (hr.department).
        'purchase',  # Demandes de prix (purchase.order) et menu Achats.
        'product',   # Articles, prix d'achat, unités de mesure, fournisseurs.
    ],

    # -------------------------------------------------------------------------
    # DATA : fichiers chargés à l'installation ET à chaque mise à jour.
    # L'ORDRE COMPTE : un fichier ne peut utiliser que ce qui a été chargé
    # par les fichiers placés avant lui.
    #   1. les groupes (le fichier CSV des droits y fait référence) ;
    #   2. les droits d'accès ;
    #   3. les données techniques (séquence, type d'activité, tâche planifiée) ;
    #   4. les vues et actions ;
    #   5. les menus EN DERNIER (ils pointent vers les actions des vues).
    # -------------------------------------------------------------------------
    'data': [
        'security/purchase_request_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_activity_type_data.xml',
        'data/ir_cron_data.xml',
        'wizard/purchase_request_refuse_wizard_views.xml',
        'views/purchase_request_views.xml',
        'views/purchase_request_budget_views.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],

    # -------------------------------------------------------------------------
    # DEMO : fichiers chargés UNIQUEMENT si la base a été créée avec les
    # données de démonstration (3 départements, 3 budgets, 5 demandes...).
    # -------------------------------------------------------------------------
    'demo': [
        'demo/purchase_request_demo.xml',
    ],

    # True = le module apparaît comme une « Application » dans le menu Applications.
    'application': True,
    'installable': True,
}
