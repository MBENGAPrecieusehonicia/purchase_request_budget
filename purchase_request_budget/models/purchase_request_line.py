# -*- coding: utf-8 -*-
# =============================================================================
# FICHIER : models/purchase_request_line.py
# RÔLE    : Nouveau modèle « Ligne de demande d'achat » (§3.2) :
#           produit, description, quantité, unité, prix unitaire estimé,
#           fournisseur suggéré et sous-total.
# =============================================================================

from odoo import api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'
    _description = "Ligne de demande d'achat"
    _order = 'request_id, sequence, id'

    # Lien vers la demande parente.
    # ondelete='cascade' : si la demande est supprimée, ses lignes aussi.
    request_id = fields.Many2one(
        'purchase.request', string="Demande d'achat", required=True,
        ondelete='cascade', index=True)

    # Permet de réordonner les lignes par glisser-déposer dans la liste.
    sequence = fields.Integer(string="Séquence", default=10)

    # domain=... : seuls les produits « Peut être acheté » sont proposés.
    product_id = fields.Many2one(
        'product.product', string="Produit", required=True,
        domain=[('purchase_ok', '=', True)])

    # Les champs suivants sont pré-remplis à partir du produit (compute),
    # mais restent modifiables (readonly=False).
    name = fields.Char(
        string="Description", required=True,
        compute='_compute_from_product', store=True, readonly=False, precompute=True)

    # digits='Product Unit' : nombre de décimales configuré pour les quantités.
    product_qty = fields.Float(
        string="Quantité", required=True, default=1.0, digits='Product Unit')

    product_uom_id = fields.Many2one(
        'uom.uom', string="Unité", required=True,
        compute='_compute_from_product', store=True, readonly=False, precompute=True)

    # Prix d'achat du produit par défaut (§3.2) = champ standard_price
    # (« Coût ») de la fiche produit.
    price_unit = fields.Monetary(
        string="Prix unitaire estimé", currency_field='currency_id',
        compute='_compute_from_product', store=True, readonly=False, precompute=True)

    # Fournisseur suggéré (optionnel) : par défaut, le premier fournisseur
    # renseigné dans l'onglet Achats de la fiche produit.
    vendor_id = fields.Many2one(
        'res.partner', string="Fournisseur suggéré",
        compute='_compute_from_product', store=True, readonly=False, precompute=True)

    price_subtotal = fields.Monetary(
        string="Sous-total", compute='_compute_price_subtotal', store=True,
        currency_field='currency_id')

    # Champs recopiés de la demande, utiles pour l'affichage et les règles.
    currency_id = fields.Many2one(related='request_id.currency_id', string="Devise")
    company_id = fields.Many2one(
        related='request_id.company_id', store=True, string="Société")
    state = fields.Selection(related='request_id.state', string="État de la demande")

    # ------------------------------------------------------------------
    # CALCULS
    # ------------------------------------------------------------------

    @api.depends('product_id')
    def _compute_from_product(self):
        """Pré-remplit description, unité, prix et fournisseur depuis le produit."""
        for line in self:
            product = line.product_id
            line.name = product.display_name
            line.product_uom_id = product.uom_id
            line.price_unit = product.standard_price
            # seller_ids = fournisseurs du produit ; [:1] = le premier (ou vide).
            line.vendor_id = product.seller_ids[:1].partner_id

    @api.depends('product_qty', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.product_qty * line.price_unit

    # ------------------------------------------------------------------
    # VERROUILLAGE : les lignes ne sont modifiables que si la demande est
    # en brouillon (§3.2). Même logique que write() sur la demande.
    # ------------------------------------------------------------------

    def _check_request_is_draft(self, requests):
        if self.env.context.get('purchase_request_workflow'):
            return
        locked = requests.filtered(lambda r: r.state != 'draft')
        if locked:
            raise UserError(self.env._(
                "Les lignes d'une demande ne sont modifiables que lorsqu'elle est en brouillon.\n"
                "Demande(s) concernée(s) : %s", ", ".join(locked.mapped('name'))))

    @api.model_create_multi
    def create(self, vals_list):
        requests = self.env['purchase.request'].browse(
            [vals['request_id'] for vals in vals_list if vals.get('request_id')])
        self._check_request_is_draft(requests)
        return super().create(vals_list)

    def write(self, vals):
        self._check_request_is_draft(self.request_id)
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_request_locked(self):
        # On autorise la suppression en cascade quand la demande entière
        # est supprimée (sa propre règle de suppression s'applique alors).
        self._check_request_is_draft(self.request_id.filtered(lambda r: r.state != 'refused'))
