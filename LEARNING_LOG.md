# Freight Management System - Senior Interview & Viva Preparation Guide

Yeh document Freight Management System (`trn_freight`) ke tamam tasks (Task 1 se le kar Task 6) ke **"Be ready to answer"** questions aur **Senior Developer Viva Questions** ke 100% solid, technical jawabaat par mushtamil hai.

---

## 📌 Section 1: Exact Task Questions ("Be Ready to Answer")

---

### Q1: Access Rights (ir.model.access.csv) aur Record Rules (ir.rule) mein kya farq hai? Dono kya control karte hain?

* **⚡ 1-Liner Answer:** 
  > **Access Rights model level (table level) par CRUD permissions control karte hain, jabke Record Rules row level (record level) par visibility aur SQL domain filtering control karte hain.**
* **🔬 In-Depth Explanation:**
  * **Access Rights (`ir.model.access.csv`):** Yeh decide karta hai ke kisi User Group (jaise `base.group_user` ya `group_freight_manager`) ko kisi model par Create, Read, Write, ya Delete (CRUD) ki ijazat hai ya nahi. Yeh poori table par lagta hai. Agar user ke paas Read access na ho to wo table ka aik bhi record nahi dekh sakta.
  * **Record Rules (`ir.rule`):** Yeh database queries mein dynamic `WHERE` clause ki tarah add hote hain. Yeh decide karte hain ke user table ke *kaunse specific records* dekh ya edit kar sakta hai (misal ke tor par: "Sirf apni company ke records dekhe").
* **⚠️ Senior Trap:** Agar Access Right mana kar de, to Odoo Record Rule check hi nahi karta, pehle hi `AccessError` throw kar deta hai.

---

### Q2: Aik automated test aapke working database par pass ho jaye lekin naye fresh database par fail kyun ho sakta hai?

* **⚡ 1-Liner Answer:** 
  > **Kyunke working database mein manual settings, dependencies, demo records, ya sequences pehle se exist karte hain jo naye database mein missing hote hain.**
* **🔬 In-Depth Explanation:**
  1. **Missing Master Data:** Working DB mein aapne UI se Port, Currency, ya Containers banaye hote hain. Naye DB mein test chalte waqt wo data tab tak exist nahi karta jab tak test case ke `setUpClass` mein code se create na kiya jaye.
  2. **Unlisted Dependencies:** Agar koi module (jaise `product` ya `uom`) aapke working DB mein installed tha lekin `__manifest__.py` ki `'depends'` list mein dalna bhool gaye, to fresh DB par module install hote waqt crash ho jayega.
  3. **Hardcoded Sequences:** Working DB mein sequence `FO/00100` par ho sakti hai jabke fresh DB mein `FO/00001` banti hai. Agar test mein hardcoded string match ki ho to fail ho jayega.
  4. **Transaction Rollback:** Odoo ke `TransactionCase` tests har test ke baad rollback karte hain.

---

### Q3: `sudo()` method kya skip karta hai, aur normal code mein iska istemal dangerous kyun hai?

* **⚡ 1-Liner Answer:** 
  > **`sudo()` current user ke context ko bypass kar ke Superuser (System Admin) ban jata hai, jo Access Rights aur Record Rules dono ko skip kar deta hai.**
* **🔬 In-Depth Explanation:**
  * Jab `self.env['model'].sudo()` call hota hai, to environment mein `uid = SUPERUSER_ID` (User ID 1) set ho jata hai.
  * Yeh 2 cheezein bypass karta hai:
    1. `ir.model.access.csv` check nahi hota.
    2. `ir.rule` (Multi-Company aur user filters) check nahi hote.
  * **Dangerous kyun hai?**
    * **Data Leakage:** Aik company ka user doosri company ka confidential data dekh sakta hai.
    * **Privilege Escalation:** Standard user wo records delete ya change kar sakta hai jo sirf manager ko allowed theen.
    * **Hidden Bugs:** Security bugs chhupe rehte hain kyunke sudo sab kuch allow kar deta hai.
* **Best Practice:** Business code mein `sudo()` ke bajaye `with_user(user)` ya `with_company(company)` use karein.

---

