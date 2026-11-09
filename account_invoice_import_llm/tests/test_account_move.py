from unittest.mock import patch

from odoo.tools import file_open

from odoo.addons.account.models.account_move import AccountMove as AccountMoveBase
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestAccountMoveLlmImport(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invoice = cls.env["account.move"].create(
            {
                "journal_id": cls.company_data["default_journal_purchase"].id,
                "move_type": "in_invoice",
            }
        )
        with file_open(
            "account_invoice_import/tests/pdf/unknown_invoice.pdf", "rb"
        ) as pdf_file:
            pdf_content = pdf_file.read()
        cls.attachment = cls.env["ir.attachment"].create(
            {
                "name": "vendor_bill.pdf",
                "raw": pdf_content,
                "mimetype": "application/pdf",
            }
        )
        cls.file_data = {
            "attachment": cls.attachment,
            "content": cls.attachment.raw,
            "filename": cls.attachment.name,
            "type": "pdf",
        }

    def test_email_pdf_uses_llm_decoder(self):
        invoice = self.invoice.with_context(from_alias=True)
        decoder = invoice._get_edi_decoder(self.file_data, new=True)

        self.assertEqual(decoder.__name__, "_import_invoice_with_llm")

        pivot_data = {"invoice_number": "LLM-001"}
        extracted = []
        updated = []

        def extract(_ocr, content, company=None, mimetype="application/pdf"):
            extracted.append((content, company, mimetype))
            return pivot_data

        def update(move, values):
            updated.append((move, values))

        ocr_model = type(self.env["account.invoice.import.ocr"])
        move_model = type(self.env["account.move"])
        with (
            patch.object(ocr_model, "extract_invoice_data", extract),
            patch.object(move_model, "_update_invoice_from_pivot", update),
        ):
            attachments_by_invoice = invoice._check_and_decode_attachment(
                self.attachment
            )

        self.assertEqual(attachments_by_invoice[self.attachment], invoice)
        self.assertEqual(
            extracted,
            [(self.attachment.raw, invoice.company_id, "application/pdf")],
        )
        self.assertEqual(updated[0][0], invoice)
        self.assertTrue(updated[0][0].env.context["skip_is_manually_modified"])
        self.assertEqual(updated[0][1], pivot_data)

    def test_non_email_pdf_does_not_use_llm_decoder(self):
        decoder = self.invoice._get_edi_decoder(self.file_data, new=True)

        self.assertFalse(decoder and decoder.__name__ == "_import_invoice_with_llm")

    def test_edi_decoder_takes_priority_over_llm(self):
        def edi_decoder(invoice, file_data, new=False):
            return True

        with patch.object(
            AccountMoveBase, "_get_edi_decoder", return_value=edi_decoder
        ):
            decoder = self.invoice.with_context(from_alias=True)._get_edi_decoder(
                self.file_data, new=True
            )

        self.assertIs(decoder, edi_decoder)

    def test_manual_action_uses_shared_llm_importer(self):
        self.attachment.write({"res_model": "account.move", "res_id": self.invoice.id})
        imported = []

        def import_invoice(move, invoice, file_data, new=False):
            imported.append((move, invoice, file_data, new))
            return True

        move_model = type(self.env["account.move"])
        with patch.object(move_model, "_import_invoice_with_llm", import_invoice):
            action = self.invoice.action_process_with_llm()

        self.assertEqual(imported[0][0], self.invoice)
        self.assertEqual(imported[0][1], self.invoice)
        self.assertEqual(imported[0][2]["attachment"], self.attachment)
        self.assertEqual(imported[0][2]["content"], self.attachment.raw)
        self.assertFalse(imported[0][3])
        self.assertEqual(action["res_id"], self.invoice.id)

    def test_customer_invoice_email_does_not_use_llm_decoder(self):
        customer_invoice = self.env["account.move"].create(
            {
                "journal_id": self.company_data["default_journal_sale"].id,
                "move_type": "out_invoice",
            }
        )
        decoder = customer_invoice.with_context(from_alias=True)._get_edi_decoder(
            self.file_data, new=True
        )

        self.assertFalse(decoder and decoder.__name__ == "_import_invoice_with_llm")
