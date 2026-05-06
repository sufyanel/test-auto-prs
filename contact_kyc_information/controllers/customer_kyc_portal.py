import binascii

from odoo import _, http
from odoo.http import request
from odoo.tools import consteq


class CustomerKycPortal(http.Controller):
    def _get_partner_sudo(self, partner_id, access_token):
        """
        Return the partner record in sudo mode when the provided KYC access token is valid for that partner; otherwise return an empty sudo `res.partner` recordset.
        
        Parameters:
            partner_id (int): ID of the partner to retrieve.
            access_token (str): KYC access token to validate for the partner.
        
        Returns:
            recordset: The partner `res.partner` recordset in sudo when the token is valid, or an empty sudo `res.partner` recordset when validation fails.
        """
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
        """
        Render the customer's KYC portal page for a validated partner or redirect to the user's profile when access is invalid.
        
        Parameters:
            partner_id (int): ID of the partner whose KYC page is requested.
            access_token (str|None): Optional token used to validate access to the KYC page.
            message (str|None): Optional message to display on the page.
        
        Returns:
            werkzeug.wrappers.Response: An HTTP response that renders the customer KYC portal page for the partner, or a redirect response to the customer's profile when access is invalid.
        """
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
        """
        Handle a customer's KYC acceptance from the portal, record their declaration and signature, attach the signed KYC PDF to the partner, and return a client redirect.
        
        Parameters:
            partner_id (int): ID of the partner accepting KYC.
            access_token (str|None): Optional access token used to validate the partner link.
            name (str|None): Full name provided as the declaration signer.
            signature (bytes|str|None): Signature data to be stored; expected in the same format the partner field accepts.
        
        Returns:
            dict: On validation failure returns {"error": "<message>"} with one of:
                - "Invalid customer KYC link."
                - "Full Name is required."
                - "Signature is missing."
                - "Invalid signature data."
            On success returns {"force_refresh": True, "redirect_url": "<partner KYC portal URL>?message=sign_ok"}.
        """
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
