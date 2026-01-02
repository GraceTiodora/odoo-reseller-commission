from odoo.tests import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestSaleOrderCommission(TransactionCase):

    def setUp(self):
        super().setUp()
        self.so_m = self.env["sale.order"]
        self.partner_m = self.env["res.partner"]
        self.product_m = self.env["product.product"]
        self.account_m = self.env["account.account"]

        self.pt_b = self.partner_m.create({
            "name": "PT B",
            "is_principal": True,
        })

        self.pt_a = self.partner_m.create({
            "name": "PT A",
            "is_principal": False,
            "commission_rate": 10.0,
        })

        self.cust = self.partner_m.create({
            "name": "Customer ABC",
        })

        self.prod = self.product_m.create({
            "name": "Product Test",
            "list_price": 1000000.0,
            "type": "product",
        })

        self._setup_acc()

    def _setup_acc(self):
        acc = self.account_m.search(
            [("internal_type", "=", "income")],
            limit=1,
        )
        if not acc:
            self.account_m.create({
                "name": "Revenue",
                "code": "4100",
                "user_type_id": self.env.ref("account.data_account_type_income").id,
            })

    def test_regular_so(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        assert not so.is_agent_sale
        assert so.commission_amount == 0.0

    def test_agent_so_create(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "agent_id": self.pt_a.id,
            "principal_id": self.pt_b.id,
            "commission_rate": 10.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        self.assertTrue(so.is_agent_sale)
        self.assertEqual(so.commission_status, "draft")

    def test_commission_calc_10pct(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "agent_id": self.pt_a.id,
            "principal_id": self.pt_b.id,
            "commission_rate": 10.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        self.assertEqual(so.amount_untaxed, 10000000.0)
        self.assertEqual(so.commission_amount, 1000000.0)

    def test_commission_calc_various_rates(self):
        test_rates = [
            (5.0, 500000.0),
            (15.0, 1500000.0),
            (25.0, 2500000.0)
        ]

        for r, exp in test_rates:
            so = self.so_m.create({
                "partner_id": self.cust.id,
                "is_agent_sale": True,
                "agent_id": self.pt_a.id,
                "principal_id": self.pt_b.id,
                "commission_rate": r,
                "order_line": [(0, 0, {
                    "product_id": self.prod.id,
                    "quantity": 10.0,
                    "price_unit": 1000000.0,
                })],
            })
            self.assertEqual(so.commission_amount, exp)

    def test_no_agent_sale_no_commission(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": False,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })
        self.assertEqual(so.commission_amount, 0.0)

    def test_onchange_reset_fields(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "agent_id": self.pt_a.id,
            "principal_id": self.pt_b.id,
            "commission_rate": 10.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        so.is_agent_sale = False
        so._onchange_is_agent_sale()
        
        self.assertFalse(so.is_agent_sale)
        self.assertEqual(so.agent_id.id, False)
        self.assertEqual(so.principal_id.id, False)
        self.assertEqual(so.commission_rate, 0.0)

    def test_confirm_no_agent(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "principal_id": self.pt_b.id,
            "commission_rate": 10.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        with self.assertRaises(UserError):
            so.action_confirm()

    def test_confirm_no_principal(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "agent_id": self.pt_a.id,
            "commission_rate": 10.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        try:
            so.action_confirm()
            self.fail("should error")
        except UserError:
            pass

    def test_confirm_zero_rate(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "agent_id": self.pt_a.id,
            "principal_id": self.pt_b.id,
            "commission_rate": 0.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        with self.assertRaises(UserError):
            so.action_confirm()

    def test_confirm_success(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "agent_id": self.pt_a.id,
            "principal_id": self.pt_b.id,
            "commission_rate": 10.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        so.action_confirm()
        self.assertEqual(so.state, "sale")
        self.assertEqual(so.commission_status, "confirmed")

    def test_invoice_not_exist(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "agent_id": self.pt_a.id,
            "principal_id": self.pt_b.id,
            "commission_rate": 10.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        assert not so.commission_invoice_id

    def test_invoice_not_confirmed_error(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "agent_id": self.pt_a.id,
            "principal_id": self.pt_b.id,
            "commission_rate": 10.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        with self.assertRaises(UserError):
            so.action_create_commission_invoice()

    def test_invoice_create_ok(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "agent_id": self.pt_a.id,
            "principal_id": self.pt_b.id,
            "commission_rate": 10.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        so.action_confirm()
        res = so.action_create_commission_invoice()
        
        assert so.commission_invoice_id
        self.assertEqual(so.commission_status, "invoiced")
        self.assertEqual(res["res_id"], so.commission_invoice_id.id)

    def test_psak72_amount(self):
        # check invoice only has commission not SO
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "agent_id": self.pt_a.id,
            "principal_id": self.pt_b.id,
            "commission_rate": 10.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        so.action_confirm()
        so.action_create_commission_invoice()
        
        inv = so.commission_invoice_id
        # should be 1M not 10M
        self.assertEqual(inv.amount_total, 1000000.0)

    def test_onchange_agent_rate(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        so.agent_id = self.pt_a.id
        so._onchange_agent_id_set_rate()

        self.assertEqual(so.commission_rate, self.pt_a.commission_rate)

    def test_invoice_not_agent_error(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": False,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        so.action_confirm()

        with self.assertRaises(UserError):
            so.action_create_commission_invoice()

    def test_invoice_already_exist_error(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "agent_id": self.pt_a.id,
            "principal_id": self.pt_b.id,
            "commission_rate": 10.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        so.action_confirm()
        so.action_create_commission_invoice()

        # try again
        with self.assertRaises(UserError):
            so.action_create_commission_invoice()

    def test_psak72_full_scenario(self):
        so = self.so_m.create({
            "partner_id": self.cust.id,
            "is_agent_sale": True,
            "agent_id": self.pt_a.id,
            "principal_id": self.pt_b.id,
            "commission_rate": 10.0,
            "order_line": [(0, 0, {
                "product_id": self.prod.id,
                "quantity": 10.0,
                "price_unit": 1000000.0,
            })],
        })

        so.action_confirm()
        so.action_create_commission_invoice()

        inv = so.commission_invoice_id

        # PT A revenue should be only komisi (1M)
        self.assertEqual(inv.amount_total, 1000000.0)
        # SO amount should still be full (10M)
        self.assertEqual(so.amount_total, 10000000.0)
