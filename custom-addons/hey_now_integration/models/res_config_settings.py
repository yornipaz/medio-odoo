from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    provider_base_url = fields.Char(
        string="Provider Base  URL",
        config_parameter="provider.base_url",
        help="URL base de tu proveedor de chat (ejemplo: https://api.botpress.com)",
        
    )

    provider_token = fields.Char(
        string="provider chat Token",
        config_parameter="provider.token",
        help="Token de autenticación para el proveedor de chat",
        password=True,  # Para ocultar el token en la interfaz
    )
    provider_name = fields.Char(
        string="Nombre del Proveedor",
        config_parameter="provider.name",
        help="Nombre del proveedor de chat",
    )

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "provider.base_url", self.provider_base_url
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "provider.token", self.provider_token
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "provider.name", self.provider_name
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        res.update(
            provider_base_url=self.env["ir.config_parameter"]
            .sudo()
            .get_param("provider.base_url"),
            provider_token=self.env["ir.config_parameter"]
            .sudo()
            .get_param("provider.token"),
            provider_name=self.env["ir.config_parameter"]
            .sudo()
            .get_param("provider.name"),
        )
        return res
