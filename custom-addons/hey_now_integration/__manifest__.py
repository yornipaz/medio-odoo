{
    "name": "Provider Chat Integration",
    "version": "1.0",
    "depends": ["base", "mail", "queue_job"],
    "author": "Yorni Felipe Bonilla Paz",
    "category": "Tools",
    "summary": "Integración de Proveedor Chat con mensajes directos en Odoo",
    "installable": True,
    "application": False,
    "data": [
        "security/ir.model.access.csv",  # AGREGAR ESTA LÍNEA
        "data/chat_channel_type.xml",
        "views/chat_provider_views.xml",
        "views/provider_config_settings_views.xml",
        "views/res_partner_views.xml",
    ],
    "post_init_hook": "assign_uuids_to_old_messages",
}