### Q4: Customs Clearance Revision Wizard `TransientModel` kyun hai? Iske records ke sath database mein kya hota hai?

* **⚡ 1-Liner Answer:** 
  > **`TransientModel` temporary dialog / wizard ke liye design kiya gaya hai; iska data temporary hota hai aur Odoo ka vacuum cron job iske purane records ko database se automatically delete kar deta hai.**
* **🔬 In-Depth Explanation:**
  * `models.Model` ka data permanent store hota hai (business transactions).
  * `models.TransientModel` sirf user se input lene (jaise Reason, Date range, Confirmation) ke liye hota hai.
  * Odoo mein ek built-in vacuum cron job (`ir.autovacuum`) hota hai jo har thori der baad run hota hai aur TransientModel ke un records ko delete kar deta hai jo kuch ghante purane ho chuke hon.
  * Is se database par temporary popup data ka load nahi banta.

---

### Q5: Kisi button method se doosra form ya screen open karne ke liye method kya return karta hai?

* **⚡ 1-Liner Answer:** 
  > **Button method aik Action Dictionary (`ir.actions.act_window`) return karta hai jisme `type`, `res_model`, `view_mode`, `res_id`, aur `target` define hota hai.**
* **🔬 In-Depth Explanation:**
  ```python
  return {
      'name': 'Custom Clearance',
      'type': 'ir.actions.act_window',
      'res_model': 'custom.clearance',
      'res_id': clearance.id,
      'view_mode': 'form',
      'target': 'current',  # 'current' = full page navigate; 'new' = modal popup
  }
  ```
  * `target: 'current'` screen ko us record par le jata hai.
  * `target: 'new'` screen par modal popup window kholta hai (jaise wizard).

---

## 🏗️ Section 2: Core Architecture & Freight Business Logic

---

### Q6: Freight Order ka State Machine aur `_ensure_state` method kaise kaam karta hai?

* **⚡ 1-Liner Answer:**
  > **`_ensure_state` guard method hai jo invalid state transitions ko rokta hai aur agar order allowed state mein na ho to user-friendly `UserError` throw karta hai.**
* **🔬 Implementation (`freight_shipping.py`):**
  ```python
  def _ensure_state(self, allowed, action):
      labels = dict(self._fields['state'].selection)
      for rec in self:
          if rec.state not in allowed:
              allowed_text = ' or '.join(labels[s] for s in allowed)
              raise UserError(f"Order {rec.name} cannot be {action} because it is {labels[rec.state]}. Only {allowed_text} orders can be {action}.")
  ```
  Is se direct jump (jaise `draft` se direct `done`) rok diya jata hai. Strict flow: `draft` ➔ `submitted` ➔ `confirmed` ➔ `invoiced` ➔ `done`.

---

### Q7: Container ka status auto-reserve aur auto-release kaise hota hai?

* **⚡ 1-Liner Answer:**
  > **Freight Order ke `action_confirm()` par container `state = 'reserved'` ho jata hai, aur `action_done()` par container wapas `state = 'available'` ho jata hai.**
* **🔬 Implementation:**
  ```python
  def action_confirm(self):
      self.write({'state': 'confirmed'})
      self.cargo_ids.mapped('container_id').write({'state': 'reserved'})

  def action_done(self):
      self.write({'state': 'done'})
      self.cargo_ids.mapped('container_id').write({'state': 'available'})
  ```
  `self.cargo_ids.mapped('container_id')` poore order ke saray containers ka batch recordset banata hai aur single query mein state change karta hai.

---

### Q8: Transport vs Port Compatibility: `@api.onchange` aur `@api.constrains` dono kyun zaroori hain?

* **⚡ 1-Liner Answer:**
  > **`@api.onchange` UI level par dynamic dropdown domain ke liye hai, jabke `@api.constrains` database level par data integrity enforce karta hai.**
* **🔬 In-Depth Explanation:**
  * `@api.onchange` sirf browser par chalta hai jab user click karta hai. Agar koi data API, CSV import, ya test script se aaye to onchange execute nahi hota!
  * `@api.constrains` ORM level par save hote waqt chalta hai. Agar port transport flag match na kare to chahe UI ho ya API, transaction reject ho jati hai.

