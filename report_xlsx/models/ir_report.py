# Copyright 2015 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import logging
import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class ReportAction(models.Model):
    _inherit = 'ir.actions.report'

    report_type = fields.Selection(selection_add=[("xlsx", "xlsx")])

    @api.model
    def render_xlsx(self, docids, data):
        report_model_name = 'report.%s' % self.report_name
        report_model = self.env.get(report_model_name)
        if report_model is None:
            raise UserError(_('%s model was not found' % report_model_name))
        ret = report_model.with_context(
            active_model=self.model,
        ).create_xlsx_report(docids, data)
        if ret and isinstance(ret, (tuple, list)):  # data, "xlsx"
            self.save_xlsx_report_attachment(docids, ret[0])
        return ret

    @api.model
    def _get_report_from_name(self, report_name):
        res = super(ReportAction, self)._get_report_from_name(report_name)
        if res:
            return res
        report_obj = self.env['ir.actions.report']
        qwebtypes = ['xlsx']
        conditions = [('report_type', 'in', qwebtypes),
                      ('report_name', '=', report_name)]
        context = self.env['res.users'].context_get()
        return report_obj.with_context(context).search(conditions, limit=1)

    def save_xlsx_report_attachment(self, docids, report_contents):
        """Save as attachment when the report is set up as such."""

        attachment_setting = self.attachment
        if not attachment_setting:
            return

        if len(docids) > 1:
            _logger.warning(
                "Cannot save XLSX report on multiple records at once."
            )
        record = self.env[self.model].browse(docids)

        # Similar to ir.actions.report::postprocess_pdf_report in the base
        # module (ir/ir_actions_report.py).
        attachment_name = safe_eval(
            attachment_setting, {"object": record, "time": time}
        )
        if not attachment_name:
            return
        attachment_vals = {
            "name": attachment_name,
            "datas": base64.encodestring(report_contents),
            "datas_fname": attachment_name,
            "res_model": self.model,
            "res_id": record.id,
        }
        try:
            attachment = self.env["ir.attachment"].create(attachment_vals)
        except AccessError:
            _logger.info(
                "Cannot save XLSX report %r as attachment",
                attachment_vals["name"],
            )
        else:
            _logger.info(
                "The XLSX document %s is now saved in the database",
                attachment_vals["name"],
            )

        return attachment, record
