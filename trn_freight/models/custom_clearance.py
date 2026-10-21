from odoo import api, fields, models
from odoo.exceptions import UserError


# =====================================================================
# 1. Main Model: Custom Clearance
# =====================================================================
class CustomClearance(models.Model):
    _name = 'custom.clearance'
    _description = 'Custom Clearance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Name', compute='_compute_name', store=True, readonly=True)
    freight_id = fields.Many2one(
        'freight.shipping', string='Freight Order', required=True,
        ondelete='cascade', tracking=True)
    date = fields.Date(
        string='Date', default=fields.Date.context_today)
    agent_id = fields.Many2one(
        'res.partner', string='Agent')
    loading_port_id = fields.Many2one(
        'freight.port', string='Loading Port')
    discharge_port_id = fields.Many2one(
        'freight.port', string='Discharging Port')
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done')],
        string='State', default='draft', required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    # Child Lines
    line_ids = fields.One2many(
        'custom.clearance.line', 'clearance_id', string='Documents')
    revision_ids = fields.One2many(
        'clearance.revision', 'clearance_id', string='Revisions')
    revision_count = fields.Integer(
        string='Revision Count', compute='_compute_revision_count')

    @api.depends('freight_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = f"CC - {rec.freight_id.name}" if rec.freight_id else "CC - "

    @api.depends('revision_ids')
    def _compute_revision_count(self):
        for rec in self:
            rec.revision_count = len(rec.revision_ids)

    @api.onchange('freight_id')
    def _onchange_freight_id(self):
        if self.freight_id:
            self.date = self.freight_id.order_date
            self.agent_id = self.freight_id.agent_id
            self.loading_port_id = self.freight_id.loading_port
            self.discharge_port_id = self.freight_id.discharge_port_id

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError("Only draft clearances can be confirmed.")
            rec.state = 'confirmed'

    def action_done(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError("Only confirmed clearances can be marked as done.")
            rec.state = 'done'

    def action_open_revision_wizard(self):
        self.ensure_one()
        return {
            'name': 'Create Revision',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.clearance.revision',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_clearance_id': self.id},
        }

    def action_view_revisions(self):
        self.ensure_one()
        return {
            'name': 'Revisions',
            'type': 'ir.actions.act_window',
            'res_model': 'clearance.revision',
            'view_mode': 'list,form',
            'domain': [('clearance_id', '=', self.id)],
            'context': {'default_clearance_id': self.id},
        }


# =====================================================================
# 2. Document Line Model: custom.clearance.line
# =====================================================================
class CustomClearanceLine(models.Model):
    _name = 'custom.clearance.line'
    _description = 'Custom Clearance Document Line'

    clearance_id = fields.Many2one(
        'custom.clearance', string='Clearance', required=True, ondelete='cascade')
    company_id = fields.Many2one(
        'res.company', related='clearance_id.company_id', store=True, readonly=True)
    name = fields.Char(string='Document Name', required=True)
    document = fields.Binary(string='File', attachment=True, required=True)
    file_name = fields.Char(string='File Name')


# =====================================================================
# 3. Revision History Model: clearance.revision
# =====================================================================
class ClearanceRevision(models.Model):
    _name = 'clearance.revision'
    _description = 'Clearance Revision'

    name = fields.Char(string='Name', required=True, default='Revision')
    reason = fields.Text(string='Reason', required=True)
    note = fields.Text(string='Note')
    clearance_id = fields.Many2one(
        'custom.clearance', string='Clearance', required=True, ondelete='cascade')
    company_id = fields.Many2one(
        'res.company', related='clearance_id.company_id', store=True, readonly=True)


# =====================================================================
# 4. Wizard (TransientModel): custom.clearance.revision
# =====================================================================
class CustomClearanceRevisionWizard(models.TransientModel):
    _name = 'custom.clearance.revision'
    _description = 'Custom Clearance Revision Wizard'

    clearance_id = fields.Many2one(
        'custom.clearance', string='Clearance', required=True)
    reason = fields.Text(string='Reason', required=True)
    note = fields.Text(string='Note')

    def action_create_revision(self):
        self.ensure_one()
        rev_number = len(self.clearance_id.revision_ids) + 1
        self.env['clearance.revision'].create({
            'name': f"REV-{rev_number:02d} ({self.clearance_id.name})",
            'reason': self.reason,
            'note': self.note,
            'clearance_id': self.clearance_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}