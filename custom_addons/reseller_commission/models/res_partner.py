from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_principal = fields.Boolean(
        string='Is Principal',
    )

    commission_rate = fields.Float(
        string='Commission Rate (%)',
        default=10.0,
    )

    @api.constrains('commission_rate')
    def _check_commission_rate(self):
        for p in self:
            is_p = p.is_principal
            if is_p:
                continue
            
            r = p.commission_rate
            if r < 0.0:
                msg = f"Rate neg: {r}%"
                raise ValidationError(_(msg))
            
            if r > 100.0:
                msg = f"Max 100: {r}%"
                raise ValidationError(_(msg))