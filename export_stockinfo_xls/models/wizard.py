# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author:Cybrosys Techno Solutions(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from datetime import datetime
from datetime import date, datetime
from odoo import models, fields, api
import time
import pytz
import json
import datetime
import io
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import date_utils
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class StockReport(models.TransientModel):
    _name = "wizard.stock.history"
    _description = "Current Stock History"

    warehouse = fields.Many2many('stock.warehouse', 'wh_wiz_rel', 'wh', 'wiz', string='Warehouse', required=True)
    category = fields.Many2many('product.category', 'categ_wiz_rel', 'categ', 'wiz', string='Warehouse')

    def export_xls(self):
        # context = self._context
        # data = {'ids': context.get('active_ids', [])}
        # data['model'] = 'wizard.stock.history'
        # data['form'] = self.read()[0]
        # for field in data['form'].keys():
        #     if isinstance(data['form'][field], tuple):
        #         data['form'][field] = data['form'][field][0]
        # if context.get('xls_export'):

            # return self.env.ref('export_stockinfo_xls.stock_xlsx').report_action(self, data=datas)
        data = {
            'ids': self.ids,
            'model': self._name,
            'warehouse': self.warehouse.id,
            'category': self.category.id,
            # 'date_start': self.date_start,
            # 'date_end': self.date_end,
            # 'state': self.state,
            # 'product_id': self.product_id.id,
            # 'usage': self.usage,
        }
        return {
            'type': 'ir_actions_xlsx_download',
            'data': {'model': 'wizard.stock.history',
                     'options': json.dumps(data, default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Current Stock History',
                     }
        }

    def get_warehouse(self, data):
        wh = data.warehouse.mapped('id')
        obj = self.env['stock.warehouse'].search([('id', 'in', wh)])
        l1 = []
        l2 = []
        for j in obj:
            l1.append(j.name)
            l2.append(j.id)
        return l1, l2

    def get_lines(self, data, warehouse):
        lines = []
        categ_id = data.mapped('id')
        if categ_id:
            stock_history = self.env['product.product'].search([('categ_id', 'in', categ_id)])
        else:
            stock_history = self.env['product.product'].search([])
        for obj in stock_history:
            sale_value = 0
            purchase_value = 0
            product = self.env['product.product'].browse(obj.id)
            sale_obj = self.env['sale.order.line'].search([('order_id.state', 'in', ('sale', 'done')),
                                                           ('product_id', '=', product.id),
                                                           ('order_id.warehouse_id', '=', warehouse)])
            for i in sale_obj:
                sale_value = sale_value + i.product_uom_qty
            purchase_obj = self.env['purchase.order.line'].search([('order_id.state', 'in', ('purchase', 'done')),
                                                                   ('product_id', '=', product.id),
                                                                   ('order_id.picking_type_id', '=', warehouse)])
            for i in purchase_obj:
                purchase_value = purchase_value + i.product_qty
            available_qty = product.with_context({'warehouse': warehouse}).virtual_available + \
                            product.with_context({'warehouse': warehouse}).outgoing_qty - \
                            product.with_context({'warehouse': warehouse}).incoming_qty
            value = available_qty * product.standard_price
            vals = {
                'sku': product.default_code,
                'name': product.name,
                'category': product.categ_id.name,
                'cost_price': product.standard_price,
                'available': available_qty,
                'virtual': product.with_context({'warehouse': warehouse}).virtual_available,
                'incoming': product.with_context({'warehouse': warehouse}).incoming_qty,
                'outgoing': product.with_context({'warehouse': warehouse}).outgoing_qty,
                'net_on_hand': product.with_context({'warehouse': warehouse}).qty_available,
                'total_value': value,
                'sale_value': sale_value,
                'purchase_value': purchase_value,
            }
            lines.append(vals)
            print(lines)
        return lines

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        lines = self.browse(data['ids'])
        print("lines",lines)
        d = lines.category
        get_warehouse = self.get_warehouse(lines)
        print("get_warehouse",get_warehouse)
        count = len(get_warehouse[0]) * 11 + 6
        print("count",count)
        comp = self.env.user.company_id.name
        print("comp",comp)
        sheet = workbook.add_worksheet('Stock Info')
        format0 = workbook.add_format({'font_size': 20, 'align': 'center', 'bold': True})
        format1 = workbook.add_format({'font_size': 14, 'align': 'vcenter', 'bold': True})
        format11 = workbook.add_format({'font_size': 12, 'align': 'center', 'bold': True})
        format21 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
        format3 = workbook.add_format({'bottom': True, 'top': True, 'font_size': 12})
        format4 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True})
        font_size_8 = workbook.add_format({'font_size': 8, 'align': 'center'})
        font_size_8_l = workbook.add_format({'font_size': 8, 'align': 'left'})
        font_size_8_r = workbook.add_format({'font_size': 8, 'align': 'right'})
        red_mark = workbook.add_format({'font_size': 8, 'bg_color': 'red'})
        justify = workbook.add_format({'font_size': 12})
        format3.set_align('center')
        justify.set_align('justify')
        format1.set_align('center')
        red_mark.set_align('center')
        sheet.merge_range(1, 7, 2, 10, 'Product Stock Info', format0)
        sheet.merge_range(3, 7, 3, 10, comp, format11)
        w_house = ', '
        cat = ', '
        c = []
        d1 = d.mapped('id')
        if d1:
            for i in d1:
                c.append(self.env['product.category'].browse(i).name)
            cat = cat.join(c)
            sheet.merge_range(4, 0, 4, 1, 'Category(s) : ', format4)
            sheet.merge_range(4, 2, 4, 3 + len(d1), cat, format4)
        sheet.merge_range(5, 0, 5, 1, 'Warehouse(s) : ', format4)
        w_house = w_house.join(get_warehouse[0])
        sheet.merge_range(5, 2, 5, 3+len(get_warehouse[0]), w_house, format4)
        user = self.env['res.users'].browse(self.env.uid)
        tz = pytz.timezone(user.tz)
        time = pytz.utc.localize(datetime.datetime.now()).astimezone(tz)
        # print("tz", time)
        sheet.merge_range('A8:G8', 'Report Date: ' + str(time.strftime("%Y-%m-%d %H:%M %p")), format1)
        sheet.merge_range(7, 7, 7, count, 'Warehouses', format1)
        sheet.merge_range('A9:G9', 'Product Information', format11)
        w_col_no = 6
        w_col_no1 = 7
        for i in get_warehouse[0]:
            w_col_no = w_col_no + 11
            sheet.merge_range(8, w_col_no1, 8, w_col_no, i, format11)
            w_col_no1 = w_col_no1 + 11
        sheet.write(9, 0, 'SKU', format21)
        sheet.merge_range(9, 1, 9, 3, 'Name', format21)
        sheet.merge_range(9, 4, 9, 5, 'Category', format21)
        sheet.write(9, 6, 'Cost Price', format21)
        p_col_no1 = 7
        for i in get_warehouse[0]:
            sheet.write(9, p_col_no1, 'Available', format21)
            sheet.write(9, p_col_no1 + 1, 'Virtual', format21)
            sheet.write(9, p_col_no1 + 2, 'Incoming', format21)
            sheet.write(9, p_col_no1 + 3, 'Outgoing', format21)
            sheet.merge_range(9, p_col_no1 + 4, 9, p_col_no1 + 5, 'Net On Hand', format21)
            sheet.merge_range(9, p_col_no1 + 6, 9, p_col_no1 + 7, 'Total Sold', format21)
            sheet.merge_range(9, p_col_no1 + 8, 9, p_col_no1 + 9, 'Total Purchased', format21)
            sheet.write(9, p_col_no1 + 10, 'Valuation', format21)
            p_col_no1 = p_col_no1 + 11
        prod_row = 10
        prod_col = 0
        for i in get_warehouse[1]:
            get_line = self.get_lines(d, i)
            for each in get_line:
                sheet.write(prod_row, prod_col, each['sku'], font_size_8)
                sheet.merge_range(prod_row, prod_col + 1, prod_row, prod_col + 3, each['name'], font_size_8_l)
                sheet.merge_range(prod_row, prod_col + 4, prod_row, prod_col + 5, each['category'], font_size_8_l)
                sheet.write(prod_row, prod_col + 6, each['cost_price'], font_size_8_r)
                prod_row = prod_row + 1
            break
        prod_row = 10
        prod_col = 7
        for i in get_warehouse[1]:
            get_line = self.get_lines(d, i)
            for each in get_line:
                if each['available'] < 0:
                    sheet.write(prod_row, prod_col, each['available'], red_mark)
                else:
                    sheet.write(prod_row, prod_col, each['available'], font_size_8)
                if each['virtual'] < 0:
                    sheet.write(prod_row, prod_col + 1, each['virtual'], red_mark)
                else:
                    sheet.write(prod_row, prod_col + 1, each['virtual'], font_size_8)
                if each['incoming'] < 0:
                    sheet.write(prod_row, prod_col + 2, each['incoming'], red_mark)
                else:
                    sheet.write(prod_row, prod_col + 2, each['incoming'], font_size_8)
                if each['outgoing'] < 0:
                    sheet.write(prod_row, prod_col + 3, each['outgoing'], red_mark)
                else:
                    sheet.write(prod_row, prod_col + 3, each['outgoing'], font_size_8)
                if each['net_on_hand'] < 0:
                    sheet.merge_range(prod_row, prod_col + 4, prod_row, prod_col + 5, each['net_on_hand'], red_mark)
                else:
                    sheet.merge_range(prod_row, prod_col + 4, prod_row, prod_col + 5, each['net_on_hand'], font_size_8)
                if each['sale_value'] < 0:
                    sheet.merge_range(prod_row, prod_col + 6, prod_row, prod_col + 7, each['sale_value'], red_mark)
                else:
                    sheet.merge_range(prod_row, prod_col + 6, prod_row, prod_col + 7, each['sale_value'], font_size_8)
                if each['purchase_value'] < 0:
                    sheet.merge_range(prod_row, prod_col + 8, prod_row, prod_col + 9, each['purchase_value'], red_mark)
                else:
                    sheet.merge_range(prod_row, prod_col + 8, prod_row, prod_col + 9, each['purchase_value'], font_size_8)
                if each['total_value'] < 0:
                    sheet.write(prod_row, prod_col + 10, each['total_value'], red_mark)
                else:
                    sheet.write(prod_row, prod_col + 10, each['total_value'], font_size_8_r)
                prod_row = prod_row + 1
            prod_row = 10
            prod_col = prod_col + 11
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
