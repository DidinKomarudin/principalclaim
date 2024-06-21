odoo.define('bsp_claim_magic_button.test', function (require) {
"use strict";

var form_widget = require('web.form_widgets');
var core = require('web.core');
var _t = core._t;
var QWeb = core.qweb;

form_widget.WidgetButton.include({
    on_click: function() {
         if(this.node.attrs.custom === "click"){

            console.log('Ngeyel...');

            return;
         }
         this._super();
    },
});
});