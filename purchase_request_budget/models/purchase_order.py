# -*- coding: utf-8 -*-
# =============================================================================
# FICHIER : models/purchase_order.py
# RÔLE    : Ajoute sur la demande de prix (purchase.order, modèle standard du
#           module Achats) un lien vers la demande d'achat d'origine (§3.5).
#           Ce lien sert dans les deux sens :
#             - la demande de prix affiche sa demande d'origine ;
#             - la demande d'achat compte ses demandes de prix (bouton intelligent).
# =============================================================================

from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # index='btree_not_null' : index SQL qui accélère les recherches,
    # en ignorant les commandes sans demande d'origine (la majorité).
    purchase_request_id = fields.Many2one(
        'purchase.request', string="Demande d'achat d'origine",
        readonly=True, copy=False, index='btree_not_null')
