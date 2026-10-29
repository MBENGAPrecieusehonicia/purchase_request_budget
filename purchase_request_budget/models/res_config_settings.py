# -*- coding: utf-8 -*-
# =============================================================================
# FICHIER : models/res_config_settings.py
# RÔLE    : Rend le seuil Direction modifiable depuis l'écran
#           Achats > Configuration > Paramètres.
#
# Comment marche l'écran Paramètres d'Odoo ?
#   « res.config.settings » est un modèle TEMPORAIRE : rien n'y est stocké
#   durablement. On y déclare un champ « related » qui pointe vers le vrai
#   champ de la société : quand l'utilisateur clique sur « Enregistrer »,
#   la valeur est écrite sur la société active.
# =============================================================================

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # related='company_id.purchase_request_threshold' : ce champ est un
    # « miroir » du champ de la société.
    # readonly=False : par défaut un champ related est en lecture seule ;
    # on l'ouvre en écriture pour pouvoir le modifier.
    # company_currency_id : champ « devise de la société » déjà fourni par
    # le module Achats sur cet écran.
    purchase_request_threshold = fields.Monetary(
        related='company_id.purchase_request_threshold',
        currency_field='company_currency_id',
        readonly=False,
    )
