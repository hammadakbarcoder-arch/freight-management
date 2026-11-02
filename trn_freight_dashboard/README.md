# 📊 Freight Dashboard (`trn_freight_dashboard`)

[![Odoo Version](https://img.shields.io/badge/Odoo-19.0-714B67?style=flat-square&logo=odoo&logoColor=white)](https://www.odoo.com)
[![Framework](https://img.shields.io/badge/Frontend-OWL%202.0-00A09D?style=flat-square)](https://github.com/odoo/owl)
[![Tests Passing](https://img.shields.io/badge/Tests-Passing-brightgreen?style=flat-square)](#-automated-tests)

An interactive executive dashboard built with **Odoo 19's OWL (Odoo Web Library)** framework for the `trn_freight` module.

---

## 🌟 Key Features

* **Server-Side SQL Aggregation (`freight.dashboard`)**:
  * Uses Odoo 19's `_read_group()` API to compute order counts per state, active shipment revenue (`cargo_total + routes_total + service_total_sale`), expense (`service_total_sale`), net profit margin, and 6-month historical trends in milliseconds.
* **OWL 2 Component & Client Action**:
  * Registered in `registry.category("actions")` under tag `trn_freight_dashboard.dashboard`.
  * Uses `setup()`, `useState()`, `onWillStart()`, `useService("orm")`, and `useService("action")`.
* **Interactive Drill-Down KPI Cards**:
  * Clicking any financial KPI card or pipeline status card (`Draft`, `Submitted`, `Confirmed`, `Invoiced`, `Done`, `Cancelled`) opens the filtered `freight.shipping` list view.
* **6-Month Revenue vs. Expense Chart**:
  * Responsive grouped bar chart comparing monthly shipment billings against vendor service expenses.

---

## 📖 Review Questions & Answers

1. **Why do the totals get calculated in Python and not in JavaScript?**
   - Calculating totals in Python via PostgreSQL (`_read_group`) aggregates thousands of rows directly in the database engine and sends only a tiny summary dictionary over the network. Computing totals in JavaScript would require downloading all order records to the browser (`searchRead`), causing high latency, excessive memory usage, and slow rendering.
2. **What is an asset bundle, and why must you update the module after changing it?**
   - An asset bundle (such as `web.assets_backend`) is a pre-compiled, concatenated, and minified collection of JS, QWeb XML, and SCSS/CSS files cached in the database (`ir.attachment`). When adding new asset paths in `__manifest__.py`, upgrading the module (`-u`) updates the stored manifest metadata and invalidates the cached bundle so Odoo regenerates it.
3. **`search_read` + `sum` vs. `read_group` (`_read_group`): which one is better for totals, and why?**
   - `read_group` / `_read_group` is far better because it executes a single SQL `SELECT ... SUM(...), COUNT(*) GROUP BY ...` query inside PostgreSQL ($O(1)$ rows transferred), whereas `search_read` + `sum` fetches every individual record into Python/JS memory ($O(N)$ data transfer and memory overhead).
