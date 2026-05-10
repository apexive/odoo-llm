"""Tests for LLM Tool MIS Builder module"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestMisTools(TransactionCase):
    """Test MIS Builder LLM tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a test report
        cls.report = cls.env["mis.report"].create({
            "name": "Test Report",
            "description": "Test report for LLM tools",
        })

        # Create test KPIs
        cls.kpi_revenue = cls.env["mis.report.kpi"].create({
            "report_id": cls.report.id,
            "name": "revenue",
            "description": "Total Revenue",
            "expression": "bal[70]",
            "type": "num",
            "sequence": 10,
        })

        cls.kpi_expenses = cls.env["mis.report.kpi"].create({
            "report_id": cls.report.id,
            "name": "expenses",
            "description": "Total Expenses",
            "expression": "bal[60]",
            "type": "num",
            "sequence": 20,
        })

        # Create test instance
        cls.instance = cls.env["mis.report.instance"].create({
            "name": "Test Instance",
            "report_id": cls.report.id,
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "company_id": cls.env.company.id,
        })

    def test_report_list(self):
        """Test mis_report_list tool"""
        result = self.env["mis.report"].mis_report_list()
        self.assertIn("reports", result)
        self.assertIn("total_count", result)
        self.assertGreater(result["total_count"], 0)

        # Test with search filter
        result = self.env["mis.report"].mis_report_list(search="Test Report")
        self.assertEqual(len(result["reports"]), 1)
        self.assertEqual(result["reports"][0]["name"], "Test Report")

    def test_report_get(self):
        """Test mis_report_get tool"""
        result = self.env["mis.report"].mis_report_get(report_id=self.report.id)
        self.assertEqual(result["id"], self.report.id)
        self.assertEqual(result["name"], "Test Report")
        self.assertEqual(len(result["kpis"]), 2)

        # Test by name
        result = self.env["mis.report"].mis_report_get(report_name="Test Report")
        self.assertEqual(result["id"], self.report.id)

    def test_report_get_not_found(self):
        """Test mis_report_get with invalid ID"""
        with self.assertRaises(UserError):
            self.env["mis.report"].mis_report_get(report_id=99999)

    def test_report_create(self):
        """Test mis_report_create tool"""
        result = self.env["mis.report"].mis_report_create(
            name="New Test Report",
            description="Created by test",
        )
        self.assertIn("id", result)
        self.assertEqual(result["name"], "New Test Report")

        # Verify in database
        report = self.env["mis.report"].browse(result["id"])
        self.assertTrue(report.exists())
        self.assertEqual(report.description, "Created by test")

    def test_report_duplicate(self):
        """Test mis_report_duplicate tool"""
        result = self.env["mis.report"].mis_report_duplicate(
            report_id=self.report.id,
            new_name="Duplicated Report",
        )
        self.assertIn("id", result)
        self.assertNotEqual(result["id"], self.report.id)
        self.assertEqual(result["kpi_count"], 2)

    def test_kpi_list(self):
        """Test mis_kpi_list tool"""
        result = self.env["mis.report.kpi"].mis_kpi_list(report_id=self.report.id)
        self.assertEqual(result["report_id"], self.report.id)
        self.assertEqual(len(result["kpis"]), 2)

    def test_kpi_create(self):
        """Test mis_kpi_create tool"""
        result = self.env["mis.report.kpi"].mis_kpi_create(
            report_id=self.report.id,
            name="profit",
            description="Net Profit",
            expression="revenue - expenses",
            sequence=30,
        )
        self.assertIn("id", result)
        self.assertEqual(result["name"], "profit")

    def test_kpi_update(self):
        """Test mis_kpi_update tool"""
        result = self.env["mis.report.kpi"].mis_kpi_update(
            kpi_id=self.kpi_revenue.id,
            description="Updated Revenue",
            expression="bal[700,701,702]",
        )
        self.assertEqual(result["id"], self.kpi_revenue.id)

        # Verify changes
        self.kpi_revenue.invalidate_recordset()
        self.assertEqual(self.kpi_revenue.description, "Updated Revenue")

    def test_instance_list(self):
        """Test mis_instance_list tool"""
        result = self.env["mis.report.instance"].mis_instance_list(
            report_id=self.report.id
        )
        self.assertIn("instances", result)
        self.assertGreater(len(result["instances"]), 0)

    def test_instance_get(self):
        """Test mis_instance_get tool"""
        result = self.env["mis.report.instance"].mis_instance_get(
            instance_id=self.instance.id
        )
        self.assertEqual(result["id"], self.instance.id)
        self.assertEqual(result["name"], "Test Instance")
        self.assertIn("periods", result)

    def test_instance_create(self):
        """Test mis_instance_create tool"""
        result = self.env["mis.report.instance"].mis_instance_create(
            report_id=self.report.id,
            name="New Instance",
            date_from="2024-02-01",
            date_to="2024-02-29",
            temporary=True,
        )
        self.assertIn("id", result)
        self.assertEqual(result["name"], "New Instance")
        self.assertTrue(result["temporary"])

    def test_period_create(self):
        """Test mis_period_create tool"""
        # Create a comparison-mode instance first
        instance = self.env["mis.report.instance"].create({
            "name": "Comparison Instance",
            "report_id": self.report.id,
            "company_id": self.env.company.id,
        })

        result = self.env["mis.report.instance.period"].mis_period_create(
            instance_id=instance.id,
            name="Current Month",
            source="actuals",
            mode="relative",
            period_type="m",
            offset=0,
            duration=1,
        )
        self.assertIn("id", result)
        self.assertEqual(result["name"], "Current Month")
        self.assertTrue(result["valid"])

    def test_period_add_comparison(self):
        """Test mis_period_add_comparison tool"""
        # Create instance with two periods
        instance = self.env["mis.report.instance"].create({
            "name": "Comparison Test",
            "report_id": self.report.id,
            "company_id": self.env.company.id,
        })

        period1 = self.env["mis.report.instance.period"].create({
            "report_instance_id": instance.id,
            "name": "This Month",
            "mode": "relative",
            "type": "m",
            "offset": 0,
            "sequence": 10,
        })

        period2 = self.env["mis.report.instance.period"].create({
            "report_instance_id": instance.id,
            "name": "Last Month",
            "mode": "relative",
            "type": "m",
            "offset": -1,
            "sequence": 20,
        })

        result = self.env["mis.report.instance.period"].mis_period_add_comparison(
            instance_id=instance.id,
            name="Variance",
            from_period_id=period2.id,
            to_period_id=period1.id,
        )
        self.assertIn("id", result)
        self.assertEqual(result["name"], "Variance")

    def test_style_list(self):
        """Test mis_style_list tool"""
        result = self.env["mis.report.style"].mis_style_list()
        self.assertIn("styles", result)
        self.assertIn("total_count", result)

    def test_style_create(self):
        """Test mis_style_create tool"""
        result = self.env["mis.report.style"].mis_style_create(
            name="Bold Red",
            color="#FF0000",
            font_weight="bold",
            decimal_places=2,
        )
        self.assertIn("id", result)
        self.assertEqual(result["name"], "Bold Red")

        # Verify in database
        style = self.env["mis.report.style"].browse(result["id"])
        self.assertEqual(style.color, "#FF0000")
        self.assertEqual(style.font_weight, "bold")

    def test_report_preview(self):
        """Test mis_report_preview tool"""
        result = self.env["mis.report.instance"].mis_report_preview(
            report_id=self.report.id,
            date_from="2024-01-01",
            date_to="2024-01-31",
        )
        self.assertEqual(result["report_id"], self.report.id)
        self.assertIn("rows", result)
        # Rows may be empty if no accounting data, but should return structure
        self.assertIsInstance(result["rows"], list)
