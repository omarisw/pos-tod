# -*- coding: utf-8 -*-

from odoo import models, fields, api
import base64
import time
import logging
_logger = logging.getLogger(__name__)


class website_self_invoice_web(models.Model):
    _name = 'website.self.invoice.web'
    _description = 'Portal de Autofacturacion Integrado a Odoo' 
    _rec_name = 'order_number' 
    _order = 'create_date desc' 

    datas_fname = fields.Char('File Name',size=256)
    file = fields.Binary('Layout')
    download_file = fields.Boolean('Descargar Archivo')
    cadena_decoding = fields.Text('Binario sin encoding')
    type = fields.Selection([('csv','CSV'),('xlsx','Excel')], 'Tipo Exportacion', 
                            required=False, )
    rfc_partner = fields.Char('RFC', size=15)
    order_number = fields.Char('Folio Pedido de Venta', size=128)
    monto_total = fields.Float('Monto total')
    mail_to = fields.Char('Correo Electronico', size=256)
    ticket_pos = fields.Boolean('Ticket', default=False)
    state = fields.Selection([('draft','Borrador'),('error','Error'),('done','Relizado')])

    attachment_ids = fields.One2many('website.self.invoice.web.attach','website_auto_id','Adjuntos del Portal')
    partner_id = fields.Many2one("res.partner","Partner")
    l10n_mx_edi_usage = fields.Selection([
        ('G01', 'Acquisition of merchandise'),
        ('G02', 'Returns, discounts or bonuses'),
        ('G03', 'General expenses'),
        ('I01', 'Constructions'),
        ('I02', 'Office furniture and equipment investment'),
        ('I03', 'Transportation equipment'),
        ('I04', 'Computer equipment and accessories'),
        ('I05', 'Dices, dies, molds, matrices and tooling'),
        ('I06', 'Telephone communications'),
        ('I07', 'Satellite communications'),
        ('I08', 'Other machinery and equipment'),
        ('D01', 'Medical, dental and hospital expenses.'),
        ('D02', 'Medical expenses for disability'),
        ('D03', 'Funeral expenses'),
        ('D04', 'Donations'),
        ('D05', 'Real interest effectively paid for mortgage loans (room house)'),
        ('D06', 'Voluntary contributions to SAR'),
        ('D07', 'Medical insurance premiums'),
        ('D08', 'Mandatory School Transportation Expenses'),
        ('D09', 'Deposits in savings accounts, premiums based on pension plans.'),
        ('D10', 'Payments for educational services (Colegiatura)'),
        ('P01', 'To define'),
    ], 'Usage', default='P01',
        help='Used in CFDI 3.3 to express the key to the usage that will '
        'gives the receiver to this invoice. This value is defined by the '
        'customer. \nNote: It is not cause for cancellation if the key set is '
        'not the usage that will give the receiver of the document.')
    error_message = fields.Text('Mensaje de Error')

    _defaults = {
        'download_file': False,
        'type': 'csv',
        'state': 'draft',
        }


    def website_form_input_filter(self, request, values):
        values['medium_id'] = (
                values.get('medium_id') or
                self.default_get(['medium_id']).get('medium_id') or
                self.sudo().env['ir.model.data'].xmlid_to_res_id('utm.utm_medium_website')
        )
        return values

    def write(self, values):
        result = super(website_self_invoice_web, self).write(values)
        return result

    @api.model
    def create(self, values):
        result = super(website_self_invoice_web, self).create(values)
        ### Validacion de Campos Obligatorios ###
        if not result.rfc_partner or not result.order_number or not result.monto_total: # or not result.mail_to:
            result.write({
                        'error_message':'Los campos Marcados con un ( * ) son Obligatorios.',
                        'state': 'error',
                    })
            return result
        if not result.partner_id:
            self.env.cr.execute("""
                select id from res_partner where UPPER(vat) like %s;
                """, ('%'+result.rfc_partner.upper()+'%',))
            cr_res = self.env.cr.fetchall()
            order_id = False
    
            try:
                partner_id = cr_res[0][0]
                if not partner_id:
                    result.write({
                            'error_message':'El RFC %s no existe en la Base de Datos.' % result.rfc_partner,
                            'state': 'error',
                        })
                    return result
            except:
                result.write({
                        'error_message':'El RFC %s no existe en la Base de Datos.' % result.rfc_partner,
                        'state': 'error',
                    })
                return result
        else:
            partner_id = result.partner_id.id
        ##### Retornamos  la Factura en caso que exista ####
        #if result.ticket_pos == False:
        #revisamos primero si está en SO
        self.env.cr.execute("""
                select id from sale_order where UPPER(name)=%s and round(amount_total,2)=%s;
                """, (result.order_number.upper(),result.monto_total or 0))
        cr_res = self.env.cr.fetchall()
        ticket_pos = False
        try:
            order_id = cr_res[0][0]
            if not order_id:
                if (result.order_number.find('Order ') != -1):
                    order_str = result.order_number.upper()
                else:
                    order_str = 'ORDER ' + result.order_number.upper()
                self.env.cr.execute("""
                    select id from pos_order where pos_reference like %s and round(amount_total,2)=%s;
                    """, ('%'+result.order_number,result.monto_total or 0))
                cr_res = self.env.cr.fetchall()
                try:
                    order_id = cr_res[0][0]
                    ticket_pos = True
                    if not order_id:
                        result.write({
                                'error_message':'El Ticket %s no existe en la Base de Datos.' % result.order_number,
                                'state': 'error',
                            })
                        return result
                except:
                    result.write({
                            'error_message':'El Ticket %s no existe en la Base de Datos.' % result.order_number,
                            'state': 'error',
                        })
                    return result
            else:
                ticket_pos = False
        except:
            if (result.order_number.find('Order ') != -1):
                order_str = result.order_number.upper()
            else:
                order_str = 'ORDER ' + result.order_number.upper()
            self.env.cr.execute("""
                select id from pos_order where pos_reference like %s and round(amount_total,2)=%s;
                """, ('%'+result.order_number,result.monto_total or 0))
            cr_res = self.env.cr.fetchall()
            try:
                order_id = cr_res[0][0]
                ticket_pos = True
                if not order_id:
                    result.write({
                            'error_message':'El Ticket %s no existe en la Base de Datos.' % result.order_number,
                            'state': 'error',
                        })
                    return result
            except:
                result.write({
                        'error_message':'El Ticket %s no existe en la Base de Datos.' % result.order_number,
                        'state': 'error',
                    })
                return result
        if order_id and ticket_pos == False:
            order_obj =  self.env['sale.order'].sudo()
            order_br = order_obj.browse(order_id)

            picking_obj  = self.env['stock.picking'].sudo()
            picking_br = picking_obj.search([('origin','=',order_br.name)])
            if order_br.state in ('draft','sent'):
                result.write({
                            'error_message':'El Pedido %s se encuentra en espera de ser procesado, por favor comuniquese con la compañia.' % order_br.name,
                            'state': 'error',
                        })
                return result
            if picking_br:
                picking_br = picking_br[0]
                #if picking_br.state=='waiting':
                for line in picking_br.move_ids_without_package:
                    line.quantity_done = line.product_uom_qty
                if picking_br.state in ['confirmed','assigned']:
                    picking_br.button_validate()
            
            if order_br.invoice_status != 'no':
                invoice_return = None
                if order_br.invoice_status == 'invoiced':
                    invoice_return = order_br.invoice_ids.filtered(lambda r: r.state != 'cancel')
                    if invoice_return and invoice_return[0].state != 'draft': # in['factura_correcta', 'factura_cancelada']:
                        result.write({
                                'error_message':'El Pedido %s ya fue Facturado.' % result.order_number,
                                'state': 'error',
                            })
                        return result
                else:
                    if not order_br.l10n_mx_edi_payment_method_id:
                        result.write({
                           'error_message':'El pedido %s no pudo facturarse ya que no cuenta con una forma de pago asignada, comuniquese con la compañia.' % order_br.name,
                           'state': 'error',
                        })
                        return result
