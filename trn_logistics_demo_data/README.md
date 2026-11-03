# Logistics & Staff Transport Demo Data (`trn_logistics_demo_data`)

End-to-end master and operational demo data module for **Odoo 19** (`trn_freight`, `trn_staff_transport`, and `trn_freight_dashboard`).

## 📦 Loaded Demo Data (Ordered XML Pipeline)

1. **`data/01_partners_and_company.xml`**
   - Updates `base.main_company` to **Apex Global Logistics & Transport**.
   - Loads shippers/customers, international consignees, customs clearing agents, and carrier/haulage vendors.
2. **`data/02_ports_containers_catalog.xml`**
   - **8 Freight Ports**: Seaports (`PKKHI`, `PKBQM`, `AEJEA`, `DEHAM`), Airports (`OPKC`, `OMDB`), and Land Terminals (`PKLHE`, `PKTKM`).
   - **5 Freight Containers**: 20ft Standard Dry (`#01`, `#02`), 40ft High Cube, 40ft Reefer, and Air ULD LD3.
   - **3 Price Lists**, **4 Freight Services** with vendor lines, and **4 Freight Routes**.
3. **`data/03_freight_orders_demo.xml`**
   - **6 Freight Orders** across all operational stages (`Draft`, `Submitted`, `Confirmed`, `Invoiced`, `Done`, `Cancelled`).
   - Uses `<function>` tags to execute real workflow methods (`action_submit`, `action_confirm`, `action_create_invoice`, `action_done`, `action_cancel`) so container states (`reserved`/`available`), chatter notifications, and `account.move` customer invoices are authentically generated.
4. **`data/04_staff_transport_master.xml`**
   - Drivers and Lahore stop addresses with real GPS coordinates (`partner_latitude`, `partner_longitude`) for Leaflet Map & Google Maps integration.
   - **3 Fleet Vehicles** (`Toyota Hiace`, `Toyota Coaster`, `Hyundai Staria`) with capacity overrides.
   - **2 Transport Routes**, **6 Stops**, and **6 HR Employees** assigned to routes and pickup/drop-off stops.
5. **`data/05_staff_transport_operations.xml`**
   - **3 Transport Schedules** (Morning Pickup & Evening Drop-off shifts).
   - **4 Daily Trips** across `Completed`, `In Progress`, and `Planned` (generated via `generate.daily.trips.wizard`), with passengers in `Dropped`, `No Show`, `Boarded`, and `Expected` statuses.
   - **5 Vehicle Requests** across `Draft`, `Submitted`, `Approved`, `Assigned`, and `Done` states.

## 🧪 Automated Verification

Run the end-to-end verification test suite across all 4 modules:
```bash
odoo-bin -c odoo.conf -d <db_name> --test-tags=/trn_freight,/trn_staff_transport,/trn_freight_dashboard,/trn_logistics_demo_data --stop-after-init
```
