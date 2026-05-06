import uuid

from werkzeug.urls import url_encode

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    kyc_risk_assessment_matrix = fields.Binary(string="Risk Assessment Matrix")
    kyc_risk_assessment_matrix_filename = fields.Char()
    kyc_risk_assessment_score = fields.Float(string="Risk Assessment Score")
    kyc_onboarding_date = fields.Date(string="Onboarding Date")
    kyc_risk_rating = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        string="Risk Rating",
    )

    kyc_sales_person_signed_on = fields.Date(string="Sales Person Signed On")
    kyc_reference_no = fields.Char(string="KYC Reference No.")

    kyc_contact_type = fields.Selection(
        [
            ("individual", "Individual"),
            ("company", "Company"),
        ],
        string="Contact Type",
    )
    kyc_customer_name = fields.Char(string="Name")

    kyc_gender = fields.Selection(
        [
            ("male", "Male"),
            ("female", "Female"),
        ],
        string="Gender",
    )
    kyc_eid_no = fields.Char(string="EID No.")
    kyc_fta_id = fields.Char(string="FTA ID")
    kyc_fta_password = fields.Char(string="FTA Password")
    kyc_passport_or_id_no = fields.Char(string="Passport no. / ID no.")
    kyc_nationality = fields.Char(string="Nationality")
    kyc_birthdate = fields.Date(string="Birthdate")
    kyc_id_document = fields.Binary(string="ID Document")
    kyc_id_document_filename = fields.Char()

    kyc_non_resident = fields.Boolean(string="Non-Resident")
    kyc_uae_resident = fields.Boolean(string="UAE Resident")
    kyc_permanent_address = fields.Char(string="Permanent Address")

    kyc_occupation = fields.Char(string="Occupation")
    kyc_company_name = fields.Char(string="Company Name")
    kyc_business_address = fields.Char(string="Business Address")
    kyc_nature_of_business = fields.Char(string="Nature of Business")

    kyc_annual_gross_income = fields.Float(string="Annual Gross Income")
    kyc_purpose_of_transaction = fields.Char(string="Purpose of Transaction")

    kyc_source_of_funds = fields.Char(string="Source of Funds")
    kyc_political_exposed = fields.Selection(
        [
            ("yes", "Yes"),
            ("no", "No"),
        ],
        string="Political Exposed Person or Individual",
    )

    kyc_customer_declaration_name = fields.Char(string="Customer Name")
    kyc_customer_signature = fields.Image(string="Customer Signature")
    kyc_customer_signature_filename = fields.Char()
    kyc_customer_representative_id = fields.Many2one(
        "res.users",
        string="Customer Representative Name",
        default=lambda self: self.env.user,
    )
    kyc_customer_representative_signature = fields.Image(
        string="Customer Representative's Signature"
    )
    kyc_customer_representative_signature_filename = fields.Char()
    kyc_access_token = fields.Char(string="KYC Access Token", copy=False)
    document_ids = fields.One2many("partner.document", "partner_id", string="Documents")

    def _kyc_ensure_access_token(self):
        """
        Ensure the partner has a KYC portal access token and return it.
        
        Ensures the method is called on a single record. If the partner has no access token, a new token is generated and stored on the record.
        
        Returns:
            kyc_access_token (str): The partner's KYC access token.
        """
        self.ensure_one()
        if not self.kyc_access_token:
            self.sudo().write({"kyc_access_token": str(uuid.uuid4())})
        return self.kyc_access_token

    def get_kyc_portal_url(self, suffix=None, query_string=None):
        """
        Builds the partner's KYC portal URL and embeds an access token for portal access.
        
        Parameters:
            suffix (str | None): Optional path suffix appended directly after the partner id in the URL (e.g., '/step'). If None, no suffix is added.
            query_string (str | None): Optional additional query string appended to the URL; should start with '&' if extending the existing query parameters.
        
        Returns:
            str: The constructed KYC portal URL (contains the `access_token` query parameter).
        """
        self.ensure_one()
        params = {"access_token": self._kyc_ensure_access_token()}
        url = f"/my/customer-kyc/{self.id}{suffix or ''}?{url_encode(params)}"
        if query_string:
            url += query_string
        return url

    def action_send_customer_kyc(self):
        """
        Send the Customer KYC email to each partner and return a client notification action.
        
        Ensures a KYC access token exists for each partner, sends the configured mail template to the partner's email, and returns an action that displays a success notification in the client.
        
        Returns:
            dict: An `ir.actions.client` action dictionary that triggers a non-sticky success notification titled "Customer KYC" with the message "Customer KYC email sent."
        
        Raises:
            UserError: If the mail template "contact_kyc_information.mail_template_customer_kyc" is not found.
            UserError: If any partner in `self` does not have an email address set.
        """
        template = self.env.ref(
            "contact_kyc_information.mail_template_customer_kyc",
            raise_if_not_found=False,
        )
        if not template:
            raise UserError(_("The Customer KYC email template is missing."))

        for partner in self:
            if not partner.email:
                raise UserError(
                    _("Please set an email address on %s before sending Customer KYC.")
                    % partner.display_name
                )
            partner._kyc_ensure_access_token()
            template.send_mail(partner.id, force_send=True)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Customer KYC"),
                "message": _("Customer KYC email sent."),
                "type": "success",
                "sticky": False,
            },
        }
