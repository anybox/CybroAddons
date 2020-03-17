# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil import parser
from odoo import http
from odoo.http import request


class WebsiteCoupon(http.Controller):

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, **post):
        """This function is overwritten because we need to pass the value 'coupon_not_available'
        to the template, inorder to show the error message to the user that, 'this coupon is not available'. """

        order = request.website.sale_get_order()
        if order:
            from_currency = order.company_id.currency_id
            to_currency = order.pricelist_id.currency_id
            compute_currency = lambda price: from_currency.compute(price, to_currency)
        else:
            compute_currency = lambda price: price

        values = {
            'website_sale_order': order,
            'compute_currency': compute_currency,
            'suggested_products': [],
        }
        if order:
            _order = order
            if not request.env.context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            values['suggested_products'] = _order._cart_accessories()

        if post.get('type') == 'popover':
            return request.render("website_sale.cart_popover", values)

        if post.get('code_not_available'):
            values['code_not_available'] = post.get('code_not_available')
        elif post.get('coupon_not_available'):
            values['coupon_not_available'] = post.get('coupon_not_available')
        return request.render("website_sale.cart", values)

    @http.route(['/shop/gift_coupon'], type='http', auth="public", website=True)
    def gift_coupon(self, promo_voucher, **post):
        """This function will be executed when we click the apply button of the voucher code in the website.
        It will verify the validity and availability of that coupon. If it can be applied, the coupon  will be applied
        and coupon balance will also be updated"""
        curr_user = request.env.user
        coupon = request.env['gift.coupon'].sudo().search([('code', '=', promo_voucher)], limit=1)
        coupon_product = request.env.ref('website_coupon.discount_product').sudo()
        flag = True
        if coupon and coupon.total_avail > 0:
            applied_coupons = request.env['partner.coupon'].sudo().search([('coupon', '=', promo_voucher),
                                                                           ('partner_id', '=', curr_user.partner_id.id)], limit=1)

        # checking voucher date and limit for each user for this coupon---------------------
            if coupon.partner_id:
                if curr_user.partner_id.id != coupon.partner_id.id:
                    flag = False
            today = datetime.now().date()
            if flag and applied_coupons.number < coupon.limit and today <= parser.parse(coupon.voucher.expiry_date).date():
                # checking coupon validity ---------------------------
                #    checking date of coupon ------------
                if coupon.start_date and coupon.end_date:
                    if today < parser.parse(coupon.start_date).date() or today > parser.parse(coupon.end_date).date():
                        flag = False
                elif coupon.start_date:
                    if today < parser.parse(coupon.start_date).date():
                        flag = False
                elif coupon.end_date:
                    if today > parser.parse(coupon.end_date).date():
                        flag = False
            else:
                flag = False
        else:
            flag = False
        if flag:
            order = request.website.sale_get_order(force_create=1)
            coupon_val, coupon_line, redirect = order.compute_coupon_value(coupon=coupon)
            if redirect:
                return request.redirect(redirect)
            if coupon_val:
                if flag and order.order_line:
                    coupon_product.product_tmpl_id.write({'list_price': coupon_val})
                    order._cart_update(product_id=coupon_product.id, set_qty=1, add_qty=1, voucher_id=coupon.voucher.id)
                    # updating coupon balance
                    total = coupon.total_avail - 1
                    coupon.write({'total_avail': total})
                    # creating a record for this partner, i.e he is used this coupon once-----------
                    if not applied_coupons:
                        curr_user.partner_id.write(
                            {'applied_coupon': [
                                (0, 0, {
                                    'partner_id': curr_user.partner_id.id,
                                    'coupon': coupon.code,
                                    'number': 1
                                })
                            ]}
                        )
                    else:
                        applied_coupons.write({'number': applied_coupons.number + 1})
                else:
                    return request.redirect("/shop/cart?coupon_not_available=1")
            else:
                return request.redirect("/shop/cart?coupon_not_available=2")
        else:
            return request.redirect("/shop/cart?coupon_not_available=1")

        return request.redirect("/shop/cart")
