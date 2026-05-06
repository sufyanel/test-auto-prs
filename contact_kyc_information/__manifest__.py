{
    "name": "Contact KYC Information",
    "version": "19.0.1.0.0",
    "category": "Contacts",
    "summary": "Adds a KYC Information page to contacts.",
    "depends": ["contacts", "portal"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template_data.xml",
        "views/partner_document_views.xml",
        "views/res_partner_views.xml",
        "views/customer_kyc_portal_templates.xml",
        "report/customer_kyc_report.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
