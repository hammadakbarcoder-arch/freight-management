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
