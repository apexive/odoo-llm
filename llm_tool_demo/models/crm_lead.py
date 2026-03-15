"""CRM Lead Tools - LLM tools for lead/opportunity management"""

import logging

from odoo import models

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    """Inherit CRM Lead to add LLM tools"""

    _inherit = "crm.lead"

    @llm_tool(destructive_hint=True)
    def create_lead_from_description(
        self, description: str, contact_name: str = "", email: str = "", phone: str = ""
    ) -> dict:
        """Create a CRM lead from a natural language description

        Parses the description and creates a lead/opportunity in the CRM.
        This is useful when an LLM extracts lead information from conversations.

        Args:
            description: Description of the opportunity or customer need
            contact_name: Name of the contact person (optional)
            email: Email address (optional)
            phone: Phone number (optional)

        Returns:
            Dictionary with created lead information
        """
        # Create the lead
        lead_vals = {
            "name": description[:100],  # Use first 100 chars as name
            "description": description,
            "type": "opportunity",
        }

        # Add contact information if provided
        if contact_name:
            lead_vals["contact_name"] = contact_name
        if email:
            lead_vals["email_from"] = email
        if phone:
            lead_vals["phone"] = phone

        # Create the lead
        lead = self.create(lead_vals)

        return {
            "lead_id": lead.id,
            "lead_name": lead.name,
            "contact_name": lead.contact_name or "",
            "email": lead.email_from or "",
            "phone": lead.phone or "",
            "stage": lead.stage_id.name if lead.stage_id else "",
            "probability": lead.probability,
        }
