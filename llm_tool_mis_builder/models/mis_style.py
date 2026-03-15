"""MIS Style Tools - Report styling management"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class MisReportStyle(models.Model):
    """Inherit MIS Report Style to add LLM tools"""

    _inherit = "mis.report.style"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def mis_style_list(self, limit: int = 50) -> dict:
        """List all available MIS report styles

        Returns the list of styles that can be applied to reports,
        KPIs, or individual cells.

        Args:
            limit: Maximum number of styles to return (default: 50)

        Returns:
            Dictionary with list of styles and their properties
        """
        styles = self.search([], limit=limit, order="name")

        result = []
        for style in styles:
            style_data = {
                "id": style.id,
                "name": style.name,
            }

            # Colors
            if style.color:
                style_data["color"] = style.color
            if style.background_color:
                style_data["background_color"] = style.background_color

            # Typography
            if style.font_style:
                style_data["font_style"] = style.font_style
            if style.font_weight:
                style_data["font_weight"] = style.font_weight
            if style.font_size:
                style_data["font_size"] = style.font_size

            # Formatting
            if style.indent_level:
                style_data["indent_level"] = style.indent_level
            if style.prefix:
                style_data["prefix"] = style.prefix
            if style.suffix:
                style_data["suffix"] = style.suffix
            if style.dp is not None:
                style_data["decimal_places"] = style.dp
            if style.divider and style.divider != 1:
                style_data["divider"] = style.divider

            # Display options
            style_data["hide_empty"] = style.hide_empty
            style_data["hide_always"] = style.hide_always

            result.append(style_data)

        return {
            "styles": result,
            "total_count": len(result),
        }

    @llm_tool(destructive_hint=True)
    def mis_style_create(
        self,
        name: str,
        color: Optional[str] = None,
        background_color: Optional[str] = None,
        font_style: Optional[str] = None,
        font_weight: Optional[str] = None,
        font_size: Optional[str] = None,
        indent_level: int = 0,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None,
        decimal_places: Optional[int] = None,
        divider: float = 1.0,
        hide_empty: bool = False,
        hide_always: bool = False,
    ) -> dict:
        """Create a new MIS report style

        Creates a reusable style that can be applied to reports,
        KPIs, or cells for consistent formatting.

        Args:
            name: Name for the style
            color: Text color in hex format (e.g., '#FF0000')
            background_color: Background color in hex format
            font_style: 'normal' or 'italic'
            font_weight: 'normal' or 'bold'
            font_size: 'medium', 'small', or 'large'
            indent_level: Indentation level for hierarchical display
            prefix: Text to show before values (e.g., '$')
            suffix: Text to show after values (e.g., '%')
            decimal_places: Number of decimal places for numeric values
            divider: Divide values by this number (e.g., 1000 for thousands)
            hide_empty: Hide row if all values are zero/empty
            hide_always: Always hide the row (for subtotals used in calculations)

        Returns:
            Dictionary with created style details
        """
        values = {"name": name}

        if color:
            values["color"] = color
        if background_color:
            values["background_color"] = background_color

        if font_style:
            if font_style not in ["normal", "italic"]:
                raise UserError(_("font_style must be 'normal' or 'italic'"))
            values["font_style"] = font_style

        if font_weight:
            if font_weight not in ["normal", "bold"]:
                raise UserError(_("font_weight must be 'normal' or 'bold'"))
            values["font_weight"] = font_weight

        if font_size:
            if font_size not in ["medium", "small", "large"]:
                raise UserError(_("font_size must be 'medium', 'small', or 'large'"))
            values["font_size"] = font_size

        values["indent_level"] = indent_level

        if prefix:
            values["prefix"] = prefix
        if suffix:
            values["suffix"] = suffix
        if decimal_places is not None:
            values["dp"] = decimal_places
        if divider != 1.0:
            values["divider"] = divider

        values["hide_empty"] = hide_empty
        values["hide_always"] = hide_always

        style = self.create(values)

        return {
            "id": style.id,
            "name": style.name,
            "message": f"Style '{name}' created successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_style_update(
        self,
        style_id: int,
        name: Optional[str] = None,
        color: Optional[str] = None,
        background_color: Optional[str] = None,
        font_style: Optional[str] = None,
        font_weight: Optional[str] = None,
        font_size: Optional[str] = None,
        indent_level: Optional[int] = None,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None,
        decimal_places: Optional[int] = None,
        divider: Optional[float] = None,
        hide_empty: Optional[bool] = None,
        hide_always: Optional[bool] = None,
    ) -> dict:
        """Update an existing MIS report style

        Updates the specified properties of a style. All reports and
        KPIs using this style will be affected.

        Args:
            style_id: ID of the style to update
            name: New name (optional)
            color: New text color (optional, empty string to remove)
            background_color: New background color (optional)
            font_style: New font style (optional)
            font_weight: New font weight (optional)
            font_size: New font size (optional)
            indent_level: New indent level (optional)
            prefix: New prefix (optional)
            suffix: New suffix (optional)
            decimal_places: New decimal places (optional)
            divider: New divider (optional)
            hide_empty: New hide_empty setting (optional)
            hide_always: New hide_always setting (optional)

        Returns:
            Dictionary with updated style details
        """
        style = self.browse(style_id)
        if not style.exists():
            raise UserError(_("Style with ID %s not found") % style_id)

        values = {}

        if name is not None:
            values["name"] = name
        if color is not None:
            values["color"] = color if color else False
        if background_color is not None:
            values["background_color"] = background_color if background_color else False

        if font_style is not None:
            if font_style and font_style not in ["normal", "italic"]:
                raise UserError(_("font_style must be 'normal' or 'italic'"))
            values["font_style"] = font_style if font_style else False

        if font_weight is not None:
            if font_weight and font_weight not in ["normal", "bold"]:
                raise UserError(_("font_weight must be 'normal' or 'bold'"))
            values["font_weight"] = font_weight if font_weight else False

        if font_size is not None:
            if font_size and font_size not in ["medium", "small", "large"]:
                raise UserError(_("font_size must be 'medium', 'small', or 'large'"))
            values["font_size"] = font_size if font_size else False

        if indent_level is not None:
            values["indent_level"] = indent_level
        if prefix is not None:
            values["prefix"] = prefix if prefix else False
        if suffix is not None:
            values["suffix"] = suffix if suffix else False
        if decimal_places is not None:
            values["dp"] = decimal_places
        if divider is not None:
            values["divider"] = divider
        if hide_empty is not None:
            values["hide_empty"] = hide_empty
        if hide_always is not None:
            values["hide_always"] = hide_always

        if values:
            style.write(values)

        return {
            "id": style.id,
            "name": style.name,
            "message": "Style updated successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_style_delete(self, style_id: int) -> dict:
        """Delete a MIS report style

        Permanently deletes a style. Reports and KPIs using this style
        will lose their styling.

        Args:
            style_id: ID of the style to delete

        Returns:
            Dictionary confirming deletion
        """
        style = self.browse(style_id)
        if not style.exists():
            raise UserError(_("Style with ID %s not found") % style_id)

        name = style.name
        style.unlink()

        return {
            "message": f"Style '{name}' deleted successfully",
            "deleted_id": style_id,
        }
