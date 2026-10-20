from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestFreightSecurity(TransactionCase):

    def setUp(self):
        super().setUp()
        # 1. Create two separate companies: Company A and Company B
        self.company_a = self.env['res.company'].create({'name': 'Company A'})
        self.company_b = self.env['res.company'].create({'name': 'Company B'})

        # 2. Create a user belonging ONLY to Company B
        self.user_b = self.env['res.users'].create({
            'name': 'User B',
            'login': 'user_b_freight_test',
            'company_id': self.company_b.id,
            'company_ids': [(6, 0, [self.company_b.id])],
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        # 3. Create partner and ports for Company A
        self.partner = self.env['res.partner'].create({
            'name': 'Shared Partner',
            'company_id': False,
        })
        self.port_1 = self.env['freight.port'].create({
            'name': 'Port A1',
            'code': 'PA1',
            'is_land': True,
        })
        self.port_2 = self.env['freight.port'].create({
            'name': 'Port A2',
            'code': 'PA2',
            'is_land': True,
        })

    def test_05_user_company_b_cannot_read_order_company_a(self):
        """Test 5: A user of company B cannot read an order of company A."""
        # Company A mein order banate hain:
        order_a = self.env['freight.shipping'].with_company(self.company_a).create({
            'shipper_id': self.partner.id,
            'consignee_id': self.partner.id,
            'order_type': 'export',
            'transport': 'land',
            'land_type': 'ftl',
            'loading_port': self.port_1.id,
            'discharge_port_id': self.port_2.id,
            'company_id': self.company_a.id,
        })

        # Ab Company B ka user (self.user_b) is order ko read karne ki koshish karega -> AccessError aana chahiye!
        with self.assertRaises(AccessError):
            order_a.with_user(self.user_b).read(['name'])