//odoo.define('bsp_claim.hide_button_edit_by_state', function (require) {
//    var FormView = require('web.FormView');
//    FormView.include({
//     init: function() {
//      this._super.apply(this, arguments);
//      if (this.model === 'bsp.claim.cl') {
//          this.display_alert(_t("testing hide_button_edit_by_state js."));
//          if (this.datarecord && (this.datarecord.state === 'done')) {
//            this.$buttons.find('.o_form_button_edit').css({'display':'none'});
//          }
//          else {
//            this.$buttons.find('.o_form_button_edit').css({'display':''});
//          }
//
//       }
//    });
//});
//
////odoo.define('bsp_claim.hide_button_edit_by_state', function (require) {
////    var FormView = require('web.FormView');
////    FormView.include({
////     init: function() {
////      this._super.apply(this, arguments);
////      if (this.controllerParams.modelName === 'bsp.claim.cl') {
//////                this.rendererParams.activeActions.edit = false;
////       }
////    });
////});
//odoo.define('hide_action_buttons.hide_action_buttons', function (require) {
//    "use strict";
//    let FormView = require('web.FormView');
//    FormView.include({
//        load_record: function (record) {
//            if (record && this.$buttons && this.get('actual_mode') === 'view') {
//                if (record.hide_action_buttons) {
//                    this.$buttons.find('.o_form_buttons_view').hide();
//                } else {
//                    this.$buttons.find('.o_form_buttons_view').show();
//                }
//            }
//            return this._super(record);
//        }
//    });
//});

//odoo.define('bsp_claim.web_onchange_action', function (require) {
//    "use strict";
//    var FormView = require('web.FormView');
//
//    FormView.include({
//     on_processed_onchange: function(result) {
//            var self = this,
//                action = null;
//
//            if(result.warning && result.warning.action)
//            {
//                action = result.warning.action;
//                delete result.warning;
//            }
//            alert('testing')
//            debugger;
//            return this._super.apply(this, arguments).then(function(){
//                if(action)
//                {
//                    self.do_action(action);
//                }
//            });
//        },
//    });
//});
