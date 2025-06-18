from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # OPCIÓN 1: Campo Many2many simple (recomendado)
    chat_provider_ids = fields.Many2many(
        "chat.provider",
        string="Proveedores de Chat Configurados",
        help="Selecciona los proveedores de chat que deseas configurar",
    )

    # OPCIÓN 2: Si necesitas mostrar TODOS los proveedores existentes
    # chat_provider_ids = fields.Many2many(
    #     "chat.provider",
    #     string="Proveedores de Chat Configurados",
    #     compute="_compute_chat_providers",
    #     inverse="_inverse_chat_providers",
    #     store=False,
    # )

    # def _compute_chat_providers(self):
    #     """Obtiene todos los proveedores de chat existentes"""
    #     for record in self:
    #         providers = self.env["chat.provider"].search([])
    #         record.chat_provider_ids = providers

    # def _inverse_chat_providers(self):
    #     """Método inverso para manejar cambios en el campo computado"""
    #     # Aquí puedes manejar la lógica cuando se modifiquen los proveedores
    #     pass

    # Método para obtener proveedores activos
    @api.model
    def get_active_providers(self):
        """Retorna los proveedores activos"""
        return self.env["chat.provider"].search([("is_active", "=", True)])

    # Método para crear un nuevo proveedor desde configuración
    def create_new_provider(self):
        """Abre el formulario para crear un nuevo proveedor"""
        return {
            "type": "ir.actions.act_window",
            "name": "Nuevo Proveedor de Chat",
            "res_model": "chat.provider",
            "view_mode": "form",
            "target": "new",
            "context": {"default_is_active": True},
        }
