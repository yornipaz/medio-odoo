import uuid
from odoo import models, fields, api


class MailMessage(models.Model):
    _inherit = "mail.message"

    message_id_provider_chat = fields.Char(
        string="ID del mensaje del proveedor",
        index=True,
        readonly=True,
        copy=False,
        # ✅ MANTENER EL UUID - Tu lógica es correcta
        default=lambda self: str(uuid.uuid4()),
        help="UUID único para tracking de mensajes con proveedores externos",
    )

    # ✅ CAMPO PARA IDENTIFICAR ORIGEN
    is_from_webhook = fields.Boolean(
        string="Mensaje de Webhook",
        default=False,
        readonly=True,
        copy=False,
        help="Indica si este mensaje proviene de un webhook externo",
    )

    # ✅ MÉTODO PARA VERIFICAR DUPLICADOS MEJORADO
    @api.model
    def check_duplicate_by_provider_id(self, provider_message_id):
        """
        Verificar si ya existe un mensaje con este provider_message_id
        """
        if not provider_message_id:
            return False

        return self.search(
            [("message_id_provider_chat", "=", provider_message_id)], limit=1
        )
