{
    "name": "Web JSON Editor",
    "version": "19.0.1.0.0",
    "category": "Web",
    "summary": "JSON Editor widget for Odoo",
    "description": """
        Provides a reusable JSON Editor widget for Odoo with schema-based autocomplete.
        Features:
        - JSON syntax highlighting
        - Schema-based autocomplete
        - Multiple view modes (code, tree, form, view)
        - Validation
    """,
    "depends": [
        "web",
    ],
    "assets": {
        "web.assets_backend": [
            # JSONEditor library
            "web_json_editor/static/lib/jsoneditor/jsoneditor.min.js",
            "web_json_editor/static/lib/jsoneditor/jsoneditor.min.css",
            "web_json_editor/static/lib/jsoneditor/img/jsoneditor-icons.svg",
            # Field widget
            "web_json_editor/static/src/fields/json_field.js",
            "web_json_editor/static/src/fields/json_field.xml",
            "web_json_editor/static/src/fields/json_field.scss",
            # OWL Component
            "web_json_editor/static/src/components/json_editor/json_editor.js",
            "web_json_editor/static/src/components/json_editor/json_editor.xml",
        ],
    },
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
