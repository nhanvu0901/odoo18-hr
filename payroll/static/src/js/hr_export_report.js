/** @odoo-module */
// payroll/static/src/js/hr_export_report.js

import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class OdooOWLListController extends ListController {
   setup() {
       super.setup();
       try {
           this.notification = useService("notification");
       } catch (e) {
           console.warn("Notification service not available:", e);
       }

       try {
           this.dialog = useService("dialog");
       } catch (e) {
           console.warn("Dialog service not available:", e);
       }
   }

   async _checkPayslipData() {
       const domain = [['state', '=', 'done']];
       const payslips = await this.model.orm.searchCount('hr.payslip', domain);
       return payslips > 0;
   }

   _showNoDataMessage(message) {
       if (this.notification && this.notification.add) {
           this.notification.add(message, {
               type: 'warning',
               title: _t("No Data Available"),
           });
       } else if (this.dialog && this.dialog.add) {
           import("@web/core/confirmation_dialog/confirmation_dialog").then(({ ConfirmationDialog }) => {
               this.dialog.add(ConfirmationDialog, {
                   title: _t("No Data Available"),
                   body: message,
                   confirm: () => {},
                   confirmLabel: _t("OK"),
                   cancel: false,
               });
           });
       } else if (this.env && this.env.services && this.env.services.notification) {
           this.env.services.notification.add(message, {
               type: 'warning',
               title: _t("No Data Available"),
           });
       } else {
           alert(message);
       }
   }

   async showKKReport() {
       const hasData = await this._checkPayslipData();

       if (!hasData) {
           this._showNoDataMessage(
               _t("No completed payslips found. Please ensure you have processed payslips before exporting KK-TNCN report.")
           );
           return;
       }

       this.actionService.doAction({
          type: 'ir.actions.act_window',
          res_model: 'hr.kk.tncn.export',
          name: 'Export KK-TNCN',
          view_mode: 'form',
          views: [[false, 'form']],
          target: 'new',
          res_id: false,
      });
   }

   async showQTTReport() {
       const hasData = await this._checkPayslipData();

       if (!hasData) {
           this._showNoDataMessage(
               _t("No completed payslips found. Please ensure you have processed payslips before exporting QTT-TNCN report.")
           );
           return;
       }

       this.actionService.doAction({
          type: 'ir.actions.act_window',
          res_model: 'hr.qtt.tncn.export',
          name: 'Export QTT-TNCN',
          view_mode: 'form',
          views: [[false, 'form']],
          target: 'new',
          res_id: false,
      });
   }
}

const viewRegistry = registry.category("views");
export const OWLListController = {
    ...listView,
    Controller: OdooOWLListController,
};
viewRegistry.add("hr_export_report", OWLListController);