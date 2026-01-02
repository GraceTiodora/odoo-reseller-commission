{
    'name': 'Reseller Commission Tracking',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Agent commission tracking & invoicing',
    'description': 'PSAK 72 compliant agent commission management',
    'author': 'Dora & Team',
    'depends': ['sale_management', 'account'],
    'data': [
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}