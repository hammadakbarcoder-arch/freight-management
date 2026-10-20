from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestFreightOrder(TransactionCase):

    def setUp(self):
        super().setUp()
        # 1. Dummy Partner (Shipper / Consignee / Vendor)
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})

        # 2. Dummy Ports (2 Land Ports, 1 Air-only Port)
        self.land_port_1 = self.env['freight.port'].create({
            'name': 'Lahore Port',
            'code': 'LHR',
            'is_land': True,
        })
        self.land_port_2 = self.env['freight.port'].create({
            'name': 'Karachi Port',
            'code': 'KHI',
            'is_land': True,
        })
        self.air_port = self.env['freight.port'].create({
            'name': 'Dubai Airport',
            'code': 'DXB',
            'is_air': True,
            'is_land': False,
        })

        # 3. Dummy Container, Product, Pricing, Route, Service
        self.container = self.env['freight.container'].create({
            'name': 'Container 20ft',
            'code': 'CNT-01',
            'size': 20.0,
            'volume': 33.0,
            'state': 'available',
        })
        self.product = self.env['product.product'].create({'name': 'Laptops'})
        self.pricing = self.env['freight.price'].create({
            'name': 'Standard Rate',
            'weight_price': 10.0,
            'volume_price': 20.0,
        })
        self.route = self.env['freight.routes'].create({
            'name': 'LHR-KHI Route',
            'land_price': 500.0,
            'air_price': 1000.0,
            'water_price': 300.0,
        })
        self.service = self.env['freight.service'].create({
            'name': 'Packing Service',
            'sale_price': 150.0,
        })

    def _create_order(self):
        """Helper method to create a basic Land Freight Order."""
        return self.env['freight.shipping'].create({
            'shipper_id': self.partner.id,
            'consignee_id': self.partner.id,
            'order_type': 'export',
            'transport': 'land',
            'land_type': 'ftl',
            'loading_port': self.land_port_1.id,
            'discharge_port_id': self.land_port_2.id,
        })

    def test_01_totals_calculated_correctly(self):
        """Test 1: Totals are calculated correctly."""
        order = self._create_order()

        self.env['freight.order.cargo'].create({
            'order_id': order.id,
            'container_id': self.container.id,
            'product_id': self.product.id,
            'billing_on': 'weight',
            'pricing_id': self.pricing.id,
            'weight': 50.0,
            'volume': 5.0,
        })
        self.env['freight.order.route'].create({
            'order_id': order.id,
            'route_id': self.route.id,
            'source_port_id': self.land_port_1.id,
            'destination_port_id': self.land_port_2.id,
        })
        self.env['freight.order.service'].create({
            'order_id': order.id,
            'vendor_id': self.partner.id,
            'service_id': self.service.id,
            'qty': 2.0,
            'sale': 150.0,
        })

        self.assertEqual(order.total_weight, 50.0)
        self.assertEqual(order.total_volume, 5.0)
        self.assertEqual(order.cargo_total, 500.0)
        self.assertEqual(order.routes_total, 500.0)
        self.assertEqual(order.service_total_sale, 300.0)

    def test_02_workflow_and_container_state(self):
        """Test 2: Submit -> Confirm -> Done changes order state and container state."""
        order = self._create_order()
        self.env['freight.order.cargo'].create({
            'order_id': order.id,
            'container_id': self.container.id,
            'product_id': self.product.id,
            'billing_on': 'weight',
            'pricing_id': self.pricing.id,
            'weight': 10.0,
        })

        self.assertEqual(order.state, 'draft')
        self.assertEqual(self.container.state, 'available')

        order.action_submit()
        self.assertEqual(order.state, 'submitted')

        order.action_confirm()
        self.assertEqual(order.state, 'confirmed')
        self.assertNotEqual(self.container.state, 'available')

        order.action_done()
        self.assertEqual(order.state, 'done')
        self.assertEqual(self.container.state, 'available')

    def test_03_wrong_port_refused(self):
        """Test 3: A wrong port for the transport type is refused."""
        order = self._create_order()
        with self.assertRaises(ValidationError):
            self.env['freight.order.route'].create({
                'order_id': order.id,
                'route_id': self.route.id,
                'source_port_id': self.air_port.id,
                'destination_port_id': self.land_port_2.id,
            })

    def test_04_delete_confirmed_order_refused(self):
        """Test 4: Deleting a confirmed order is refused."""
        order = self._create_order()
        order.action_submit()
        order.action_confirm()

        with self.assertRaises(UserError):
            order.unlink()