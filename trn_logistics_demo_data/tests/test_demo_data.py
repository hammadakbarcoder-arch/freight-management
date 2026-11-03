# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestLogisticsDemoData(TransactionCase):

    def test_01_demo_data_end_to_end_verification(self):
        """Verify master, freight operational, and staff transport demo records & workflow states."""
        # 1. Verify Company & Master Data
        main_company = self.env.ref('base.main_company')
        self.assertEqual(main_company.name, 'Apex Global Logistics & Transport')

        port_khi = self.env.ref('trn_logistics_demo_data.port_karachi_sea')
        self.assertTrue(port_khi.is_water)

        # 2. Verify 6 Freight Orders across all 6 workflow states
        order_draft = self.env.ref('trn_logistics_demo_data.freight_order_demo_1_draft')
        order_sub = self.env.ref('trn_logistics_demo_data.freight_order_demo_2_submitted')
        order_conf = self.env.ref('trn_logistics_demo_data.freight_order_demo_3_confirmed')
        order_inv = self.env.ref('trn_logistics_demo_data.freight_order_demo_4_invoiced')
        order_done = self.env.ref('trn_logistics_demo_data.freight_order_demo_5_done')
        order_canc = self.env.ref('trn_logistics_demo_data.freight_order_demo_6_cancelled')

        self.assertEqual(order_draft.state, 'draft')
        self.assertEqual(order_sub.state, 'submitted')
        self.assertEqual(order_conf.state, 'confirmed')
        self.assertEqual(order_inv.state, 'invoiced')
        self.assertEqual(order_done.state, 'done')
        self.assertEqual(order_canc.state, 'cancelled')

        # 3. Verify workflow side-effects (Container reservation/release & Invoices)
        cntr_reserved = self.env.ref('trn_logistics_demo_data.container_40ft_hc_1')
        cntr_released = self.env.ref('trn_logistics_demo_data.container_20ft_std_2')
        self.assertEqual(cntr_reserved.state, 'reserved')
        self.assertEqual(cntr_released.state, 'available')
        self.assertEqual(order_inv.invoice_count, 1)
        self.assertEqual(order_done.invoice_count, 1)

        # 4. Verify Staff Transport Trips & Passenger Statuses
        trip_completed = self.env.ref('trn_logistics_demo_data.trip_demo_1_completed')
        trip_in_prog = self.env.ref('trn_logistics_demo_data.trip_demo_2_in_progress')
        self.assertEqual(trip_completed.state, 'completed')
        self.assertEqual(trip_in_prog.state, 'in_progress')

        pax_bilal = self.env.ref('trn_logistics_demo_data.pax_trip1_bilal')
        pax_ayesha = self.env.ref('trn_logistics_demo_data.pax_trip1_ayesha')
        pax_zain = self.env.ref('trn_logistics_demo_data.pax_trip2_zain')
        self.assertEqual(pax_bilal.status, 'dropped')
        self.assertEqual(pax_ayesha.status, 'no_show')
        self.assertEqual(pax_zain.status, 'boarded')

        # 5. Verify Vehicle Requests across workflow states
        vr_draft = self.env.ref('trn_logistics_demo_data.veh_req_demo_1_draft')
        vr_sub = self.env.ref('trn_logistics_demo_data.veh_req_demo_2_submitted')
        vr_app = self.env.ref('trn_logistics_demo_data.veh_req_demo_3_approved')
        vr_ass = self.env.ref('trn_logistics_demo_data.veh_req_demo_4_assigned')
        vr_done = self.env.ref('trn_logistics_demo_data.veh_req_demo_5_done')

        self.assertEqual(vr_draft.state, 'draft')
        self.assertEqual(vr_sub.state, 'submitted')
        self.assertEqual(vr_app.state, 'approved')
        self.assertEqual(vr_ass.state, 'assigned')
        self.assertEqual(vr_done.state, 'done')
