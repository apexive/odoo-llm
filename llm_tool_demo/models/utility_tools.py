"""Utility Tools - Generic helper tools that don't belong to a specific model

These tools are implemented as a TransientModel since they don't persist data
and are just utility functions for LLMs to use.
"""

import logging
from datetime import datetime, timedelta

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class LLMUtilityTools(models.TransientModel):
    """Utility tools for LLMs - mathematical, date, and other helper functions"""

    _name = "llm.utility.tools"
    _description = "LLM Utility Tools"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def calculate_business_days(
        self, start_date: str, end_date: str, exclude_weekends: bool = True
    ) -> dict:
        """Calculate the number of business days between two dates

        This is a utility tool for date calculations. Business days typically
        exclude weekends (Saturday and Sunday).

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            exclude_weekends: Whether to exclude Saturday and Sunday (default: True)

        Returns:
            Dictionary with calculation results including total days and business days

        Example:
            calculate_business_days('2024-01-01', '2024-01-31', True)
            # Returns: {
            #     "total_days": 31,
            #     "business_days": 23,
            #     "weekend_days": 8
            # }
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError as e:
            raise UserError(_("Invalid date format. Use YYYY-MM-DD format.")) from e

        if start > end:
            raise UserError(_("Start date must be before or equal to end date"))

        total_days = (end - start).days + 1
        business_days = 0

        current = start
        while current <= end:
            # If exclude_weekends, skip Saturday (5) and Sunday (6)
            if not exclude_weekends or current.weekday() < 5:
                business_days += 1
            current += timedelta(days=1)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_days": total_days,
            "business_days": business_days,
            "weekend_days": total_days - business_days if exclude_weekends else 0,
            "exclude_weekends": exclude_weekends,
        }