#                     invoice_return = order_br.action_invoice_create()
                    invoice_return = order_br._create_invoices()
                invoice_br = self.env['account.move'].sudo().search([('id','=',invoice_return.id)])
                vals = {}
                if hasattr(invoice_br, 'factura_cfdi'):
                    vals.update({'factura_cfdi':True, })
                if result.l10n_mx_edi_usage:
                    vals.update({'l10n_mx_edi_usage': result.l10n_mx_edi_usage})
                if invoice_br.partner_id.id!= partner_id:
                    vals.update({'partner_id':partner_id})
                if invoice_br.company_id != order_br.company_id:
                    _logger.info('compañia')
                    vals.update({'company_id':order_br.company_id})

                if order_br.l10n_mx_edi_payment_method_id:
                    vals.update({'l10n_mx_edi_payment_method_id': order_br.l10n_mx_edi_payment_method_id.id})
		
                invoice_br.write(vals)
                if invoice_br.state == 'draft':
                    invoice_br.sudo().action_post()
                    invoice_br.sudo().action_process_edi_web_services()
                _logger.info('uuid %s partner %s nombre %s uso_cfdi %s', invoice_br.l10n_mx_edi_cfdi_uuid, invoice_br.partner_id.name, invoice_br.name, invoice_br.l10n_mx_edi_usage)

                result.write({'attachment_ids':[]})
                result.write({'state':'done'})
                invoice_br.force_invoice_send()
            else:
                result.write({
                            'error_message':'El Pedido %s ya fue Facturado.' % result.order_number,
                            'state': 'error',
                        })
                return result
        if order_id and ticket_pos == True:
            invoice_obj = self.env['account.move'].sudo()
            pos_order_obj = self.env['pos.order'].sudo()
            pos_br = pos_order_obj.browse(order_id)
            pos_br.write({'partner_id':partner_id})
            if pos_br.partner_id:
                if pos_br.partner_id.id != partner_id:
                    result.write({
                                'error_message':'El RFC %s no pertenece al Relacionado con el Pedido de Venta %s.' % (result.rfc_partner,result.order_number,),
                                'state': 'error',
                            }) 
                    return result
            if pos_br.state != 'cancel':
                if True:
                    invoice_id = None
                    if pos_br.state == 'invoiced':
                        invoice_return = invoice_obj.search([('origin', '=', pos_br.name), ('state', '!=', 'cancel')])
                        invoice_id = invoice_return.id
                        if invoice_return and invoice_return[0].l10n_mx_edi_cfdi_uuid in['factura_correcta', 'factura_cancelada']:
                            result.write({
                                    'error_message':'El Pedido %s ya fue Facturado.' % result.order_number,
                                    'state': 'error',
                                })
                            return result
                    else:
                        invoice_return = pos_br.action_pos_order_invoice() #action_invoice()
                        invoice_id = invoice_return['res_id']
                    invoice_br = invoice_obj.browse(invoice_id)
                    vals = {}
                    if hasattr(invoice_obj, 'factura_cfdi'):
                        vals.update({'factura_cfdi':True, })
                    if result.l10n_mx_edi_usage:
                        vals.update({'l10n_mx_edi_usage': result.l10n_mx_edi_usage})
                    if invoice_br.partner_id.id!= partner_id:
                        vals.update({'partner_id':partner_id})
                    if pos_br.payment_ids:
                        l10n_mx_edi_payment_method = pos_br.payment_ids[0].payment_method_id.cash_journal_id.l10n_mx_edi_payment_method_id
                        payment_method_code = l10n_mx_edi_payment_method.code
                        if payment_method_code not in ('01', '02', '03', '04', '05', '06', '08', '28', '29'):
                            result.write({
                                    'error_message':'Forma de pago desconocido %s: %s.' % (payment_method_code,
                                                                                         pos_br.payment_ids[0].payment_method_id.cash_journal_id.name),
                                    'state': 'error',
                                })
                            return result
                        vals.update({'l10n_mx_edi_payment_method_id': l10n_mx_edi_payment_method.id})
                    invoice_br.write(vals)
                    if True:
                        if invoice_br.state == 'draft':
                            invoice_br.sudo().action_post()
                            invoice_br.sudo().action_process_edi_web_services()

                        ir_attach = self.env['ir.attachment'].sudo()
                        attachment_ids = ir_attach.search([('res_model','=','account.move'),('res_id','=',invoice_br.id)])
                        if not attachment_ids:
                            Template = self.env['mail.template'].sudo()
                            Attachment = self.env['ir.attachment'].sudo()
