# -*- coding: utf-8 -*-
# =============================================================================
# FICHIER : wizard/purchase_request_refuse_wizard.py
# RÔLE    : Assistant « Refuser la demande » (§3.3, règle 4) : une petite
#           fenêtre qui OBLIGE à saisir un motif avant de refuser.
#
# TransientModel = modèle TEMPORAIRE : ses enregistrements sont effacés
# automatiquement par Odoo après un moment. Parfait pour une fenêtre de
# saisie qui ne sert qu'une fois.
# =============================================================================

from odoo import fields, models


class PurchaseRequestRefuseWizard(models.TransientModel):
    _name = 'purchase.request.refuse.wizard'
    _description = "Assistant de refus d'une demande d'achat"

    # Rempli automatiquement grâce au contexte « default_request_id »
    # envoyé par le bouton Refuser (voir action_open_refuse_wizard).
    request_id = fields.Many2one(
        'purchase.request', string="Demande d'achat", required=True, readonly=True)

    # required=True : impossible de valider la fenêtre sans motif.
    reason = fields.Text(string="Motif du refus", required=True)

    def action_confirm(self):
        """Bouton « Refuser » de la fenêtre : applique le refus puis ferme la fenêtre."""
        self.ensure_one()
        self.request_id._do_refuse(self.reason)
        # Cette action standard ferme la fenêtre surgissante.
        return {'type': 'ir.actions.act_window_close'}
