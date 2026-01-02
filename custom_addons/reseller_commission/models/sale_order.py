from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_agent_sale = fields.Boolean(
        string="Agent Reseller Sale",
        default=False,
    )
    agent_id = fields.Many2one(
        "res.partner",
        string="Agent",
        domain="[('is_agent', '=', True)]",
        help="The agent/reseller facilitating this sale",
    )
    principal_id = fields.Many2one(
        "res.partner", string="Principal",
        domain="[('is_principal', '=', True)]",
    )
    commission_rate = fields.Float(
        string="Commission Rate (%)", default=0.0,
    )
    commission_amount = fields.Monetary(
        string="Commission Amount",
        compute="_compute_commission", store=True,
        currency_field="currency_id",
    )
    commission_status = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("invoiced", "Invoiced"), ("paid", "Paid")],
        default="draft", copy=False, readonly=True,
    )
    commission_invoice_id = fields.Many2one(
        "account.move", string="Commission Invoice", readonly=True, copy=False,
    )

    @api.onchange("is_agent_sale")
    def _onchange_is_agent_sale(self):
        # reset fields kalo di-uncheck
        if not self.is_agent_sale:
            self.agent_id = False
            self.principal_id = False
            self.commission_rate = 0.0
            self.commission_status = "draft"

    @api.onchange("agent_id")
    def _onchange_agent_id_set_rate(self):
        # auto isi rate dari agent
        if self.agent_id and self.agent_id.commission_rate > 0:
            self.commission_rate = self.agent_id.commission_rate

    @api.depends("amount_untaxed", "commission_rate", "is_agent_sale")
    def _compute_commission(self):
        for order in self:
            amt = 0
            if order.is_agent_sale and order.commission_rate > 0:
                amt = order.amount_untaxed * (order.commission_rate / 100.0)
            order.commission_amount = amt

    @api.constrains("commission_rate")
    def _check_commission_rate_value(self):
        for order in self:
            if order.commission_rate < 0:
                raise ValidationError(_("Commission rate tidak boleh negatif"))
            if order.commission_rate > 100:
                raise ValidationError(_("Commission rate max 100%"))

    def action_confirm(self):
        # validasi dulu sebelum confirm
        for order in self:
            if order.is_agent_sale:
                if not order.agent_id:
                    raise UserError(_("Agent harus dipilih"))
                if not order.principal_id:
                    raise UserError(_("Principal harus dipilih"))
                if order.commission_rate <= 0:
                    raise UserError(_("Commission rate harus lebih dari 0"))

        res = super().action_confirm()

        # update status ke confirmed
        for order in self:
            if order.is_agent_sale:
                order.commission_status = "confirmed"
                _logger.info(f"Commission confirmed: {order.name} - {order.commission_amount}")

        return res

    def action_create_commission_invoice(self):
        self.ensure_one()
        
        # cek dulu semua requirement
        if not self.is_agent_sale:
            raise UserError(_("Ini bukan agent sale"))
        if self.state != "sale":
            raise UserError(_("SO harus di-confirm dulu"))
        if self.commission_status != "confirmed":
            raise UserError(_("Status commission belum confirmed"))
        if self.commission_invoice_id:
            raise UserError(_("Invoice sudah pernah dibuat"))
        if not self.agent_id or not self.principal_id:
            raise UserError(_("Agent dan Principal harus diisi"))
        if self.commission_amount <= 0:
            raise UserError(_("Commission amount harus > 0"))
        
        # bikin invoice dari agent ke principal
        # sesuai PSAK 72, agent cuma catat komisi aja
        inv_line = {
            "name": f"Komisi - {self.name} ({self.partner_id.name})",
            "quantity": 1.0,
            "price_unit": self.commission_amount,
            "account_id": self._get_revenue_account().id,
        }
        
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.principal_id.id,
            "invoice_origin": self.name,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [(0, 0, inv_line)],
        })
        
        invoice.action_post()
        
        self.commission_invoice_id = invoice.id
        self.commission_status = "invoiced"
        
        _logger.info(f"Invoice komisi created: {invoice.name} - Amount: {self.commission_amount}")
        
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": invoice.id,
            "target": "current",
        }

    def _get_revenue_account(self):
        # cari revenue account buat invoice line
        acc = self.env["account.account"].search(
            [("code", "=like", "41%"), ("deprecated", "=", False)],
            limit=1
        )
        if acc:
            return acc
        
        # kalo ga ada, coba cari income account
        acc = self.env["account.account"].search(
            [("account_type", "=", "income")],
            limit=1
        )
        if acc:
            return acc
        
        raise UserError(_("Ga ada revenue account, tolong setup chart of accounts dulu"))