---

### Q9: Cargo Pricing Engine mein Weight vs Volume billing kaise hoti hai?

* **⚡ 1-Liner Answer:**
  > **`billing_on` field check karti hai: agar 'weight' ho to `weight_price * weight`, aur agar 'volume' ho to `volume_price * volume` calculate hota hai.**
* **🔬 Implementation (`freight.order.cargo`):**
  ```python
  @api.depends('billing_on', 'pricing_id.weight_price', 'pricing_id.volume_price', 'weight', 'volume')
  def _compute_prices(self):
      for line in self:
          if line.billing_on == 'weight':
              line.unit_price = line.pricing_id.weight_price if line.pricing_id else 0.0
              line.total_price = line.unit_price * line.weight
          else:
              line.unit_price = line.pricing_id.volume_price if line.pricing_id else 0.0
              line.total_price = line.unit_price * line.volume
  ```
  `store=True` hone ki wajah se header par `cargo_total = sum(cargo_ids.mapped('total_price'))` fast SQL aggregation se calculate hota hai.

---

### Q10: Child Line models par `company_id` ko `related='order_id.company_id', store=True` kyun rakha gaya?

* **⚡ 1-Liner Answer:**
  > **Performance aur security ke liye: `store=True` hone se database table mein column banta hai jis par Multi-Company Record Rules direct fast query chala sakte hain.**
* **🔬 In-Depth Explanation:**
  Agar `store=False` hota, to record rule chalne par Odoo ko har single cargo/route line ke liye parent `order_id` join karna parta (N+1 query problem). `store=True` hone se PostgreSQL direct `WHERE company_id IN (...)` fast filter lagata hai.

---

### Q11: Multi-Company Record Rule ka domain samjhayein: `['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]`

* **⚡ 1-Liner Answer:**
  > **Yeh domain record ko tab allow karta hai agar uski company khali (global) ho YA uski company user ki currently selected companies (`company_ids`) mein shamil ho.**
* **🔬 Breakdown:**
  * `('company_id', '=', False)`: Global records jo sab ke liye share hain.
  * `('company_id', 'in', company_ids)`: Records jo user ki allowed companies ke hain.
  * `'|'`: Logical OR operator.

---

### Q12: Order delete karte waqt humne `unlink()` ko override kyun nahi kiya, balki `@api.ondelete(at_uninstall=False)` use kiya?

* **⚡ 1-Liner Answer:**
  > **`@api.ondelete` modern Odoo standard decorator hai jo module uninstall ke waqt run nahi hota, jis se module bina validation error ke cleanly uninstall ho sakta hai.**
* **🔬 In-Depth Explanation:**
  Agar aap purana `def unlink(self):` override karke validation error lagayein, to module uninstall hote waqt Odoo database clean karta hai aur aapka `unlink()` uninstallation ko crash kar deta hai. `@api.ondelete(at_uninstall=False)` normal delete ko validate karta hai lekin uninstallation ke waqt skip ho jata hai.

---

### Q13: Customs Clearance compliance kaise ensure karti hai ke ghalat order confirm na ho?

* **⚡ 1-Liner Answer:**
  > **`action_confirm()` mein 2-tier gatekeeper check hai: clearance record ka hona lazmi hai, aur koi bhi clearance 'draft' state mein nahi honi chahiye.**
* **🔬 Implementation:**
  ```python
  def action_confirm(self):
      self._ensure_state(['submitted'], 'confirmed')
      for rec in self:
          if not rec.clearance_ids:
              raise UserError("Cannot confirm order: No Customs Clearance found for this order.")
          if any(c.state == 'draft' for c in rec.clearance_ids):
              raise UserError("Cannot confirm order: Customs Clearance is still in Draft state.")
      self.write({'state': 'confirmed'})
      self.cargo_ids.mapped('container_id').write({'state': 'reserved'})
  ```

---

### Q14: `fields.Binary(attachment=True)` ka kya faida hai? Database vs Filestore?

* **⚡ 1-Liner Answer:**
  > **`attachment=True` file ko PostgreSQL database ke andar binary blob rakhne ke bajaye disk par Odoo Filestore mein save karta hai, jis se database ka size light rehta hai aur backup tez hota hai.**
