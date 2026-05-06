# -*- coding: utf-8 -*-
from odoo import fields, models


class PartnerDocument(models.Model):
    _name = "partner.document"
    _description = "Partner Document"

    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    document_name = fields.Char(string="Document Name", required=True)
    file = fields.Binary(string="File", attachment=True)
    filename = fields.Char(string="Filename")
    document_type = fields.Char(string="Type")
    status = fields.Selection(
        [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        string="Status",
        default="pending",
    )
    verified = fields.Boolean(string="Verified", default=False)
