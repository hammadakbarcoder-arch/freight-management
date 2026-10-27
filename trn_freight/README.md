# 🚢 Freight Management System (`trn_freight`)

[![Odoo Version](https://img.shields.io/badge/Odoo-19.0-714B67?style=flat-square&logo=odoo&logoColor=white)](https://www.odoo.com)
[![License](https://img.shields.io/badge/License-LGPL--3-blue?style=flat-square)](https://www.gnu.org/licenses/lgpl-3.0.html)
[![Tests Passing](https://img.shields.io/badge/Tests-11%2F11%20Passing-brightgreen?style=flat-square)](#-automated-tests)

A comprehensive, modular Freight Management System (FMS) built for **Odoo 19** to manage and streamline end-to-end logistics operations across **Land (FTL/LTL)**, **Air**, and **Water/Ocean (FCL/LCL)** transport modes.

---

## 🌟 Key Features

* **Multi-Modal Shipping**: Support for Land (`FTL`/`LTL`), Air, and Water (`FCL`/`LCL`).
* **Dynamic Pricing Engine**: Automated calculation of cargo costs based on Weight (per KG) or Volume (per CBM).
* **Port Transport Verification**: Strict constraints preventing incompatible port selection (e.g. airport for sea freight).
* **Smart Container Tracking**: Auto-reserves containers when order is confirmed (`available` ➔ `reserved`), and frees them when completed (`reserved` ➔ `available`).
* **Customs Clearance Gatekeeper**: Shipments cannot be confirmed without an approved Customs Clearance.
* **Audit Revision Wizard**: Interactive popup wizard for customs revisions (`REV-01`, `REV-02`) with reason logging.
* **Integrated Invoicing Engine**: Automated generation of Odoo Customer Invoices (`account.move`) from confirmed shipments with line-item conversion (Cargo, Routes, Services).
* **Backend Data Integrity Locks**: Python-level restrictions blocking add/edit/delete of cargo on confirmed orders, and routes/services on invoiced orders.
* **Live Milestone Tracking & Chatter Notifications**: Checkpoint logging with source, destination, transport mode, and status (`Received` / `Delivered`) with automated chatter updates to Shipper, Consignee, and Agent.
* **QWeb PDF Reports**: Printable, multi-page ready Freight Order summary and Tracking Timeline reports with dynamic currency formatting and repeating table headers accessible directly from the Print action menu.
* **Multi-Company Compliant**: Built from the ground up with `res.company` record rules and stored related company fields.

---

## 🏗️ Architecture & Models

| Model | Description |
| :--- | :--- |
| `freight.shipping` | Master shipment model managing lifecycle (`draft` ➔ `submitted` ➔ `confirmed` ➔ `done`), cargo lines, route legs, services, and invoice reconciliation. |
| `custom.clearance` | Regulatory customs compliance holding cargo declarations, document attachments, and approval state machines. |
| `custom.clearance.revision` | Audit trail recording revision increments and reasons. |
| `custom.clearance.revision.wizard` | Transient wizard managing interactive revision submissions. |
| `freight.port` | Seaports, airports, and inland dry ports with transport validation flags (`is_land`, `is_air`, `is_water`). |
| `freight.container` | Container registry managing dimensional specs (20ft, 40ft, Reefer) and real-time state (`available`, `reserved`). |
| `freight.price` | Dynamic rating matrix calculating rate charges based on Volume (CBM) or Weight (KG). |
| `freight.routes` | Multi-leg route segment library linking transit legs and pricing. |
| `freight.service` | Catalog of ancillary logistics services (Handling, Fumigation, Storage). |
| `freight.order.cargo` | Line items defining shipment goods, weight, volume, container assignment, and total cost. |
| `freight.order.route` | Line items tracking individual journey legs, transport modes, and transit costs. |
| `freight.order.service` | Line items tracking billable ancillary services. |
| `freight.order.track` | Live checkpoint tracking lines logging milestone progress. |

---

## 🛡️ Security & Multi-Company Architecture

### Security Groups
* **Freight User (`base.group_user`)**: Read and write access to orders, lines, and clearances (`1, 1, 1, 0`).
* **Freight Manager (`group_freight_manager`)**: Administrative privileges including delete operations and configuration management (`1, 1, 1, 1`).

### Multi-Company Isolation
All primary and child models enforce company-level data isolation:
* `freight.shipping`, `custom.clearance`, `freight.container`, `freight.port`, `freight.routes`, `freight.price`, and `freight.service` maintain explicit `company_id` fields with record rules:
  ```xml
  ['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]
  ```
* Child line models utilize stored related fields (`related='order_id.company_id', store=True`) to guarantee performant and secure query filtering.

---

## 🧪 Automated Testing

Automated test suites ensure regression-free stability:
* **`test_freight_order.py`**:
  * Sequence generation on create.
  * Cargo price computations (weight-based vs volume-based).
  * Port transport mode validation constraints.
  * Order lifecycle progression (`draft` ➔ `submitted` ➔ `confirmed` ➔ `done`).
  * Container state reservation and auto-release.
  * Customs clearance requirement enforcement on order confirmation.
  * Order and clearance deletion constraints.
  * Customer invoice creation and financial reconciliation (`amount_untaxed` = order totals).
  * Backend line locks enforcement (`create`, `write`, `unlink` refusal on locked states).
  * Live tracking line creation and chatter notification posting.
  * Freight Order and Tracking PDF report QWeb generation rendering.
* **`test_security.py`**:
  * Multi-company record rule isolation across different company environments.

Run tests using the Odoo CLI:
```bash
odoo-bin -c /path/to/odoo.conf -d <database_name> --http-port=8070 --test-enable --test-tags=/trn_freight --stop-after-init
```
