from . import models
from . import controllers


def assign_uuids_to_old_messages(cr, registry):
    """
    Función para regenerar todos los UUIDs usando ORM
    """
    import uuid
    from odoo.api import Environment

    env = Environment(cr, 1, {})  # Usuario admin

    # Obtener todos los mensajes existentes
    messages = env["mail.message"].search([])

    # Actualizar cada mensaje con un UUID único
    for message in messages:
        message.write({"message_id_provider_chat": str(uuid.uuid4())})

    print(f"Se regeneraron UUIDs únicos para {len(messages)} mensajes")