* **🔬 In-Depth Explanation:**
  * `attachment=False`: Poori file base64 format mein database table ke column mein store hoti hai, jis se DB size gigabytes mein chala jata hai aur performance down hoti hai.
  * `attachment=True`: Odoo file ko physical disk (`~/.local/share/Odoo/filestore/<db>/`) par hash name se save karta hai, aur table mein sirf metadata link rehta hai.

---

### Q15: Sequence Number `create()` method mein `@api.model_create_multi` ke sath kaise handle hota hai?

* **⚡ 1-Liner Answer:**
  > **`@api.model_create_multi` batch creation ke liye `vals_list` leta hai; loop mein check karte hain agar `name == 'New'` ho to `ir.sequence` se next code assign karte hain.**
* **🔬 Implementation:**
  ```python
  @api.model_create_multi
  def create(self, vals_list):
      for vals in vals_list:
          if vals.get('name', 'New') == 'New':
              vals['name'] = self.env['ir.sequence'].next_by_code('freight.order') or 'New'
      return super().create(vals_list)
  ```

---

## 💰 Section 3: Task 7 - Invoicing Engine, Tracking & Data Integrity

---

### Q16: Odoo 19 mein Freight Lines ko Customer Invoice (`account.move`) mein kaise convert karte hain?

* **⚡ 1-Liner Answer:** 
  > **`action_create_invoice()` method mein `Command.create()` pattern ke sath Cargo, Route, aur Service lines ko map kar ke `account.move` (type `out_invoice`) create karte hain aur new invoice ko `invoice_ids` se link karte hain.**
* **🔬 In-Depth Explanation:**
  * Odoo 19 mein relational records create karne ke liye tuple `(0, 0, vals)` ke bajaye modern **`Command.create(vals)`** use hota hai.
  * Invoicing Engine 3 categories ko convert karta hai:
    1. **Cargo:** Weight vs Volume billing check karta hai; quantity aur rate set karta hai.
    2. **Routes:** Route name, ports, quantity 1.0 aur route sale price.
    3. **Services:** Service name, vendor name, quantity aur vendor/service price.
  * Taxes ko reset karne ke liye `tax_ids: [Command.clear()]` lagaya jata hai.
  * Invoice create hone ke baad:
    ```python
    rec.write({
        'state': 'invoiced',
        'invoice_ids': [Command.link(move.id)],
    })
    ```

---

### Q17: Dynamic Cargo Billing (Weight vs Volume) Invoicing mein kaise handle hoti hai?

* **⚡ 1-Liner Answer:** 
  > **Cargo line ki `billing_on` field evaluate ki jati hai: agar `weight` ho to quantity `cargo.weight` banti hai, agar `volume` ho to quantity `cargo.volume` banti hai.**
* **🔬 Implementation:**
  ```python
  for cargo in rec.cargo_ids:
      qty = cargo.weight if cargo.billing_on == 'weight' else cargo.volume
      price = cargo.unit_price
      invoice_lines.append(Command.create({
          'name': f"Cargo: {cargo.product_id.display_name} ({cargo.container_id.name})",
          'product_id': cargo.product_id.id,
          'quantity': qty or 1.0,
          'price_unit': price,
          'tax_ids': [Command.clear()],
      }))
  ```

---

### Q18: Line Locks (Data Integrity) Python-level par kaise lagaye jatay hain aur kyun zaroori hain?

* **⚡ 1-Liner Answer:** 
  > **Child models (`freight.order.cargo`, `freight.order.route`, `freight.order.service`) ke `create`, `write`, aur `unlink` methods ko override kar ke parent order ki state check ki jati hai aur locked states par `UserError` raise kiya jata hai.**
* **🔬 Rules:**
  * **Cargo Lines:** Jab order `confirmed`, `invoiced`, ya `done` ho to add, edit ya delete block hota hai (kyunki container reserve aur custom clearance ho chuki hoti hai).
  * **Route aur Service Lines:** Jab order `invoiced` ya `done` ho to add, edit ya delete block hota hai (kyunki invoice ban chuki hoti hai aur amounts mismatch nahi honi chahiye).
