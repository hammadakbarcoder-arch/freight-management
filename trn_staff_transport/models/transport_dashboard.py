# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class TransportDashboard(models.AbstractModel):
    _name = 'transport.dashboard'
    _description = 'Staff Transport Management Backend Analytics & Dashboard Model'

    @api.model
    def _get_company_domain(self):
        """Scoping domain for multi-company isolation."""
        company_ids = self.env.companies.ids if self.env.companies else [self.env.company.id]
        return ['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]

    @api.model
    def get_kpis(self, date_from=None, date_to=None):
        """Compute the core 6 operational KPIs for Staff Transport."""
        Trip = self.env['logistics.transport.trip']
        Request = self.env['logistics.transport.vehicle.request']
        Fleet = self.env['fleet.vehicle']

        company_domain = self._get_company_domain()
        trip_domain = list(company_domain)
        if date_from and date_from != 'all':
            trip_domain.append(('date', '>=', date_from))
        if date_to and date_to != 'all':
            trip_domain.append(('date', '<=', date_to))

        req_domain = list(company_domain)
        if date_from and date_from != 'all':
            req_domain.append(('from_datetime', '>=', f"{date_from} 00:00:00"))
        if date_to and date_to != 'all':
            req_domain.append(('from_datetime', '<=', f"{date_to} 23:59:59"))

        # Trip state counts
        trip_counts = {
            'draft': 0,
            'planned': 0,
            'in_progress': 0,
            'completed': 0,
            'cancelled': 0,
        }
        for state_val, count in Trip._read_group(trip_domain, ['state'], ['__count']):
            if state_val in trip_counts:
                trip_counts[state_val] = count

        total_trips = sum(trip_counts.values())
        active_trips = total_trips - trip_counts['cancelled']

        # Pending Vehicle Requests (Draft or Submitted)
        pending_requests_cnt = Request.search_count(req_domain + [('state', 'in', ['draft', 'submitted'])])

        # Active Fleet
        active_trips_rec = Trip.search(trip_domain + [('state', '!=', 'cancelled')])
        assigned_vehicles = active_trips_rec.mapped('vehicle_id')
        total_fleet_cnt = Fleet.search_count(company_domain)
        active_fleet_cnt = len(assigned_vehicles) or total_fleet_cnt

        # Occupancy Rate %
        occupancy_sum = 0.0
        trips_with_cap = 0
        total_passengers = 0
        for trip in active_trips_rec:
            total_passengers += trip.passenger_count
            if trip.capacity > 0:
                occupancy_sum += (trip.occupancy_percent or 0.0)
                trips_with_cap += 1
        avg_occupancy_pct = round((occupancy_sum / trips_with_cap) * 100, 1) if trips_with_cap > 0 else 0.0

        return {
            'total_trips': total_trips,
            'active_trips': active_trips,
            'in_progress_trips': trip_counts['in_progress'],
            'completed_trips': trip_counts['completed'],
            'planned_trips': trip_counts['planned'],
            'draft_trips': trip_counts['draft'],
            'cancelled_trips': trip_counts['cancelled'],
            'pending_requests': pending_requests_cnt,
            'active_fleet': active_fleet_cnt,
            'total_fleet': total_fleet_cnt,
            'total_passengers': total_passengers,
            'occupancy_rate_pct': avg_occupancy_pct,
            'trip_counts': trip_counts,
        }

    @api.model
    def get_route_analytics(self, limit=5):
        """Top routes grouped by trip volume with distribution percentages."""
        Trip = self.env['logistics.transport.trip']
        company_domain = self._get_company_domain()
        route_palette = ['#f97316', '#3b82f6', '#10b981', '#ea580c', '#8b5cf6']

        route_groups = Trip.sudo()._read_group(
            company_domain + [('state', '!=', 'cancelled')],
            ['route_id'],
            ['__count']
        )
        sorted_routes = sorted(route_groups, key=lambda x: x[1], reverse=True)[:limit]
        max_route_count = sorted_routes[0][1] if sorted_routes else 1
        top_routes = []
        for idx, (route_record, cnt) in enumerate(sorted_routes):
            r_name = route_record.sudo().name if route_record else 'Unassigned Route'
            pct = max(10, min(100, round((cnt / max_route_count) * 100)))
            top_routes.append({
                'id': route_record.id if route_record else False,
                'name': r_name,
                'count': cnt,
                'percentage': pct,
                'color': route_palette[idx % len(route_palette)],
            })
        return top_routes

    @api.model
    def get_pipeline_summary(self):
        """Pipeline counts for vehicle requests lifecycle."""
        Request = self.env['logistics.transport.vehicle.request']
        company_domain = self._get_company_domain()

        req_counts = {
            'draft': 0,
            'submitted': 0,
            'approved': 0,
            'assigned': 0,
            'done': 0,
            'rejected': 0,
            'cancelled': 0,
        }
        for state_val, count in Request._read_group(company_domain, ['state'], ['__count']):
            if state_val in req_counts:
                req_counts[state_val] = count

        return {
            'draft': req_counts['draft'],
            'submitted': req_counts['submitted'],
            'approved': req_counts['approved'],
            'assigned': req_counts['assigned'],
            'done': req_counts['done'],
            'pending_approvals': req_counts['submitted'],
            'pending_assignments': req_counts['approved'],
        }

    @api.model
    def get_operational_alerts(self):
        """Real-time operational alerts for unassigned trips, over-capacity, and pending approvals."""
        Trip = self.env['logistics.transport.trip']
        Request = self.env['logistics.transport.vehicle.request']
        company_domain = self._get_company_domain()

        over_capacity_cnt = Trip.search_count(company_domain + [
            ('over_capacity', '=', True),
            ('state', 'in', ['planned', 'in_progress'])
        ])
        unassigned_trips_cnt = Trip.search_count(company_domain + [
            ('state', 'in', ['planned', 'in_progress']),
            '|', ('driver_id', '=', False), ('vehicle_id', '=', False)
        ])
        pending_approval_cnt = Request.search_count(company_domain + [('state', '=', 'submitted')])

        return {
            'over_capacity': over_capacity_cnt,
            'unassigned_trips': unassigned_trips_cnt,
            'pending_approvals': pending_approval_cnt,
        }

    @api.model
    def get_top_drivers(self, limit=5):
        """Top driver rankings by assigned trip counts."""
        Trip = self.env['logistics.transport.trip']
        company_domain = self._get_company_domain()

        driver_groups = Trip.sudo()._read_group(
            company_domain + [('driver_id', '!=', False), ('state', '!=', 'cancelled')],
            ['driver_id'],
            ['__count']
        )
        sorted_drivers = sorted(driver_groups, key=lambda x: x[1], reverse=True)[:limit]
        max_driver_trips = sum(cnt for _, cnt in sorted_drivers) or 1
        top_drivers = []
        for rank, (driver_record, cnt) in enumerate(sorted_drivers, start=1):
            pct = round((cnt / max_driver_trips) * 100)
            top_drivers.append({
                'rank': rank,
                'id': driver_record.id if driver_record else False,
                'name': driver_record.sudo().name if driver_record else 'Driver',
                'count': cnt,
                'percentage': pct,
            })
        return top_drivers

    @api.model
    def get_timeline_analytics(self, months=12):
        """12-month historical trend of trips, completed trips, requests, and passengers."""
        Trip = self.env['logistics.transport.trip']
        Request = self.env['logistics.transport.vehicle.request']
        company_domain = self._get_company_domain()

        now = datetime.now()
        chart_data = []
        for i in range(months - 1, -1, -1):
            m_date = now - relativedelta(months=i)
            m_start = m_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_m = m_start + relativedelta(months=1)
            m_end = next_m - relativedelta(seconds=1)

            m_trip_domain = company_domain + [
                ('date', '>=', m_start.date()),
                ('date', '<=', m_end.date()),
            ]
            m_trips = Trip.search(m_trip_domain)
            m_total_trips = len(m_trips)
            m_completed = sum(1 for t in m_trips if t.state == 'completed')
            m_passengers = sum(t.passenger_count for t in m_trips)

            m_req_domain = company_domain + [
                ('from_datetime', '>=', m_start),
                ('from_datetime', '<=', m_end),
            ]
            m_req_cnt = Request.search_count(m_req_domain)

            chart_data.append({
                'label': m_date.strftime('%b'),
                'full_label': m_date.strftime('%B %Y'),
                'total_trips': m_total_trips,
                'completed': m_completed,
                'requests': m_req_cnt,
                'passengers': m_passengers,
            })
        return chart_data

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None, status=None):
        """Unified method returning all transport metrics in one call."""
        Trip = self.env['logistics.transport.trip']
        Request = self.env['logistics.transport.vehicle.request']
        company_domain = self._get_company_domain()

        kpis = self.get_kpis(date_from=date_from, date_to=date_to)
        active_trips = kpis['active_trips']
        completed_trips = kpis['completed_trips']
        completion_rate_pct = round((completed_trips / active_trips) * 100, 1) if active_trips > 0 else 0.0
        tracked_states_count = sum(1 for c in kpis['trip_counts'].values() if c > 0)

        # Recent Trips (Last 6)
        recent_trips = []
        for t in Trip.search(company_domain, order='date desc, id desc', limit=6):
            t_sudo = t.sudo()
            r_str = t_sudo.route_id.name if t_sudo.route_id else 'Direct Trip'
            driver_str = t_sudo.driver_id.name if t_sudo.driver_id else 'Unassigned'
            vehicle_str = t_sudo.vehicle_id.name if t_sudo.vehicle_id else 'No Vehicle'
            recent_trips.append({
                'id': t.id,
                'name': t.name,
                'route': r_str,
                'driver': driver_str,
                'vehicle': vehicle_str,
                'state': t.state,
                'passengers': t.passenger_count,
            })

        # Recent Vehicle Requests (Last 6)
        recent_requests = []
        for r in Request.search(company_domain, order='from_datetime desc, id desc', limit=6):
            r_sudo = r.sudo()
            emp_str = r_sudo.employee_id.name if r_sudo.employee_id else 'Employee'
            v_str = r_sudo.vehicle_id.name if r_sudo.vehicle_id else 'TBD'
            recent_requests.append({
                'id': r.id,
                'name': r.name,
                'requester': emp_str,
                'vehicle': v_str,
                'purpose': r.purpose or 'Official Transport',
                'state': r.state,
            })

        return {
            **kpis,
            'completion_rate_pct': completion_rate_pct,
            'tracked_states_count': tracked_states_count,
            'chart_12m': self.get_timeline_analytics(months=12),
            'top_routes': self.get_route_analytics(limit=5),
            'booking_pipeline': self.get_pipeline_summary(),
            'recent_trips': recent_trips,
            'recent_requests': recent_requests,
            'alerts': self.get_operational_alerts(),
            'top_drivers': self.get_top_drivers(limit=5),
        }
