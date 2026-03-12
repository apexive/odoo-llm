import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class LLMKnowledgeCollectionSkills(models.Model):
    _inherit = "llm.knowledge.collection"
