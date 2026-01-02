"""Migration: Add is_agent, is_principal, commission_rate fields to res.partner"""

from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    """Add missing fields to res.partner if they don't exist."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Get the res.partner model
    partner_model = env['res.partner']
    
    # Add the fields by updating the module
    cr.execute("""
        SELECT EXISTS(
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'res_partner'
            AND column_name = 'is_agent'
        )
    """)
    
    if not cr.fetchone()[0]:
        # Fields don't exist, so we need to let Odoo create them by reloading the model
        cr.execute("ALTER TABLE res_partner ADD COLUMN is_agent boolean DEFAULT FALSE")
        cr.execute("ALTER TABLE res_partner ADD COLUMN is_principal boolean DEFAULT FALSE")
        cr.execute("ALTER TABLE res_partner ADD COLUMN commission_rate numeric DEFAULT 10.0")
        cr.commit()
