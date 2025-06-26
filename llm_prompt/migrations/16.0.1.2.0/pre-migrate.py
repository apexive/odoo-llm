import logging
import yaml

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration script to convert existing template_ids to single template field
    with YAML format for prompts that have multiple templates.
    """
    _logger.info("Starting migration to refactor LLM prompts to single template field")

    # First, add the new columns
    cr.execute("""
        ALTER TABLE llm_prompt 
        ADD COLUMN IF NOT EXISTS template TEXT,
        ADD COLUMN IF NOT EXISTS format VARCHAR DEFAULT 'text'
    """)

    # Get all existing prompts with their templates
    cr.execute("""
        SELECT 
            p.id as prompt_id,
            p.name as prompt_name,
            array_agg(
                json_build_object(
                    'sequence', t.sequence,
                    'role', t.role,
                    'content', t.content,
                    'condition', t.condition
                ) ORDER BY t.sequence, t.id
            ) as templates
        FROM llm_prompt p
        LEFT JOIN llm_prompt_template t ON t.prompt_id = p.id
        WHERE p.template IS NULL  -- Only process prompts that haven't been migrated yet
        GROUP BY p.id, p.name
    """)

    prompts_data = cr.fetchall()
    _logger.info(f"Found {len(prompts_data)} prompts to migrate")

    for prompt_id, prompt_name, templates in prompts_data:
        try:
            # Skip if no templates exist
            if not templates or templates == [None]:
                _logger.info(f"Prompt '{prompt_name}' has no templates, setting empty text template")
                cr.execute("""
                    UPDATE llm_prompt 
                    SET template = '', format = 'text'
                    WHERE id = %s
                """, (prompt_id,))
                continue

            # Filter out None templates (in case of LEFT JOIN with no matches)
            valid_templates = [t for t in templates if t is not None]

            if len(valid_templates) == 1:
                # Single template - use text format
                template = valid_templates[0]
                content = template.get('content', '')

                _logger.info(f"Migrating prompt '{prompt_name}' with single template to text format")
                cr.execute("""
                    UPDATE llm_prompt 
                    SET template = %s, format = 'text'
                    WHERE id = %s
                """, (content, prompt_id))

            else:
                # Multiple templates - convert to YAML format
                _logger.info(f"Migrating prompt '{prompt_name}' with {len(valid_templates)} templates to YAML format")

                yaml_data = {
                    'messages': []
                }

                for template in valid_templates:
                    role = template.get('role', 'user')
                    content = template.get('content', '')
                    condition = template.get('condition')

                    # Map role from old format to new format
                    message_type = role  # system, user, assistant remain the same

                    message = {
                        'type': message_type,
                        'content': content
                    }

                    # Add condition as a comment if it exists
                    if condition:
                        message['condition'] = condition

                    yaml_data['messages'].append(message)

                # Convert to YAML string
                yaml_content = yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True, indent=2)

                cr.execute("""
                    UPDATE llm_prompt 
                    SET template = %s, format = 'yaml'
                    WHERE id = %s
                """, (yaml_content, prompt_id))

        except Exception as e:
            _logger.error(f"Error migrating prompt '{prompt_name}' (ID: {prompt_id}): {str(e)}")
            # Set a default empty template to avoid constraint issues
            cr.execute("""
                UPDATE llm_prompt 
                SET template = '', format = 'text'
                WHERE id = %s
            """, (prompt_id,))

    _logger.info("Migration completed successfully")

    # Log some statistics
    cr.execute("SELECT COUNT(*) FROM llm_prompt WHERE format = 'text'")
    text_count = cr.fetchone()[0]

    cr.execute("SELECT COUNT(*) FROM llm_prompt WHERE format = 'yaml'")
    yaml_count = cr.fetchone()[0]

    cr.execute("SELECT COUNT(*) FROM llm_prompt WHERE format = 'json'")
    json_count = cr.fetchone()[0]

    _logger.info(f"Migration summary: {text_count} text prompts, {yaml_count} YAML prompts, {json_count} JSON prompts")
