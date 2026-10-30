# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class LogisticsTransportVehicleRequest(models.Model):
    _name = 'logistics.transport.vehicle.request'
    _description = 'Vehicle Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'from_datetime desc, id desc'

    name = fields.Char(
        string='Request Number', required=True, copy=False, readonly=True,
        default='New', tracking=True
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Requester', required=True, tracking=True,
        default=lambda self: self.env.user.employee_id
    )
    from_datetime = fields.Datetime(
        string='From', required=True, tracking=True
    )
    to_datetime = fields.Datetime(
        string='To', required=True, tracking=True
    )
    purpose = fields.Text(
        string='Purpose', required=True, tracking=True
    )
    vehicle_id = fields.Many2one(
        'fleet.vehicle', string='Vehicle', tracking=True
    )
    approver_id = fields.Many2one(
        'res.users', string='Approver', readonly=True, tracking=True
    )
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, store=True
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('assigned', 'Assigned'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled')
        ],
        string='Status', default='draft', required=True, tracking=True
    )

    @api.constrains('from_datetime', 'to_datetime')
    def _check_dates(self):
        for rec in self:
            if rec.to_datetime and rec.from_datetime and rec.to_datetime <= rec.from_datetime:
                raise ValidationError(_("'To' datetime must be after 'From' datetime!"))

    @api.constrains('vehicle_id', 'from_datetime', 'to_datetime', 'state')
    def _check_vehicle_overlap(self):
        for rec in self:
            # Sirf tab check karein jab vehicle assign ho aur request Approved ya Assigned ho
            if rec.vehicle_id and rec.from_datetime and rec.to_datetime and rec.state in ('approved', 'assigned'):
                overlapping = self.search([
                    ('id', '!=', rec.id),
                    ('vehicle_id', '=', rec.vehicle_id.id),
                    ('state', 'in', ('approved', 'assigned')),
                    ('from_datetime', '<', rec.to_datetime),
                    ('to_datetime', '>', rec.from_datetime),
                ], limit=1)
                if overlapping:
                    raise ValidationError(_(
                        "Vehicle %(vehicle)s is already booked for request %(req)s from %(start)s to %(end)s!",
                        vehicle=rec.vehicle_id.name,
                        req=overlapping.name,
                        start=overlapping.from_datetime,
                        end=overlapping.to_datetime
                    ))

    def unlink(self):
        for rec in self:
            if rec.state in ('approved', 'assigned', 'done'):
                raise UserError(_("You cannot delete a vehicle request in '%s' status.") % rec.state)
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('logistics.transport.vehicle.request') or 'New'
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only draft requests can be submitted."))
            rec.state = 'submitted'

    def action_approve(self):
        is_manager = self.env.user.has_group('trn_staff_transport.group_staff_transport_manager')
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_("Only submitted requests can be approved."))
            if not is_manager:
                raise UserError(_("Only a Staff Transport Manager can approve vehicle requests."))
            # Apni request khud approve karne par pabandi
            if rec.sudo().employee_id.user_id == self.env.user:
                raise UserError(_("You cannot approve your own vehicle request!"))
            rec.write({
                'state': 'approved',
                'approver_id': self.env.user.id,
            })

    def action_reject(self):
        is_manager = self.env.user.has_group('trn_staff_transport.group_staff_transport_manager')
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_("Only submitted requests can be rejected."))
            if not is_manager:
                raise UserError(_("Only a Staff Transport Manager can reject vehicle requests."))
            if rec.sudo().employee_id.user_id == self.env.user:
                raise UserError(_("You cannot reject your own vehicle request!"))
            rec.write({
                'state': 'rejected',
                'approver_id': self.env.user.id,
            })

    def action_assign(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_("Only approved requests can be assigned."))
            if not rec.vehicle_id:
                raise UserError(_("Please assign a vehicle before marking as Assigned."))
            rec.state = 'assigned'

    def action_done(self):
        for rec in self:
            if rec.state != 'assigned':
                raise UserError(_("Only assigned requests can be completed."))
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_("Completed requests cannot be cancelled."))
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            rec.write({
                'state': 'draft',
                'approver_id': False,
            })
