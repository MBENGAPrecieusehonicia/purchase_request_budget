# -*- coding: utf-8 -*-
# =============================================================================
# FICHIER : models/__init__.py
# RÔLE    : Liste les fichiers Python du dossier models/ à charger.
#           Chaque fichier contient un modèle (= une table en base de données)
#           ou l'extension d'un modèle existant d'Odoo.
# =============================================================================

from . import res_company              # Ajoute le seuil Direction sur la société.
from . import res_config_settings      # Affiche ce seuil dans Achats > Configuration > Paramètres.
from . import purchase_request_budget  # Nouveau modèle : budget de département.
from . import purchase_request         # Nouveau modèle : la demande d'achat (en-tête + workflow).
from . import purchase_request_line    # Nouveau modèle : les lignes de la demande.
from . import purchase_order           # Ajoute le lien « demande d'origine » sur les demandes de prix.
