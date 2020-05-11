from odoo import models, fields, api, _


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, attributes=None, voucher_id=None, **kwargs):
        self.ensure_one()
        SaleOrderLineSudo = self.env['sale.order.line'].sudo()

        try:
            if add_qty:
                add_qty = float(add_qty)
        except ValueError:
            add_qty = 1
        try:
            if set_qty:
                set_qty = float(set_qty)
        except ValueError:
            set_qty = 0
        quantity = 0
        order_line = False
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(_('It is forbidden to modify a sale order which is not in draft status'))
        if line_id is not False:
            order_lines = self._cart_find_product_line(product_id, line_id, **kwargs)
            order_line = order_lines and order_lines[0]

        # Create line if no line with product_id can be located
        if not order_line:
            values = self._website_product_id_change(self.id, product_id, qty=1)
            values['name'] = self._get_line_description(self.id, product_id, attributes=attributes)
            order_line = SaleOrderLineSudo.create(values)

            try:
                order_line._compute_tax_id()
            except ValidationError as e:
                # The validation may occur in backend (eg: taxcloud) but should fail silently in frontend
                _logger.debug("ValidationError occurs during tax compute. %s" % (e))
            if add_qty:
                add_qty -= 1

        # compute new quantity
        if set_qty:
            quantity = set_qty
        elif add_qty is not None:
            quantity = order_line.product_uom_qty + (add_qty or 0)

        if voucher_id is not None:
            values['voucher_id'] = voucher_id

        # Remove zero of negative lines
        if quantity <= 0:
            order_line.unlink()
        else:
            # update line
            values = self._website_product_id_change(self.id, product_id, qty=quantity)
            if self.pricelist_id.discount_policy == 'with_discount' and not self.env.context.get('fixed_price'):
                order = self.sudo().browse(self.id)
                product_context = dict(self.env.context)
                product_context.setdefault('lang', order.partner_id.lang)
                product_context.update({
                    'partner': order.partner_id.id,
                    'quantity': quantity,
                    'date': order.date_order,
                    'pricelist': order.pricelist_id.id,
                })
                product = self.env['product.product'].with_context(product_context).browse(product_id)
                values['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                    order_line._get_display_price(product),
                    order_line.product_id.taxes_id,
                    order_line.tax_id,
                   self.company_id
                )

            order_line.write(values)

        return {'line_id': order_line.id, 'quantity': quantity}

    def compute_coupon_value(self, coupon=None):
        coupon_line, coupon_value, redirect = False, 0.00, False
        coupon_product = self.env.ref('website_coupon.discount_product').sudo()
        for line in self.order_line:
            if line.product_id == coupon_product:
                coupon_line = line
                break
        if not coupon_line and not coupon:
            return False, False, False
        if coupon is None:
            voucher_type = coupon_line.voucher_id.voucher_type
            coupon = self.env['gift.coupon'].search([('voucher', '=', coupon_line.voucher_id.id)])
            coupon_type, coupon_val = coupon.type, coupon.voucher_val
        else:
            coupon_type = coupon.type
            coupon_val = coupon.voucher_val
            voucher_type = coupon.voucher.voucher_type
        if coupon_type == 'fixed':
            if coupon_val >= self.amount_total:
                redirect = "/shop/cart?coupon_not_available=3"
        if coupon_type == 'percentage':
            if voucher_type == 'product':
                for line in self.order_line:
                    if line.product_id.name == categ_id.name:
                        coupon_value = (coupon_val / 100) * line.price_subtotal
                        break
            elif voucher_type == 'category':
                for line in self.order_line:
                    if line.product_id.categ_id.name == product_id.name:
                        coupon_value += (coupon_val / 100) * line.price_subtotal
            elif voucher_type == 'all':
                for line in self.order_line:
                    if line == coupon_line:
                        continue
                    coupon_value += (coupon_val/100) * line.price_subtotal
            coupon_val = coupon_value
        return -coupon_val, coupon_line, redirect


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    coupon_id = fields.Many2one('gift.coupon', default=False)
    voucher_id = fields.Many2one('gift.voucher', default=False)