#                             report = Template.env['report'].get_pdf([invoice_br.id], 'account.report_invoice')
                            report = self.env['ir.actions.report']._get_report_from_name('account.report_invoice').sudo()
                            report_data = report._render_qweb_pdf([invoice_br.id])[0]
                            report = base64.b64encode(report_data)
                            fname =  'CDFI_' + invoice_br.name.replace('/', '_') + '.pdf'
                            attachment_data = {
                                'name': fname,
                                'store_fname': fname,
                                'datas': report,
                                'res_model': 'account.move',
                                'res_id': invoice_br.id,
                            }
                            
                            #xml_file = open(invoice_br.xml_invoice_link, 'rb').read()
                            fname_xml = 'CDFI_' + invoice_br.name.replace('/', '_') + '.xml'
                            attachment_xml = {
                                'name': fname_xml,
                                'store_fname': fname_xml,
#                                 'datas': invoice_br.l10n_mx_edi_cfdi, #base64.b64encode(xml_file),
                                'res_model': 'account.move',
                                'res_id': invoice_br.id,
                            }
                            
                            attachment_ids = [Attachment.create(attachment_data), Attachment.create(attachment_xml)]
                    
                        if attachment_ids:
                            attachment_web =[]
                            for attach in attachment_ids:
                                xval = (0,0,{
                                    'attach_id': attach.id,
                                    })
                                attachment_web.append(xval)
                            result.write({'attachment_ids':attachment_web})
                            result.write({'state':'done'})
                            invoice_br.force_invoice_send()
                    else:
                        result.write({
                            'error_message':'La factura %s no pudo timbrarse con el PAC, comuniquese con la compañia.' % invoice_br.number,
                            'state': 'error',
                        })
                        return result
                else:
                    result.write({
                            'error_message':'El Ticket %s tiene problemas para ser procesado comuniquese con la compañia.' % result.order_number,
                            'state': 'error',
                        })
                    return result
            else:
                result.write({
                            'error_message':'El Ticket %s ya fue Facturado.' % result.order_number,
                            'state': 'error',
                        })
                return result
        #### Ligar Adjuntos de Facturacion al one2many por el campo attach_id ####
        return result
# URL ejemplo:
# http://localhost:10069/web?db=AUTOINVOICE_TEST


class website_self_invoice_web_attach(models.Model):
    _name = 'website.self.invoice.web.attach'
    _description = 'Adjuntos para Portal de Auto Facturacion'

    website_auto_id = fields.Many2one('website.self.invoice.web', 'ID Ref')
    attach_id = fields.Many2one('ir.attachment', 'Adjunto')
    store_fname = fields.Char('File Name',size=256, related="attach_id.store_fname")
    file = fields.Binary('Archivo Binario', related="attach_id.datas")
