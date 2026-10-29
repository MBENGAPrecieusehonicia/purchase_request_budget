# -*- coding: utf-8 -*-
# =============================================================================
# FICHIER : models/purchase_request.py
# RÔLE    : Nouveau modèle « Demande d'achat interne » : l'en-tête de la
#           demande, ses calculs et tout son WORKFLOW (cahier des charges §3).
#
# Les 6 états et leurs passages (§3.1) :
#
#   Brouillon --soumission--> Soumise --validation manager--> total > seuil ?
#                                                              |-- non --> Validée
#                                                              |-- oui --> Attente Direction
#   Attente Direction --validation direction--> Validée
#   Validée --création des demandes de prix--> Convertie
#   Soumise / Attente Direction --refus + motif--> Refusée --remise en brouillon--> Brouillon
#
# Chaque bouton de l'écran appelle une méthode « action_... » de ce fichier.
# =============================================================================

from datetime import timedelta

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import format_amount, format_date

# Identifiant XML du type d'activité « À valider » (défini dans
# data/mail_activity_type_data.xml). On le met dans une constante pour ne
# pas répéter la chaîne partout.
ACTIVITY_TYPE_TO_VALIDATE = 'purchase_request_budget.mail_activity_type_to_validate'

# Identifiant XML du groupe Direction (défini dans security/purchase_request_security.xml).
GROUP_DIRECTOR = 'purchase_request_budget.group_purchase_request_director'

