import binascii

from odoo import _, http
from odoo.http import request
from odoo.tools import consteq


class CustomerKycPortal(http.Controller):
    def _get_partner_sudo(self, partner_id, access_token):
        partner_sudo = request.env["res.partner"].sudo().browse(partner_id).exists()
        if (
            not partner_sudo
            or not access_token
            or not partner_sudo.kyc_access_token
            or not consteq(partner_sudo.kyc_access_token, access_token)
        ):
            return request.env["res.partner"].sudo()
        return partner_sudo

    @http.route(
        ["/my/customer-kyc/<int:partner_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def customer_kyc_page(self, partner_id, access_token=None, message=None, **kwargs):
        partner_sudo = self._get_partner_sudo(partner_id, access_token)
        if not partner_sudo:
            return request.redirect("/my")

        values = {
            "partner": partner_sudo,
            "access_token": access_token,
            "message": message,
        }
        return request.render("contact_kyc_information.customer_kyc_portal_page", values)

    @http.route(
        ["/my/customer-kyc/<int:partner_id>/accept"],
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def customer_kyc_accept(self, partner_id, access_token=None, name=None, signature=None):
        access_token = access_token or request.httprequest.args.get("access_token")
        partner_sudo = self._get_partner_sudo(partner_id, access_token)
        if not partner_sudo:
            return {"error": _("Invalid customer KYC link.")}
        if not name:
            return {"error": _("Full Name is required.")}
        if not signature:
            return {"error": _("Signature is missing.")}

        try:
            partner_sudo.write(
                {
                    "kyc_customer_declaration_name": name,
                    "kyc_customer_signature": signature,
                }
            )
            request.env.cr.flush()
        except (TypeError, binascii.Error):
            return {"error": _("Invalid signature data.")}

        pdf = request.env["ir.actions.report"].sudo()._render_qweb_pdf(
            "contact_kyc_information.action_report_customer_kyc",
            [partner_sudo.id],
        )[0]
        partner_sudo.message_post(
            attachments=[("Customer KYC - %s.pdf" % partner_sudo.display_name, pdf)],
            author_id=partner_sudo.id,
            body=_("Customer KYC accepted and signed by Administrator"),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

        return {
            "force_refresh": True,
            "redirect_url": partner_sudo.get_kyc_portal_url(query_string="&message=sign_ok"),
        }
