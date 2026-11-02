# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFreightDashboard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Dashboard = self.env['freight.dashboard']
        self.Order = self.env['freight.shipping']

        self.shipper = self.env['res.partner'].create({'name': 'Test Shipper'})
        self.consignee = self.env['res.partner'].create({'name': 'Test Consignee'})
        self.vendor = self.env['res.partner'].create({'name': 'Test Vendor'})

        self.port_a = self.env['freight.port'].create({
            'name': 'Karachi Port', 'code': 'KHI-01', 'is_land': True,
        })
        self.port_b = self.env['freight.port'].create({
            'name': 'Lahore Dry Port', 'code': 'LHE-01', 'is_land': True,
        })
        self.container = self.env['freight.container'].create({
            'name': 'CNT-DASH-01', 'code': 'CNT-D01', 'size': 20.0, 'volume': 30.0, 'state': 'available',
        })
        self.product = self.env['product.product'].create({'name': 'Electronics Cargo'})
        self.pricing = self.env['freight.price'].create({
            'name': 'Standard Pricing', 'weight_price': 10.0, 'volume_price': 5.0,
        })
        self.route_master = self.env['freight.routes'].create({
            'name': 'KHI to LHE Land', 'land_price': 500.0,
        })
        self.service_master = self.env['freight.service'].create({
            'name': 'Loading Handling', 'sale_price': 200.0,
        })

    def test_01_dashboard_aggregation_and_cancelled_exclusion(self):
        """Test dashboard state counts, revenue, expense, margin, and 6-month trend."""
        before = self.Dashboard.get_dashboard_data()

        # Create 1 active order (Cargo = 100 * 10 = 1000, Route = 500, Service = 200)
        order = self.Order.create({
            'shipper_id': self.shipper.id,
            'consignee_id': self.consignee.id,
            'order_type': 'import',
            'transport': 'land',
            'land_type': 'ftl',
            'loading_port': self.port_a.id,
            'discharge_port_id': self.port_b.id,
            'cargo_ids': [(0, 0, {
                'container_id': self.container.id,
                'product_id': self.product.id,
                'billing_on': 'weight',
                'pricing_id': self.pricing.id,
                'weight': 100.0,
            })],
            'route_ids': [(0, 0, {
                'route_id': self.route_master.id,
                'source_port_id': self.port_a.id,
                'destination_port_id': self.port_b.id,
            })],
            'service_ids': [(0, 0, {
                'vendor_id': self.vendor.id,
                'service_id': self.service_master.id,
                'qty': 1.0,
                'sale': 200.0,
            })],
        })

        after = self.Dashboard.get_dashboard_data()
        self.assertEqual(after['total_orders'], before['total_orders'] + 1)
        self.assertEqual(after['active_orders'], before['active_orders'] + 1)
        self.assertEqual(after['orders_by_state']['draft'], before['orders_by_state']['draft'] + 1)

        # Revenue increased by 1000 + 500 + 200 = 1700; Expense increased by 200; Margin by 1500
        self.assertAlmostEqual(after['total_revenue'], before['total_revenue'] + 1700.0, places=2)
        self.assertAlmostEqual(after['total_expense'], before['total_expense'] + 200.0, places=2)
        self.assertAlmostEqual(after['net_margin'], before['net_margin'] + 1500.0, places=2)
        self.assertEqual(len(after['monthly_data']), 6)

        # Cancel the order -> should be excluded from active revenue/expense
        order.action_cancel()
        after_cancel = self.Dashboard.get_dashboard_data()
        self.assertEqual(after_cancel['active_orders'], before['active_orders'])
        self.assertAlmostEqual(after_cancel['total_revenue'], before['total_revenue'], places=2)
