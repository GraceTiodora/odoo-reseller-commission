from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestPartnerCommission(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner_model = self.env["res.partner"]

    def test_create_principal_partner(self):
        # Test membuat partner sebagai principal
        p = self.partner_model.create({
            "name": "PT B Vendor",
            "is_principal": True,
        })
        assert p.is_principal == True
        assert p.name == "PT B Vendor"

    def test_create_agent_partner(self):
        # Test create agent
        a = self.partner_model.create({
            "name": "PT A Reseller",
            "is_principal": False,
            "commission_rate": 10.0,
        })
        self.assertFalse(a.is_principal)
        self.assertEqual(a.commission_rate, 10.0)

    def test_commission_rate_valid(self):
        # Valid rates: 0, 50, 100
        ag1 = self.partner_model.create({
            "name": "Agent Rate 0",
            "is_principal": False,
            "commission_rate": 0.0,
        })
        self.assertEqual(ag1.commission_rate, 0.0)

        ag2 = self.partner_model.create({
            "name": "Agent Rate 50",
            "is_principal": False,
            "commission_rate": 50.0,
        })
        self.assertEqual(ag2.commission_rate, 50.0)

        ag3 = self.partner_model.create({
            "name": "Agent Rate 100",
            "is_principal": False,
            "commission_rate": 100.0,
        })
        self.assertEqual(ag3.commission_rate, 100.0)

    def test_commission_rate_negative_error(self):
        # negative rate should fail
        try:
            self.partner_model.create({
                "name": "Bad Agent",
                "is_principal": False,
                "commission_rate": -5.0,
            })
            self.fail("Should raise validation error")
        except ValidationError:
            pass  # expected

    def test_commission_rate_over_100_error(self):
        # over 100% should fail
        with self.assertRaises(ValidationError):
            self.partner_model.create({
                "name": "Bad Agent 2",
                "is_principal": False,
                "commission_rate": 150.0,
            })

    def test_principal_no_need_rate(self):
        # principal doesnt need rate
        principal = self.partner_model.create({
            "name": "PT C",
            "is_principal": True,
        })
        self.assertTrue(principal.is_principal)

    def test_agent_default_rate(self):
        # agent should have default 10%
        agent = self.partner_model.create({
            "name": "PT A Default",
            "is_principal": False,
        })
        self.assertEqual(agent.commission_rate, 10.0)

    def test_update_rate_validation(self):
        # update rate also validated
        agent = self.partner_model.create({
            "name": "Update Test",
            "is_principal": False,
            "commission_rate": 10.0,
        })

        # valid update
        agent.write({"commission_rate": 20.0})
        agent.refresh()
        self.assertEqual(agent.commission_rate, 20.0)

        # invalid update
        with self.assertRaises(ValidationError):
            agent.write({"commission_rate": 120.0})