* **⚠️ Senior Trap:** Locks hamesha Child Model par lagte hain kyunki child ke paas `order_id` hota hai. Agar ghalti se Parent Model par `line.order_id` check kiya jaye to `AttributeError` aye ga.

---

### Q19: Mail Chatter Notifications aur `Markup` ka kya taluq hai?

* **⚡ 1-Liner Answer:** 
  > **Odoo 19 mein HTML formatting (jaise `<b>...</b>`) ko escape hone se bachane ke liye `Markup(msg)` wrap kiya jata hai, aur `message_post(body=Markup(msg), partner_ids=...)` se specific partners ko notify kiya jata hai.**
* **🔬 Implementation:**
  ```python
  partners = (rec.shipper_id | rec.consignee_id | rec.agent_id).ids
  msg = Markup(f"Freight Order <b>{rec.name}</b> has been <b>{action_name}</b>.")
  rec.message_post(body=msg, partner_ids=partners, subtype_xmlid='mail.mt_comment')
  ```

---

### Q20: Stat Button Navigation Pattern (`action_view_invoices`): Single vs Multiple records kaise handle hotay hain?

* **⚡ 1-Liner Answer:** 
  > **Agar `len(invoices) == 1` ho to action direct `form` view with `res_id` return karta hai, agar multiple hon to `list,form` view with domain `[('id', 'in', invoices.ids)]` return karta hai.**
* **🔬 Implementation:**
  ```python
  def action_view_invoices(self):
      self.ensure_one()
      invoices = self.invoice_ids
      action = {
          'name': 'Customer Invoices',
          'type': 'ir.actions.act_window',
          'res_model': 'account.move',
          'context': {'default_move_type': 'out_invoice'},
      }
      if len(invoices) == 1:
          action.update({'view_mode': 'form', 'res_id': invoices.id})
      else:
          action.update({'view_mode': 'list,form', 'domain': [('id', 'in', invoices.ids)]})
      return action
  ```

---

## 📄 Section 4: Task 8 - PDF Reports & QWeb Templating

### Q21: `t-field` vs `t-esc` / `t-out` mein kya farq hai?

* **⚡ 1-Liner Answer:** 
  > **`t-field` model field ki type ke mutabiq automatic formatting (currency widget, user timezone date/time, float precision) apply karta hai, jabke `t-out` / `t-esc` raw Python expressions ya calculated values print karne ke liye use hota hai.**
* **🔬 Detail & Best Practice:**
  * `t-field` sirf direct record fields par chalta hai (e.g. `doc.order_date`, `cargo.total_price`). Yeh monetary symbols aur date formats automatically locale ke mutabiq render karta hai.
  * Computed / compound expressions (e.g. `doc.cargo_total + doc.routes_total`) par `t-field` kaam nahi karta, is liye wahan `t-out` ke sath `t-options='{"widget": "monetary", ...}'` use kiya jata hai.
  * Odoo 19 mein `t-out` recommended hai kyunki yeh XSS injection se protect karta hai jab tak `Markup` explicitly na diya gaya ho.

---

### Q22: PDF Report ke header mein Company Logo aur Address kahan se aate hain?

* **⚡ 1-Liner Answer:** 
  > **`web.external_layout` layout template Odoo standard report engine se call hota hai, jo current document ke `company_id` (ya user company) se logo, address, vat number, aur footer fetch karta hai.**
* **🔬 Architecture:**
  * Jab hum report template ke andar `<t t-call="web.external_layout">` likhte hain, Odoo `doc.company_id` ko read karke `web.address_layout` aur header header/footer blocks inject karta hai.
  * Is wajah se har report par manual logo ya address likhne ki zaroorat nahi rehti aur multi-company reporting fully seamless rehti hai.

---

### Q23: PDF Report ko Form View ke "Print" menu ke sath kaise bind kiya jata hai?

* **⚡ 1-Liner Answer:** 
  > **`ir.actions.report` record mein `binding_model_id="model_freight_shipping"` aur `binding_type="report"` set karne se yeh report automatic form view ke Print dropdown mein show ho jata hai.**
