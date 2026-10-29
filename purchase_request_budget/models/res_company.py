# -*- coding: utf-8 -*-
# =============================================================================
# FICHIER : models/res_company.py
# RÔLE    : Ajoute un champ « seuil de validation Direction » sur la société.
#
# Pourquoi sur la société ? Le cahier des charges (§3.6) demande un seuil
# « par société » : chaque société d'une base multi-sociétés a son propre seuil.
# =============================================================================

from odoo import fields, models


class ResCompany(models.Model):
    # _inherit sans _name = on AJOUTE des champs au modèle existant
    # « res.company » (la table des sociétés) au lieu d'en créer un nouveau.
    _inherit = 'res.company'

    # fields.Monetary = montant affiché avec le symbole de la devise.
    # currency_field indique quel champ contient la devise : ici, la devise
    # de la société elle-même (champ « currency_id » qui existe déjà).
    # default=5000 : valeur donnée aux sociétés à l'installation du module.
    purchase_request_threshold = fields.Monetary(
        string="Seuil de validation Direction",
        currency_field='currency_id',
        default=5000.0,
        help="Une demande d'achat dont le total est STRICTEMENT supérieur à ce "
             "montant doit être validée par la Direction après le manager.",
    )
