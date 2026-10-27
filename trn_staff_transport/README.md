# 🚐 Staff Transport Management (`trn_staff_transport`)

[![Odoo Version](https://img.shields.io/badge/Odoo-19.0-714B67?style=flat-square&logo=odoo&logoColor=white)](https://www.odoo.com)
[![License](https://img.shields.io/badge/License-LGPL--3-blue?style=flat-square)](https://www.gnu.org/licenses/lgpl-3.0.html)
[![Tests Passing](https://img.shields.io/badge/Tests-5%2F5%20Passing-brightgreen?style=flat-square)](#-automated-tests)

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

The module includes 5 automated unit test cases in `tests/test_staff_transport.py`:
1. `test_01_fleet_vehicle_capacity_and_trips`: Tests default vs override capacity and trips count smart button.
2. `test_02_route_capacity_and_occupancy`: Tests stop count, employee count, capacity, and occupancy % formula.
3. `test_03_employee_stop_constraints_and_onchange`: Tests cross-route stop validation error and onchange stop reset.
4. `test_04_route_actions_and_google_maps`: Tests view stops action, map view action, and Google Maps URL generator.
5. `test_05_multi_company_security_isolation`: Tests multi-company isolation blocking cross-company record access.

### Run Tests Command:
```bash
python odoo-bin -c /path/to/odoo.conf -d <db_name> --http-port=8070 --test-enable --test-tags=/trn_staff_transport --stop-after-init
```
Result: **5 Passed, 0 Failed, 0 Errors (100% Pass)**.
