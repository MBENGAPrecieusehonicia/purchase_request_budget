# -*- coding: utf-8 -*-
# =============================================================================
# FICHIER : models/purchase_request_budget.py
# RÔLE    : Nouveau modèle « Budget de département » (cahier des charges §3.4).
#
# Un budget = un montant alloué à un département sur une période.
#   - Montant engagé  = somme des demandes « Validées » ou « Converties » du
#                       département dont la date tombe dans la période.
#   - Montant restant = montant alloué - montant engagé.
# Règle : deux budgets d'un même département ne peuvent pas se chevaucher.
# =============================================================================

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_date


class PurchaseRequestBudget(models.Model):
    # _name = nom technique du modèle. Odoo crée la table SQL
    # « purchase_request_budget » (les points deviennent des _).
    _name = 'purchase.request.budget'
    # _description = libellé lisible du modèle (obligatoire, sinon avertissement).
    _description = "Budget de département"
    # _order = tri par défaut des listes : budgets les plus récents d'abord.
    _order = 'date_start desc, department_id'

    # ------------------------------------------------------------------
    # CHAMPS (chaque champ = une colonne dans la table)
    # ------------------------------------------------------------------

    # Many2one = lien vers UN enregistrement d'un autre modèle (ici un département).
    # required=True : le champ est obligatoire.
    department_id = fields.Many2one(
        'hr.department', string="Département", required=True, index=True)

    date_start = fields.Date(string="Date de début", required=True)
    date_end = fields.Date(string="Date de fin", required=True)

    # default=lambda self: self.env.company : par défaut, la société active
    # de l'utilisateur. « lambda » permet de calculer cette valeur au moment
    # de la création (et pas une seule fois au démarrage du serveur).
    company_id = fields.Many2one(
        'res.company', string="Société", required=True,
        default=lambda self: self.env.company)

    # related = valeur recopiée automatiquement depuis un autre champ.
    # Ici, la devise de la société : elle sert à afficher les montants.
    currency_id = fields.Many2one(
        related='company_id.currency_id', string="Devise")

    amount_allocated = fields.Monetary(
        string="Montant alloué", required=True, currency_field='currency_id')

    # Champs CALCULÉS (compute=...) : Odoo appelle la méthode indiquée pour
    # obtenir la valeur. Ils ne sont pas stockés en base (pas de store=True)
    # car ils dépendent de l'état de nombreuses demandes : on les recalcule
    # à chaque affichage pour qu'ils soient toujours à jour.
    amount_committed = fields.Monetary(
        string="Montant engagé", compute='_compute_amounts',
        currency_field='currency_id')
    amount_remaining = fields.Monetary(
        string="Montant restant", compute='_compute_amounts',
        currency_field='currency_id')

    # ------------------------------------------------------------------
    # CONTRAINTE SQL : vérifiée directement par PostgreSQL.
    # ------------------------------------------------------------------
    _check_amount_positive = models.Constraint(
        'CHECK(amount_allocated >= 0)',
        "Le montant alloué d'un budget ne peut pas être négatif.",
    )

    # ------------------------------------------------------------------
    # MÉTHODES DE CALCUL
    # ------------------------------------------------------------------

    @api.depends('department_id', 'date_start', 'date_end')
    def _compute_display_name(self):
        """Nom affiché du budget, par exemple : « Informatique (01/01/2026 → 31/12/2026) ».

        display_name est le texte qu'Odoo montre partout où l'on affiche
        un budget (listes déroulantes, champ Budget sur la demande...).
        """
        for budget in self:
            budget.display_name = "%s (%s → %s)" % (
                budget.department_id.name or '',
                format_date(self.env, budget.date_start),
                format_date(self.env, budget.date_end),
            )

    def _compute_amounts(self):
        """Calcule le montant engagé et le montant restant de chaque budget."""
        # sudo() = on lit les demandes avec les droits « administrateur ».
        # Pourquoi ? Un simple demandeur ne voit que SES demandes ; sans sudo()
        # il ne verrait qu'une partie du montant engagé et le calcul serait faux.
        Request = self.env['purchase.request'].sudo()
        for budget in self:
            requests = Request.search(budget._get_committed_requests_domain())
            # mapped('amount_total') = liste des totaux ; sum() les additionne.
            budget.amount_committed = sum(requests.mapped('amount_total'))
            budget.amount_remaining = budget.amount_allocated - budget.amount_committed

    def _get_committed_requests_domain(self):
        """Renvoie le « domaine » (filtre de recherche) des demandes qui
        consomment ce budget.

        Un domaine Odoo est une liste de conditions (champ, opérateur, valeur)
        reliées par des ET.
        """
        self.ensure_one()  # Vérifie qu'on travaille sur UN seul budget.
        return [
            ('department_id', '=', self.department_id.id),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ('validated', 'converted')),
            ('date_request', '>=', self.date_start),
            ('date_request', '<=', self.date_end),
        ]

    # ------------------------------------------------------------------
    # CONTRAINTES PYTHON : @api.constrains est appelé automatiquement à
    # chaque création / modification des champs listés. Lever une
    # ValidationError annule l'enregistrement et affiche le message.
    # ------------------------------------------------------------------

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for budget in self:
            if budget.date_end < budget.date_start:
                raise ValidationError(self.env._(
                    "La date de fin du budget doit être postérieure ou égale à sa date de début."))

    @api.constrains('department_id', 'company_id', 'date_start', 'date_end')
    def _check_no_overlap(self):
        """Deux budgets d'un même département ne doivent pas se chevaucher.

        Deux périodes [A_début, A_fin] et [B_début, B_fin] se chevauchent si :
            A_début <= B_fin  ET  A_fin >= B_début
        """
        for budget in self:
            overlapping = self.sudo().search([
                ('id', '!=', budget.id),  # On ne se compare pas à soi-même.
                ('department_id', '=', budget.department_id.id),
                ('company_id', '=', budget.company_id.id),
                ('date_start', '<=', budget.date_end),
                ('date_end', '>=', budget.date_start),
            ], limit=1)
            if overlapping:
                raise ValidationError(self.env._(
                    "Le département %(department)s a déjà un budget sur cette période : %(budget)s.\n"
                    "Deux budgets d'un même département ne peuvent pas se chevaucher.",
                    department=budget.department_id.name,
                    budget=overlapping.display_name,
                ))

    # ------------------------------------------------------------------
    # OUTIL utilisé par la demande d'achat
    # ------------------------------------------------------------------

    @api.model
    def _find_budget(self, department, date, company):
        """Renvoie le budget du département couvrant la date donnée
        (ou un ensemble vide s'il n'y en a pas).

        @api.model : méthode qui ne travaille pas sur un enregistrement
        précis, mais sur le modèle en général (comme une fonction utilitaire).
        """
        if not department or not date:
            return self.browse()  # Ensemble vide.
        return self.search([
            ('department_id', '=', department.id),
            ('company_id', '=', company.id),
            ('date_start', '<=', date),
            ('date_end', '>=', date),
        ], limit=1)
