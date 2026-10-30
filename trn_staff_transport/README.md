# 🚐 Staff Transport Management (`trn_staff_transport`)

[![Odoo Version](https://img.shields.io/badge/Odoo-19.0-714B67?style=flat-square&logo=odoo&logoColor=white)](https://www.odoo.com)
[![License](https://img.shields.io/badge/License-LGPL--3-blue?style=flat-square)](https://www.gnu.org/licenses/lgpl-3.0.html)
[![Tests Passing](https://img.shields.io/badge/Tests-9%2F9%20Passing-brightgreen?style=flat-square)](#-automated-tests)

A specialized extension module for **Odoo 19** extending standard **Fleet** and **Employees (HR)** applications to manage corporate staff transport, daily commutes, route planning, vehicle seating capacity, and turn-by-turn navigation.

---

## 🌟 Key Features

* **Route & Stops Architecture**:
  * Manage comprehensive transport routes (`logistics.transport.route`) supporting `Pickup`, `Drop-off`, and `Both` direction schedules.
  * Stops model (`logistics.transport.stop`) with exact physical addresses (`res.partner`) and planned arrival times (`widget="float_time"`).
* **Interactive Drag-and-Drop Sequencing**:
  * Reorder stops easily by dragging handle icons (`widget="handle"`) in list views with automatic sequence persistence.
* **Dual Mapping Capabilities**:
  * **OpenStreetMap / Leaflet View**: Displays all route stops interactively with sequenced route lines (`routing="1"`).
  * **Google Maps GPS Navigation**: Single-click header action generating Google Maps directions with origin, destination, and intermediate waypoints.
* **Fleet Seating Capacity & Trips Counter**:
  * Extends `fleet.vehicle` with `seat_capacity_override` and computed `effective_capacity`.
  * Dedicated **Trips** smart button displaying the count of routes assigned to each vehicle.
* **Clean HR Employee XPath Integration**:
  * Injects a dedicated **"Transport"** tab into the standard employee form (`hr.view_employee_form`) without modifying standard views.
  * Real-time route stop assignment with strict `@api.constrains` preventing mismatched stops.
  * Dynamic `@api.onchange` automatically resetting invalid stops when a route is modified.
* **Live Route Occupancy Dashboard**:
  * Formula-driven vehicle capacity utilization:
    $$\text{Occupancy \%} = \frac{\text{Assigned Employees}}{\text{Vehicle Capacity}} \times 100$$
    rendered with Odoo's native visual percentage widget (`widget="percentage"`).
* **Odoo 19 Search Views**:
  * Predefined quick filters for `Pickup`, `Drop-off`, `Both`, and `Assigned Vehicle`.
  * Grouping by Direction, Vehicle, Driver, and Company.

---

## 🏗️ Models & Extensions

| Model | Type | Description |
| :--- | :--- | :--- |
| `logistics.transport.route` | New Master Model | Core route management, capacity tracking, chatter, and map actions. |
| `logistics.transport.stop` | New Child Model | Sequenced stops with drag handles, addresses, and map coordinates. |
| `logistics.transport.schedule` | New Model (Task 10) | Recurring weekly schedules with departure/arrival `float_time` and weekday selection. |
| `logistics.transport.trip` | New Model (Task 10) | Daily operational trips (`TRIP/YYYY/NNNN`) with live capacity, occupancy, and timestamps. |
| `logistics.transport.trip.passenger` | New Child Model (Task 10) | Passenger manifest with `Board`, `Drop`, and `No Show` actions and timestamps. |
| `generate.daily.trips.wizard` | Transient Model (Task 10) | Idempotent batch generator creating daily trips for active weekday schedules. |
| `logistics.transport.vehicle.request` | New Model (Task 10) | Staff ad-hoc vehicle requests (`VR/YYYY/NNNN`) with manager approval and overlap checks. |
| `fleet.vehicle` | Model Extension (`_inherit`) | Added seating override, effective capacity, and active trips counter. |
| `hr.employee` | Model Extension (`_inherit`) | Transport tab, pickup/dropoff stops, constraints, and onchange clearing. |

---

## 🛡️ Access Rights & Security

* **Transport User (`group_staff_transport_user`)**:
  * Can view routes, stops, and assign employee transport (`1, 1, 1, 0`).
  * Record deletion is strictly blocked.
* **Transport Administrator (`group_staff_transport_manager`)**:
  * Full administrative privileges including route and stop deletion (`1, 1, 1, 1`).
* **Multi-Company Tenancy**:
  * Both routes and stops enforce company isolation rules:
    ```xml
    ['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]
    ```

---

## 🧪 Automated Tests

The module includes **9 automated unit test cases** across `tests/test_staff_transport.py` (Task 9) and `tests/test_transport_operations.py` (Task 10):
1. `test_01_fleet_vehicle_capacity_and_trips`: Tests default vs override capacity and trips count smart button.
2. `test_02_route_capacity_and_occupancy`: Tests stop count, employee count, capacity, and occupancy % formula.
3. `test_03_employee_stop_constraints_and_onchange`: Tests cross-route stop validation error and onchange stop reset.
4. `test_04_route_actions_and_google_maps`: Tests view stops action, map view action, and Google Maps URL generator.
5. `test_05_multi_company_security_isolation`: Tests multi-company isolation blocking cross-company record access.
6. `test_01_schedule_constraints_and_weekdays`: Tests `arrival > departure`, weekday selection, and `float_time` to UTC conversion.
7. `test_02_trip_lifecycle_and_passenger_attendance`: Tests trip sequence, capacity, timestamps (`actual_departure_time`, `actual_arrival_time`), and passenger `Board` / `Drop` / `No Show`.
8. `test_03_generate_daily_trips_wizard_idempotency`: Tests wizard trip generation for active weekday schedules and idempotency (no duplicates on re-run).
9. `test_04_vehicle_request_workflow_overlap_and_security`: Tests vehicle request date validation, manager-only approval, self-approval block, vehicle booking overlap detection, and `unlink` protection.

### Run Tests Command:
```bash
python odoo-bin -c /path/to/odoo.conf -d <db_name> --http-port=8072 --test-tags=/trn_staff_transport --stop-after-init
```
Result: **9 Passed, 0 Failed, 0 Errors (100% Pass)**.

---

## 📖 Task 10 Review Questions

1. **How do you combine a `Date` and a `float_time` (e.g., `7.5` for `07:30`) into a UTC `Datetime` for Odoo?**
   - Extract hours (`int(val)`) and minutes (`int(round((val - hours) * 60))`), combine with `target_date` using `datetime.combine(target_date, time(hours, minutes))`, localize in the user's timezone (`pytz.timezone(self.env.user.tz or 'UTC').localize(naive_dt)`), convert to UTC (`.astimezone(pytz.utc)`), and strip `tzinfo` (`.replace(tzinfo=None)`) for Odoo's naive UTC `fields.Datetime`.
2. **How do you make the "Generate Daily Trips" wizard idempotent so running it twice for the same date doesn't create duplicate trips?**
   - Before creating a trip for each matching schedule on `self.date`, search `logistics.transport.trip` with domain `[('date', '=', self.date), ('schedule_id', '=', sched.id), ('state', '!=', 'cancelled')]`. If a record exists, skip (`continue`).
3. **What is the condition to check if two datetime intervals $[A_{\text{start}}, A_{\text{end}}]$ and $[B_{\text{start}}, B_{\text{end}}]$ overlap?**
   - Two intervals overlap if and only if $A_{\text{start}} < B_{\text{end}}$ AND $A_{\text{end}} > B_{\text{start}}$. In Odoo domain syntax: `[('from_datetime', '<', rec.to_datetime), ('to_datetime', '>', rec.from_datetime)]`.
4. **How do you prevent a manager from approving their own vehicle request?**
   - Compare the requester employee's linked user (`rec.sudo().employee_id.user_id`) with `self.env.user` inside `action_approve()`. If they match, raise a `UserError`.

