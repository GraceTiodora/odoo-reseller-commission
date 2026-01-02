from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_agent = fields.Boolean(
        string='Is Agent',
        help='Centang kalo partner ini agent/reseller',
    )
    
    is_principal = fields.Boolean(
        string='Is Principal',
        help='Centang kalo partner ini principal',
    )

    commission_rate = fields.Float(
        string='Commission Rate (%)',
        default=10.0,
        help='Rate komisi default bila jadi agent',
    )

    @api.constrains('commission_rate')
    def _check_commission_rate(self):
        for p in self:
            if p.is_principal:
                continue
            
            if p.commission_rate < 0.0:
                raise ValidationError(_(f"Rate bila boleh negatif: {p.commission_rate}%"))
            
            if p.commission_rate > 100.0:
                raise ValidationError(_(f"Rate max 100%: {p.commission_rate}%"))