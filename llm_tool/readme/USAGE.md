Decorate a model method to expose it as a tool. Type hints are required on
every parameter and on the return value; the input schema is generated from
them.

```python
from odoo.addons.llm_tool.decorators import llm_tool


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @llm_tool(read_only_hint=True)
    def generate_sales_report(
        self, start_date: str, end_date: str, limit: int = 10
    ) -> dict:
        """Generate a sales summary report for a date range."""
        ...
        return {"total_revenue": 0.0}
```

The docstring becomes the tool description sent to the model, so write it for
the model rather than for a developer.

If a method cannot carry type hints, pass a schema instead:

```python
@llm_tool(schema={
    "type": "object",
    "properties": {"partner_id": {"type": "integer"}},
    "required": ["partner_id"],
})
def create_invoice(self, partner_id):
    """Create an invoice for a partner."""
```

Decorated methods are picked up when the server restarts. **Sync Tools** on the
tool list view re-runs the sync without a restart, once the registry has been
populated by a restart.

To make tools available to a conversation, add them to the thread's or
assistant's tool list. Only tools on that list can be called.
