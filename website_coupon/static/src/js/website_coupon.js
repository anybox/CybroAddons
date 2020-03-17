odoo.define('website_coupon.service', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var base = require('web_editor.base');
    var website = require('website.website');
    var Model = require('web.Model');
    var _t = core._t;

    $('body').on('click', '#add_coupon', function () {
        $(this).closest('form').submit();
    });

});
