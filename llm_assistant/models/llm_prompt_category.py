from odoo import _, api, fields, models


class LLMPromptCategory(models.Model):
    _name = "llm.prompt.category"
    _description = "LLM Prompt Category"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = "complete_name"
    _order = "complete_name"

    name = fields.Char(
        string="Category Name",
        required=True,
        index=True,
    )
    complete_name = fields.Char(
        string="Complete Name",
        compute="_compute_complete_name",
        store=True,
        recursive=True,
    )
    parent_id = fields.Many2one(
        "llm.prompt.category",
        string="Parent Category",
        index=True,
        ondelete="cascade",
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "llm.prompt.category",
        "parent_id",
        string="Child Categories",
    )
    prompt_count = fields.Integer(
        string="Prompt Count",
        compute="_compute_prompt_count",
    )
    active = fields.Boolean(default=True)
    code = fields.Char(
        string="Category Code",
        help="Technical code to identify this category",
    )
    description = fields.Text(
        string="Description",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = (
                    f"{category.parent_id.complete_name} / {category.name}"
                )
            else:
                category.complete_name = category.name

    @api.depends("child_ids")
    def _compute_prompt_count(self):
        prompt_data = self.env["llm.prompt"].read_group(
            [("category_id", "child_of", self.ids)],
            ["category_id"],
            ["category_id"],
        )
        prompt_count_dict = {
            data["category_id"][0]: data["category_id_count"] for data in prompt_data
        }

        for category in self:
            category.prompt_count = prompt_count_dict.get(category.id, 0)

    @api.constrains("parent_id")
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise models.ValidationError(
                _("Error! You cannot create recursive categories.")
            )