* **🔬 Code Reference:**
  ```xml
  <record id="action_report_freight_shipping" model="ir.actions.report">
      <field name="name">Freight Order</field>
      <field name="model">freight.shipping</field>
      <field name="report_type">qweb-pdf</field>
      <field name="report_name">trn_freight.report_freight_shipping_document</field>
      <field name="report_file">trn_freight.report_freight_shipping_document</field>
      <field name="binding_model_id" ref="model_freight_shipping"/>
      <field name="binding_type">report</field>
  </record>
  ```

---

### Q24: Multi-page PDF reports mein table headers repeating aur clean pagination kaise ensure ki jati hai?

* **⚡ 1-Liner Answer:** 
  > **Tables ke `thead` element par inline style `display: table-header-group;` aur `tr` par `page-break-inside: avoid;` set karne se Wkhtmltopdf har new page par table headers automatically repeat karta hai.**
* **🔬 Implementation:**
  ```xml
  <table class="table table-sm table-bordered mt-2">
      <thead class="table-light" style="display: table-header-group;">
          <tr><th>Container</th><th>Goods</th>...</tr>
      </thead>
      <tbody>...</tbody>
  </table>
  ```

---

### Q25: Automated Tests mein PDF report generation ko bina browser UI ke kaise test kiya jata hai?

* **⚡ 1-Liner Answer:** 
  > **`self.env['ir.actions.report']._render_qweb_pdf('report_xml_id', res_ids=order.ids)` call karke return hone wale binary content ki validity check ki jati hai.**
* **🔬 Test Implementation (`test_freight_order.py`):**
  ```python
  def test_11_freight_pdf_reports(self):
      order = self._create_order()
      pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
          'trn_freight.action_report_freight_shipping', res_ids=order.ids
      )
      self.assertTrue(pdf_content)
      self.assertGreater(len(pdf_content), 0)
  ```

---

## 🚐 Section 5: Task 9 - Staff Transport Management & Odoo App Extensions

### Q26: `_inherit` without `_name` vs with a new `_name` mein kya farq hai?

* **⚡ 1-Liner Answer:** 
  > **Without `_name` existing database table ko in-place extend karta hai (naye columns aur methods add karta hai), jabke with new `_name` ek bilkul nayi database table banata hai jo parent model ki fields aur methods copy karti hai (Prototype Inheritance).**
* **🔬 Architecture & Best Practice:**
  * **In-Place Extension (`_inherit = 'fleet.vehicle'`):**
    * Koi nayi table nahi banti. Odoo `fleet_vehicle` table mein hi naye columns (`seat_capacity_override`, `effective_capacity`) add karta hai.
    * Use Case: Jab standard Odoo app (jaise Fleet ya Employees) mein naye features add karne hon.
  * **Prototype Inheritance (`_name = 'custom.vehicle'`, `_inherit = 'fleet.vehicle'`):**
    * Ek nayi table `custom_vehicle` banti hai. Parent table ka schema aur logic copy hota hai lekin data isolated rehta hai.
    * Use Case: Jab standard model ka template use karke ek nayi business entity banani ho.

---

### Q27: Standard view copy karne ke bajaye `xpath` kyun use karte hain?

* **⚡ 1-Liner Answer:** 
  > **`xpath` standard view ko bina modify kiye usme dynamically naye elements inject karta hai, jo Odoo updates/upgrades ke doraan merge conflicts se bachata hai aur modularity preserve karta hai.**
* **🔬 Detail:**
  * Agar hum standard view copy kar lein aur upstream Odoo koi naya button, security attribute, ya UI fix release kare, toh copied view outdated ho jayegi aur code maintain karna impossible ho jayega.
  * `xpath` locator (e.g. `<xpath expr="//notebook" position="inside">` ya `<xpath expr="//field[@name='seats']" position="after">`) sirf target node ko point karta hai aur clean diff provide karta hai.

---

### Q28: Field par `tracking=True` lagane se kya hota hai aur iske prerequisites kya hain?

* **⚡ 1-Liner Answer:** 
  > **Jab model `mail.thread` inherit karta hai, toh `tracking=True` wali field ki har value change (before ➔ after) user ke naam aur timestamp ke sath automatically record ke Chatter mein log ho jati hai.**
