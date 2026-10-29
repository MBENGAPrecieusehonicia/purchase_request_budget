# -*- coding: utf-8 -*-
# =============================================================================
# FICHIER : __init__.py (racine du module)
# RÔLE    : Fait du dossier un « package » Python et indique à Odoo quels
#           sous-dossiers contiennent du code Python à charger.
#           Sans ces imports, nos classes (modèles) ne seraient jamais lues
#           et les tables correspondantes jamais créées en base de données.
#
# À retenir : __manifest__.py charge les fichiers XML/CSV,
#             __init__.py charge les fichiers Python.
# =============================================================================

from . import models   # Modèles métier : demande, lignes, budget, extensions.
from . import wizard   # Assistant de saisie du motif de refus.
