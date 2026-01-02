from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_agent_sale = fields.Boolean(
        string="Agent Reseller Sale",
        default=False,
    )
    agent_id = fields.Many2one(
        "res.partner",
        string="Agent",
        domain="[('is_principal', '=', False)]",
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
        if not self.is_agent_sale:
            # reset
            self.agent_id = False
            self.principal_id = False
            self.commission_rate = 0.0
            self.commission_status = "draft"

    @api.onchange("agent_id")
    def _onchange_agent_id_set_rate(self):
        if self.agent_id:
            # set rate from agent if available
            r = self.agent_id.commission_rate
            if r > 0:
                self.commission_rate = r

    @api.depends("amount_untaxed", "commission_rate", "is_agent_sale")
    def _compute_commission(self):
        for order in self:
            amt = 0
            if order.is_agent_sale:
                if order.commission_rate > 0:
                    untax = order.amount_untaxed
                    pct = order.commission_rate / 100.0
                    amt = untax * pct
            order.commission_amount = amt

    @api.constrains("commission_rate")
    def _check_commission_rate_value(self):
        for order in self:
            val = order.commission_rate
            if val < 0:
                raise ValidationError(_("Commission tidak boleh negatif"))
            if val > 100:
                raise ValidationError(_("Max commission adalah 100%"))

    def action_confirm(self):
        for order in self:
            if order.is_agent_sale:
                # Check agent
                agent = order.agent_id
                if not agent:
                    raise UserError(_("Agent wajib dipilih"))
                
                principal = order.principal_id
                if not principal:
                    raise UserError(_("Tentukan principal terlebih dahulu"))
                
                # Check rate
                if order.commission_rate <= 0:
                    raise UserError(_("Rate harus lebih dari 0"))

        result = super().action_confirm()

        for order in self:
            if order.is_agent_sale:
                order.commission_status = "confirmed"

        return result

    def action_create_commission_invoice(self):
        self.ensure_one()
        
        # Validation
        is_agent = self.is_agent_sale
        if not is_agent:
            raise UserError(_("Bukan agent sale"))
        
        state = self.state
        if state != "sale":
            raise UserError(_("Order harus di-confirm dulu"))
        
        status = self.commission_status
        if status != "confirmed":
            raise UserError(_("Status commission belum confirmed"))
        
        inv_exist = self.commission_invoice_id
        if inv_exist:
            raise UserError(_("Invoice sudah dibuat"))
        
        if not self.agent_id:
            raise UserError(_("Agent tidak ada"))
        if not self.principal_id:
            raise UserError(_("Principal tidak ada"))
        
        komisi = self.commission_amount
        if komisi <= 0:
            raise UserError(_("Komisi harus > 0"))
        
        # Create invoice data
        line_item = {
            "name": f"Komisi - {self.partner_id.name}",
            "quantity": 1.0,
            "price_unit": komisi,
            "account_id": self._get_revenue_account().id,
        }
        
        move_data = {
            "move_type": "out_invoice",
            "partner_id": self.agent_id.id,
            "invoice_origin": self.name,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [(0, 0, line_item)],
        }
        
        move = self.env["account.move"].create(move_data)
        move.action_post()
        
        self.commission_invoice_id = move.id
        self.commission_status = "invoiced"
        
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": move.id,
            "target": "current",
        }

    def _get_revenue_account(self):
        # first try to find standard account
        acc_model = self.env["account.account"]
        
        search_params = [("code", "=like", "41%"), ("deprecated", "=", False)]
        acc = acc_model.search(search_params, limit=1)
        
        if acc:
            return acc
        
        # no standard found, fallback
        income_search = [("internal_type", "=", "income")]
        acc2 = acc_model.search(income_search, limit=1)
        
        if acc2:
            return acc2
        
        # nothing
        raise UserError(_("Tidak ada revenue account"))
