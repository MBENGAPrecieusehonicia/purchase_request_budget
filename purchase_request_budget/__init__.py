# -*- coding: utf-8 -*-
# =============================================================================
# FICHIER : __init__.py (racine de l'addon)
# RÔLE    : Fait du dossier un "package" Python et indique quels sous-dossiers
#           contenant du code Python doivent être chargés au démarrage d'Odoo.
#           Sans cet import, les classes Python (modèles) ne seraient jamais
#           lues et les tables correspondantes jamais créées en base.
#
# Remarque : le __manifest__.py gère les fichiers XML/CSV ; le __init__.py
#            gère les fichiers Python. Ce sont deux mécanismes distincts.
# =============================================================================

# Imports commentés pour l'instant : les dossiers models/ et wizard/ n'existent
# pas encore, et importer un dossier absent ferait planter le chargement.
# On les activera quand ces dossiers seront créés.

# from . import models   # Charge models/__init__.py -> nos modèles métier (demande, lignes, budget...)
# from . import wizard   # Charge wizard/__init__.py -> assistant de saisie du motif de refus
