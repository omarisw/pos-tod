from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vat = fields.Char(copy=False)

    @api.constrains('vat', 'company_id')
    def _check_vat_unique(self):
        for record in self:
            if record.parent_id or not record.vat:
                continue
            if self.env['res.partner'].sudo().search_count(
                    [
                        ('parent_id', '=', False),
                        ('vat', '=', record.vat),
                        ('id', '!=', record.id),
                        "|",
                        ('company_id', '=', False),
                        ('company_id', '=', record.company_id.id),
                    ]):
                raise ValidationError("El RFC {} existe en otro contacto \n"
                                      "NOTA: Considere archivar este contacto o descartarlo".format(record.vat)
                                      )