* **🔬 Implementation Checklist:**
  1. Python model mein `_inherit = ['mail.thread', 'mail.activity.mixin']` hona zaroori hai.
  2. Target field par `tracking=True` set ho (e.g. `transport_route_id = fields.Many2one(..., tracking=True)`).
  3. XML form view ke end par `<chatter/>` widget placed ho.
  4. Jab user field change karke Save karega, Odoo audit log note generate kar dega.

---

### Q29: Drag-and-Drop Sequence reordering Odoo List Views mein kaise implement ki jati hai?

* **⚡ 1-Liner Answer:** 
  > **Model mein `sequence = fields.Integer(default=10)` aur `_order = 'sequence, id'` define karke List view ke field par `widget="handle"` lagaya jata hai.**
* **🔬 Technical Mechanism:**
  * Model level par:
    ```python
    _order = 'sequence, id'
    sequence = fields.Integer(string='Sequence', default=10)
    ```
  * View level par:
    ```xml
    <list string="Transport Stops">
        <field name="sequence" widget="handle"/>
        <field name="name"/>
    </list>
    ```
  * User jab mouse se handle ko drag karke chorta hai, Odoo ka web client background mein `write()` RPC call karke saare affected records ke `sequence` integers update kar deta hai.

---

### Q30: Google Maps URL multiple waypoints ke sath Odoo action se kaise generate aur open kiya jata hai?

* **⚡ 1-Liner Answer:** 
  > **Stops ke partner addresses ko URL parameters (`origin`, `destination`, `waypoints`) mein format karke `ir.actions.act_url` dictionary return ki jati hai.**
* **🔬 Implementation (`transport_route.py`):**
  ```python
  def action_open_google_maps(self):
      self.ensure_one()
      params = {
          'api': '1',
          'origin': self.start_address_id.street or self.stop_ids[0].name,
          'destination': self.end_address_id.street or self.stop_ids[-1].name,
          'waypoints': '|'.join([s.address_id.street for s in self.stop_ids[1:-1]])
      }
      url = f"https://www.google.com/maps/dir/?{urllib.parse.urlencode(params)}"
      return {
          'type': 'ir.actions.act_url',
          'url': url,
          'target': 'new',
      }
  ```

---

### Q31: Odoo 19 RelaxNG Search View requirements mein legacy Odoo se kya farq hai?

* **⚡ 1-Liner Answer:** 
  > **Odoo 19 RelaxNG validator `<search>` view ke andar `<group>` element par legacy attributes `expand="0"` aur `string="Group By"` strictly disallow karta hai; sirf plain `<group>` tags use hote hain.**
* **🔬 Syntax Comparison:**
  * **❌ Legacy (Odoo 14-16):**
    ```xml
    <group expand="0" string="Group By">
        <filter string="Route" name="group_route" context="{'group_by': 'route_id'}"/>
    </group>
    ```
  * **✅ Modern Odoo 19 Standard:**
    ```xml
    <group>
        <filter string="Route" name="group_route" context="{'group_by': 'route_id'}"/>
    </group>
    ```

---

### Q32: Automated Testing mein `@api.constrains` vs `@api.onchange` ko kaise test kiya jata hai?

* **⚡ 1-Liner Answer:** 
  > **`@api.constrains` ko invalid database assignment karke `with self.assertRaises(ValidationError)` se test kiya jata hai, jabke `@api.onchange` ko memory record (`env[model].new(...)`) par direct method call karke assert kiya jata hai taake premature DB flush na ho.**
* **🔬 Test Implementation (`test_staff_transport.py`):**
  ```python
  # 1. Constrains Validation Test (Raises ValidationError on DB write):
  with self.assertRaises(ValidationError):
      self.employee.pickup_stop_id = stop_from_other_route.id

  # 2. Onchange Reset Test (In-memory virtual record):
  emp_temp = self.env['hr.employee'].new({
      'transport_route_id': route_a.id,
      'pickup_stop_id': stop_a.id,
  })
  emp_temp.transport_route_id = route_b.id
  emp_temp._onchange_transport_route_id()
  self.assertFalse(emp_temp.pickup_stop_id)
  ```
