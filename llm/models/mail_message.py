from odoo import api, fields, models, tools


class MailMessage(models.Model):
    """Extension of mail.message to handle LLM-specific message subtypes."""

    _inherit = "mail.message"

    LLM_XMLIDS = (
        "llm.mt_tool",
        "llm.mt_user",
        "llm.mt_assistant",
        "llm.mt_system",
    )

    llm_role = fields.Char(
        string="LLM Role",
        compute="_compute_llm_role",
        store=True,
        index=True,  # Add index for better query performance
        help="The LLM role for this message (user, assistant, tool, system)",
    )

    body_json = fields.Json(
        string="JSON Body",
        help="JSON data for tool messages and other structured content",
    )

    @api.depends("subtype_id")
    def _compute_llm_role(self):
        """Compute the LLM role for messages based on their subtype."""
        id_to_role, _ = self.get_llm_roles()

        for message in self:
            if message.subtype_id and message.subtype_id.id in id_to_role:
                message.llm_role = id_to_role[message.subtype_id.id]
            else:
                message.llm_role = False

    @tools.ormcache()
    def get_llm_roles(self):
        """Get cached mapping of LLM subtype IDs to clean role names and vice versa.

        Returns:
            tuple: (id_to_role_dict, role_to_id_dict) where:
                - id_to_role_dict: {subtype_id: 'user', subtype_id: 'assistant', ...}
                - role_to_id_dict: {'user': subtype_id, 'assistant': subtype_id, ...}
        """
        id_to_role = {}
        role_to_id = {}

        for xmlid in self.LLM_XMLIDS:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id(
                xmlid, raise_if_not_found=False
            )
            if subtype_id:
                # Extract clean role name (e.g., 'user' from 'llm.mt_user')
                role = xmlid.split(".")[-1][3:]  # Remove 'mt_' prefix
                id_to_role[subtype_id] = role
                role_to_id[role] = subtype_id

        return id_to_role, role_to_id

    def get_llm_role(self):
        """Get the LLM role for this message (ensure_one).

        DEPRECATED: Use the llm_role computed field instead.

        Returns:
            str or False: The role name ('user', 'assistant', 'tool', 'system') or False if not an LLM message
        """
        self.ensure_one()
        return self.llm_role

    def is_llm_message(self):
        """Check if messages are LLM messages using the stored field."""
        return {message: bool(message.llm_role) for message in self}

    def is_llm_user_message(self):
        """Check if messages are LLM user messages using the stored field."""
        return {message: message.llm_role == "user" for message in self}

    def is_llm_assistant_message(self):
        """Check if messages are LLM assistant messages using the stored field."""
        return {message: message.llm_role == "assistant" for message in self}

    def is_llm_tool_message(self):
        """Check if messages are LLM tool messages using the stored field."""
        return {message: message.llm_role == "tool" for message in self}

    def is_llm_system_message(self):
        """Check if messages are LLM system messages using the stored field."""
        return {message: message.llm_role == "system" for message in self}

    def _check_llm_role(self, role):
        """Check if messages match a specific LLM role using the stored field.

        Args:
            role (str): The role name ('user', 'assistant', 'tool', 'system')
        """
        return {message: message.llm_role == role for message in self}

    def to_store_format(self):
        """Convert message to store format compatible with Odoo 17.0. Used by frontend js components"""
        self.ensure_one()
        from odoo.addons.mail.tools.discuss import Store

        store = Store()
        self._to_store(store)
        result = store.get_result()

        return result["mail.message"][0]
