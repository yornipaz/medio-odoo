from odoo import models, fields, api, _


class ChatChannelType(models.Model):
    _name = "chat.channel.type"
    _description = "Tipo de Canal"

    name = fields.Char(string="Nombre del Canal", required=True)
    code = fields.Char(
        string="Código", required=True, help="Ej: whatsapp, telegram, etc."
    )

    active = fields.Boolean(string="Activo", default=True)