# Nombre de jours d'attente avant que l'action planifiée relance les valideurs.
REMINDER_DELAY_DAYS = 3


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _description = "Demande d'achat interne"
    # _inherit avec une liste = on « hérite » des fonctionnalités de ces modèles :
    #   - mail.thread          : le chatter (historique des messages + suivi
    #                            des modifications de champs avec tracking=True) ;
    #   - mail.activity.mixin  : les activités planifiées (« À valider »).
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_request desc, id desc'

    # ==================================================================
    # CHAMPS DE L'EN-TÊTE (§3.2)
    # ==================================================================

    # Référence DA/2026/0001 : remplie dans create() grâce à une séquence.
    # copy=False : quand on duplique une demande, la copie reçoit une
    # nouvelle référence au lieu de recopier l'ancienne.
    name = fields.Char(
        string="Référence", required=True, readonly=True, copy=False,
        default="Nouveau")

    # Demandeur = un employé (hr.employee). Par défaut : l'employé lié à
    # l'utilisateur connecté (self.env.user.employee_id).
    # tracking=True : chaque changement est noté dans le chatter.
    employee_id = fields.Many2one(
        'hr.employee', string="Demandeur", required=True, tracking=True,
        default=lambda self: self.env.user.employee_id)

    # Utilisateur Odoo du demandeur, recopié depuis l'employé.
    # store=True : la valeur est enregistrée en base, ce qui permet de
    # l'utiliser dans les règles de sécurité et les filtres
    # (« voit uniquement ses demandes » = user_id = utilisateur connecté).
    user_id = fields.Many2one(
        related='employee_id.user_id', store=True, index=True,
        string="Utilisateur demandeur")

    # Département : DÉDUIT de l'employé (compute), mais MODIFIABLE
    # (readonly=False), comme le demande le §3.2.
    # precompute=True : la valeur est calculée avant l'enregistrement en
    # base, ce qui permet de respecter required=True dès la création.
    department_id = fields.Many2one(
        'hr.department', string="Département", required=True, tracking=True,
        compute='_compute_department_id', store=True, readonly=False,
        precompute=True, index=True)

    # Date du jour par défaut (dans le fuseau horaire de l'utilisateur).
    date_request = fields.Date(
        string="Date de la demande", required=True,
        default=fields.Date.context_today)
    date_needed = fields.Date(string="Date souhaitée")

    reason = fields.Text(string="Motif", required=True, tracking=True)

    company_id = fields.Many2one(
        'res.company', string="Société", required=True,
        default=lambda self: self.env.company)

    # Tous les montants sont exprimés dans la devise de la société (§3.2).
    currency_id = fields.Many2one(
        related='company_id.currency_id', string="Devise")

    # One2many = la liste des lignes qui pointent vers cette demande
    # (champ request_id du modèle purchase.request.line).
    # copy=True : dupliquer une demande duplique aussi ses lignes.
    line_ids = fields.One2many(
        'purchase.request.line', 'request_id', string="Lignes", copy=True)

    # Total calculé ET stocké (store=True), comme demandé au §3.2.
    amount_total = fields.Monetary(
        string="Total", compute='_compute_amount_total', store=True,
        tracking=True, currency_field='currency_id')

    # Selection = liste de choix fixe. Chaque choix est un couple
    # (valeur technique stockée en base, libellé affiché).
    state = fields.Selection(
        selection=[
            ('draft', "Brouillon"),
            ('submitted', "Soumise"),
            ('to_approve', "Attente Direction"),
            ('validated', "Validée"),
            ('converted', "Convertie"),
            ('refused', "Refusée"),
        ],
        string="État", required=True, default='draft', copy=False,
        tracking=True, index=True)

    refuse_reason = fields.Text(
        string="Motif du refus", readonly=True, copy=False, tracking=True)

    # ------------------------------------------------------------------
    # Traçabilité des validations (qui a validé, et quand).
    # ------------------------------------------------------------------
    date_submitted = fields.Datetime(
        string="Date de soumission", readonly=True, copy=False)
    manager_approver_id = fields.Many2one(
        'res.users', string="Validée par (manager)", readonly=True, copy=False)
    manager_approval_date = fields.Datetime(
        string="Date de validation manager", readonly=True, copy=False)
    director_approver_id = fields.Many2one(
        'res.users', string="Validée par (direction)", readonly=True, copy=False)
    director_approval_date = fields.Datetime(
        string="Date de validation direction", readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Budget (§3.4) : le budget du département qui couvre la date de la
    # demande, et ce qu'il en reste. Non stockés : recalculés à l'affichage.
    # ------------------------------------------------------------------
    budget_id = fields.Many2one(
        'purchase.request.budget', string="Budget",
        compute='_compute_budget')
    budget_remaining = fields.Monetary(
        string="Budget restant", compute='_compute_budget',
        currency_field='currency_id')

    # Indique si la validation Direction sera nécessaire (pour l'affichage).
    needs_director_approval = fields.Boolean(
        string="Validation Direction requise",
        compute='_compute_needs_director_approval')

    # ------------------------------------------------------------------
    # Demandes de prix générées (§3.5).
    # groups=... : seuls les acheteurs voient ce champ (un simple demandeur
    # n'a pas le droit de lire les commandes d'achat).
    # ------------------------------------------------------------------
    purchase_order_ids = fields.One2many(
        'purchase.order', 'purchase_request_id', string="Demandes de prix",
        groups='purchase.group_purchase_user')
    purchase_order_count = fields.Integer(
        string="Nombre de demandes de prix",
        compute='_compute_purchase_order_count')

    # ==================================================================
    # MÉTHODES DE CALCUL (compute)
    # @api.depends(...) liste les champs dont dépend le calcul : quand l'un
    # d'eux change, Odoo relance automatiquement la méthode.
    # ==================================================================

    @api.depends('employee_id')
    def _compute_department_id(self):
        for request in self:
            request.department_id = request.employee_id.department_id

    @api.depends('line_ids.price_subtotal')
    def _compute_amount_total(self):
        for request in self:
            request.amount_total = sum(request.line_ids.mapped('price_subtotal'))

    @api.depends('department_id', 'date_request', 'company_id')
    def _compute_budget(self):
        Budget = self.env['purchase.request.budget']
        for request in self:
            budget = Budget._find_budget(
                request.department_id, request.date_request, request.company_id)
            request.budget_id = budget
            request.budget_remaining = budget.amount_remaining

    @api.depends('amount_total', 'company_id.purchase_request_threshold')
    def _compute_needs_director_approval(self):
        for request in self:
            request.needs_director_approval = request._is_above_threshold()

    @api.depends('purchase_order_ids')
    def _compute_purchase_order_count(self):
        for request in self:
            # sudo() : le compteur est calculable même par un utilisateur qui
            # n'a pas accès aux commandes d'achat.
            request.purchase_order_count = len(request.sudo().purchase_order_ids)

    # ==================================================================
    # CRÉATION, MODIFICATION, SUPPRESSION (méthodes standard d'Odoo
    # que l'on « surcharge » pour ajouter nos règles).
    # ==================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Attribue la référence DA/AAAA/NNNN à chaque nouvelle demande."""
        for vals in vals_list:
            if vals.get('name', "Nouveau") == "Nouveau":
                # next_by_code lit la séquence définie dans
                # data/ir_sequence_data.xml et renvoie le numéro suivant.
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request') or "Nouveau"
        # super() = on appelle la méthode create() d'origine d'Odoo, qui
        # fait la vraie création en base.
        return super().create(vals_list)

    def write(self, vals):
        """Seules les demandes en brouillon sont modifiables (§3.2).

        Exception : les méthodes du workflow (soumettre, valider...) doivent
        pouvoir changer l'état. Elles passent un « contexte »
        purchase_request_workflow=True pour signaler que la modification
        est autorisée.
        """
        if not self.env.context.get('purchase_request_workflow'):
            locked_requests = self.filtered(lambda r: r.state != 'draft')
            if locked_requests and self._has_business_fields(vals):
                raise UserError(self.env._(
                    "Seules les demandes en brouillon peuvent être modifiées.\n"
                    "Demande(s) concernée(s) : %s",
                    ", ".join(locked_requests.mapped('name'))))
        return super().write(vals)

    @api.model
    def _has_business_fields(self, vals):
        """Vrai si vals contient d'autres champs que ceux du chatter.

        Les champs « message_... » et « activity_... » appartiennent au
        chatter : on doit pouvoir écrire des messages ou planifier des
        activités sur une demande, quel que soit son état.
        """
        return any(not field.startswith(('message_', 'activity_')) for field in vals)

    # @api.ondelete : vérification appelée AVANT la suppression.
    # at_uninstall=False : on ne bloque pas la suppression quand on
    # désinstalle le module (sinon la désinstallation échouerait).
    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_refused(self):
        """Seules les demandes en brouillon ou refusées sont supprimables (§3.2)."""
        for request in self:
            if request.state not in ('draft', 'refused'):
                raise UserError(self.env._(
                    "La demande %(name)s est à l'état « %(state)s » : seules les "
                    "demandes en brouillon ou refusées peuvent être supprimées.",
                    name=request.name,
                    state=dict(self._fields['state']._description_selection(self.env))[request.state],
                ))

    # ==================================================================
    # OUTILS INTERNES (méthodes commençant par « _ » : non appelables
    # depuis un bouton de l'interface)
    # ==================================================================

    def _workflow_write(self, vals):
        """Écrit vals en signalant à write() qu'il s'agit du workflow."""
        return self.with_context(purchase_request_workflow=True).write(vals)

    def _is_above_threshold(self):
        """Vrai si le total est STRICTEMENT supérieur au seuil Direction (§3.3)."""
        self.ensure_one()
        threshold = self.company_id.purchase_request_threshold
        # compare_amounts compare deux montants en tenant compte de l'arrondi
        # de la devise : renvoie 1 si le premier est plus grand.
        return self.currency_id.compare_amounts(self.amount_total, threshold) > 0

    def _is_director(self):
        """Vrai si l'utilisateur connecté appartient au groupe Direction."""
        return self.env.user.has_group(GROUP_DIRECTOR)

    def _get_director_users(self):
        """Utilisateurs du groupe Direction (hors demandeur de la demande)."""
        self.ensure_one()
        directors = self.env.ref(GROUP_DIRECTOR).all_user_ids
        # On écarte les utilisateurs « portail » (share) et le demandeur
        # lui-même, qui ne peut pas valider sa propre demande.
        return directors.filtered(
            lambda user: user.active and not user.share and user != self.user_id)

    def _get_manager_user(self):
        """Utilisateur du manager du département (vide s'il n'y en a pas)."""
        self.ensure_one()
        return self.department_id.manager_id.user_id

    def _get_current_approvers(self):
        """Utilisateurs qui doivent valider la demande à son étape actuelle."""
        self.ensure_one()
        if self.state == 'submitted':
            manager = self._get_manager_user()
            # Si le département n'a pas de manager (ou si le demandeur EST
            # le manager), c'est la Direction qui valide.
            if manager and manager != self.user_id:
                return manager
            return self._get_director_users()
        if self.state == 'to_approve':
            return self._get_director_users()
        return self.env['res.users']

    def _schedule_validation_activities(self):
        """Crée une activité « À valider » pour chaque valideur attendu."""
        for request in self:
            for user in request._get_current_approvers():
                request.activity_schedule(
                    ACTIVITY_TYPE_TO_VALIDATE,
                    user_id=user.id,
                    note=self.env._("Demande d'achat %s à valider.", request.name),
                )

    def _check_budget(self):
        """Contrôle budgétaire au moment de la soumission (§3.4).

        Bloque si aucun budget ne couvre la date, ou si le total dépasse
        le montant restant. Le message indique les deux montants.
        """
        for request in self:
            budget = request.budget_id
            if not budget:
                raise UserError(self.env._(
                    "Soumission impossible : aucun budget n'est défini pour le "
                    "département « %(department)s » à la date du %(date)s.\n"
                    "Demandez à la Direction de créer un budget pour cette période.",
                    department=request.department_id.name,
                    date=format_date(self.env, request.date_request),
                ))
            remaining = budget.amount_remaining
            if request.currency_id.compare_amounts(request.amount_total, remaining) > 0:
                raise UserError(self.env._(
                    "Soumission impossible : budget insuffisant.\n\n"
                    "Total de la demande : %(total)s\n"
                    "Budget restant du département « %(department)s » : %(remaining)s",
                    total=format_amount(self.env, request.amount_total, request.currency_id),
                    department=request.department_id.name,
                    remaining=format_amount(self.env, remaining, request.currency_id),
                ))

    def _check_can_validate(self):
        """Vérifie que l'utilisateur connecté peut valider / refuser à l'étape actuelle (§3.3)."""
        user = self.env.user
        for request in self:
            # Règle : on ne valide jamais sa propre demande.
            if request.user_id == user:
                raise UserError(self.env._(
                    "Vous ne pouvez pas valider ou refuser votre propre demande (%s).",
                    request.name))
            if request.state == 'submitted':
                # Niveau 1 : le manager du département OU un membre de la Direction.
                if request._get_manager_user() != user and not self._is_director():
                    raise UserError(self.env._(
                        "Seul le manager du département « %(department)s » ou un "
                        "membre de la Direction peut traiter la demande %(name)s.",
                        department=request.department_id.name,
                        name=request.name,
                    ))
            elif request.state == 'to_approve':
                # Niveau 2 : uniquement la Direction.
                if not self._is_director():
                    raise UserError(self.env._(
                        "Seule la Direction peut traiter la demande %s, "
                        "dont le total dépasse le seuil de validation.",
                        request.name))
            else:
                raise UserError(self.env._(
                    "La demande %s n'est pas en attente de validation.", request.name))

    # ==================================================================
    # ACTIONS DES BOUTONS (workflow)
    # Chaque méthode correspond à un bouton du formulaire
    # (views/purchase_request_views.xml, balise <header>).
    # ==================================================================

    def action_submit(self):
        """Bouton « Soumettre » : Brouillon -> Soumise (§3.3, règle 1)."""
        for request in self:
            if request.state != 'draft':
                raise UserError(self.env._("Seule une demande en brouillon peut être soumise."))
            if request.user_id != self.env.user and not self._is_director():
                raise UserError(self.env._("Seul le demandeur peut soumettre sa demande."))
            # Une demande sans ligne ne peut pas être soumise (§3.2).
            if not request.line_ids:
                raise UserError(self.env._(
                    "La demande %s ne contient aucune ligne : ajoutez au moins un article "
                    "avant de la soumettre.", request.name))
        # Contrôle du budget (lève une erreur et annule tout si insuffisant).
        self._check_budget()
        self._workflow_write({
            'state': 'submitted',
            'date_submitted': fields.Datetime.now(),
            'refuse_reason': False,  # On efface l'ancien motif de refus éventuel.
        })
        for request in self:
            # Le demandeur suit la demande : il sera notifié des messages.
            request.message_subscribe(partner_ids=request.user_id.partner_id.ids)
        # Activité « À valider » pour le manager du département.
        self._schedule_validation_activities()
        return True

    def action_approve(self):
        """Bouton « Valider » (niveau 1, manager) : Soumise -> Validée ou Attente Direction."""
        self._check_can_validate()
        for request in self:
            if request.state != 'submitted':
                raise UserError(self.env._("La demande %s n'est pas à l'état « Soumise ».", request.name))
            # Validation Direction obligatoire si total > seuil (§3.3, règle 3).
            next_state = 'to_approve' if request._is_above_threshold() else 'validated'
            # On clôture l'activité « À valider » du manager...
            request.activity_feedback([ACTIVITY_TYPE_TO_VALIDATE])
            request._workflow_write({
                'state': next_state,
                'manager_approver_id': self.env.user.id,
                'manager_approval_date': fields.Datetime.now(),
            })
            # ... et, si besoin, on en crée une pour la Direction.
            if next_state == 'to_approve':
                request._schedule_validation_activities()
        return True

    def action_approve_director(self):
        """Bouton « Valider (Direction) » (niveau 2) : Attente Direction -> Validée."""
        self._check_can_validate()
        for request in self:
            if request.state != 'to_approve':
                raise UserError(self.env._(
                    "La demande %s n'est pas en attente de validation Direction.", request.name))
            request.activity_feedback([ACTIVITY_TYPE_TO_VALIDATE])
            request._workflow_write({
                'state': 'validated',
                'director_approver_id': self.env.user.id,
                'director_approval_date': fields.Datetime.now(),
            })
        return True

    def action_open_refuse_wizard(self):
        """Bouton « Refuser » : ouvre l'assistant qui demande le motif (§3.3, règle 4).

        Renvoyer un dictionnaire « ir.actions.act_window » demande au
        navigateur d'ouvrir une fenêtre ; target='new' = fenêtre surgissante.
        """
        self.ensure_one()
        self._check_can_validate()  # On vérifie les droits AVANT d'ouvrir l'assistant.
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Refuser la demande"),
            'res_model': 'purchase.request.refuse.wizard',
            'view_mode': 'form',
            'target': 'new',
            # « default_... » pré-remplit le champ correspondant de l'assistant.
            'context': {'default_request_id': self.id},
        }

    def _do_refuse(self, reason):
        """Refus effectif, appelé par l'assistant une fois le motif saisi."""
        self._check_can_validate()
        for request in self:
            # On supprime les activités « À valider » devenues inutiles.
            request.activity_unlink([ACTIVITY_TYPE_TO_VALIDATE])
            request._workflow_write({'state': 'refused', 'refuse_reason': reason})
            # Message dans le chatter + notification au demandeur (partner_ids).
            # Markup(...) % (...) protège le texte saisi (pas d'injection HTML).
            request.message_post(
                body=Markup("<p>%s</p><p><b>%s</b> %s</p>") % (
                    self.env._("Demande refusée par %s.", self.env.user.name),
                    self.env._("Motif :"),
                    reason,
                ),
                partner_ids=request.user_id.partner_id.ids,
                subtype_xmlid='mail.mt_comment',
            )
        return True

    def action_reset_draft(self):
        """Bouton « Remettre en brouillon » : Refusée -> Brouillon (§3.3, règle 5)."""
        for request in self:
            if request.state != 'refused':
                raise UserError(self.env._("Seule une demande refusée peut être remise en brouillon."))
            if request.user_id != self.env.user and not self._is_director():
                raise UserError(self.env._("Seul le demandeur peut remettre sa demande en brouillon."))
        # Le motif de refus est conservé pour que le demandeur puisse corriger ;
        # il sera effacé à la prochaine soumission.
        self._workflow_write({
            'state': 'draft',
            'manager_approver_id': False,
            'manager_approval_date': False,
            'director_approver_id': False,
            'director_approval_date': False,
        })
        return True

    def action_create_purchase_orders(self):
        """Bouton « Créer les demandes de prix » : Validée -> Convertie (§3.5).

        Une demande de prix (purchase.order) par fournisseur suggéré, avec
        une ligne de commande par ligne de demande.
        """
        if not self.env.user.has_group('purchase.group_purchase_user'):
            raise UserError(self.env._("Seuls les acheteurs peuvent créer les demandes de prix."))
        PurchaseOrder = self.env['purchase.order']
        for request in self:
            if request.state != 'validated':
                raise UserError(self.env._(
                    "La demande %s doit être à l'état « Validée » pour générer les demandes de prix.",
                    request.name))
            # Toutes les lignes doivent avoir un fournisseur : sinon on refuse
            # en listant les lignes concernées.
            lines_without_vendor = request.line_ids.filtered(lambda line: not line.vendor_id)
            if lines_without_vendor:
                raise UserError(self.env._(
                    "Impossible de générer les demandes de prix : les lignes suivantes "
                    "n'ont pas de fournisseur suggéré :\n%s",
                    "\n".join("- %s (quantité : %s)" % (line.name, line.product_qty)
                              for line in lines_without_vendor)))
            date_planned = request.date_needed or fields.Date.context_today(request)
            # grouped('vendor_id') renvoie un dictionnaire
            # {fournisseur: lignes de ce fournisseur}.
            for vendor, lines in request.line_ids.grouped('vendor_id').items():
                PurchaseOrder.create({
                    'partner_id': vendor.id,
                    'company_id': request.company_id.id,
                    'origin': request.name,              # Champ standard « Document d'origine ».
                    'purchase_request_id': request.id,   # Notre lien vers la demande.
                    # Command.create(...) = crée une ligne de commande liée.
                    'order_line': [Command.create({
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'product_qty': line.product_qty,
                        'product_uom_id': line.product_uom_id.id,
                        'price_unit': line.price_unit,
                        'date_planned': date_planned,
                    }) for line in lines],
                })
            request._workflow_write({'state': 'converted'})
        if len(self) == 1:
            return self.action_view_purchase_orders()
        return True

    def action_view_purchase_orders(self):
        """Bouton intelligent : ouvre les demandes de prix liées à la demande."""
        self.ensure_one()
        orders = self.purchase_order_ids
        action = {
            'type': 'ir.actions.act_window',
            'name': self.env._("Demandes de prix"),
            'res_model': 'purchase.order',
            'domain': [('id', 'in', orders.ids)],
            'view_mode': 'list,form',
        }
        if len(orders) == 1:
            # Une seule demande de prix : on l'ouvre directement en formulaire.
            action.update({'view_mode': 'form', 'res_id': orders.id})
        return action

    # ==================================================================
    # ACTION PLANIFIÉE (data/ir_cron_data.xml)
    # ==================================================================

    @api.model
    def _cron_send_validation_reminders(self):
        """Relance quotidienne : les demandes en attente de validation depuis
        plus de REMINDER_DELAY_DAYS jours reçoivent un message qui notifie
        les valideurs attendus.
        """
        limit_date = fields.Datetime.now() - timedelta(days=REMINDER_DELAY_DAYS)
        pending_requests = self.search([
            ('state', 'in', ('submitted', 'to_approve')),
            ('date_submitted', '<=', limit_date),
        ])
        for request in pending_requests:
            approvers = request._get_current_approvers()
            if not approvers:
                continue
            request.message_post(
                body=self.env._(
                    "Relance automatique : cette demande attend une validation "
                    "depuis plus de %s jours.", REMINDER_DELAY_DAYS),
                partner_ids=approvers.partner_id.ids,
                subtype_xmlid='mail.mt_note',
            )
