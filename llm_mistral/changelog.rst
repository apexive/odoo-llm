18.0.1.0.3 (2026-01-13)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Added mistral_get_default_ocr_model() method for unified OCR model selection
* [IMP] Single source of truth for OCR model selection across all consumers

18.0.1.0.2 (2026-01-07)
~~~~~~~~~~~~~~~~~~~~~~~

* [REM] Removed provider data file - users now create providers manually
* [IMP] Provider data is now user-owned and survives module uninstall

18.0.1.0.1 (2025-11-17)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Removed wizard override - model fetching now handled by base provider
* [IMP] Reordered OCR capability detection to check string patterns before API capabilities
* [ADD] Added _determine_model_use() override for OCR model classification
* [REM] Removed wizards directory and related imports

18.0.1.0.0 (2025-10-23)
~~~~~~~~~~~~~~~~~~~~~~~

* [MIGRATION] Migrated to Odoo 18.0
* [IMP] Updated views and manifest for compatibility
