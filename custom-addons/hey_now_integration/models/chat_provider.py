import json
import base64
from cryptography.fernet import Fernet
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ChatProvider(models.Model):
    _name = "chat.provider"
    _description = "Configuración de Proveedor de Chat"
    _order = "provider_type"

    name = fields.Char(
        string="Nombre visible", required=True, help="Nombre del proveedor"
    )
    provider_type = fields.Selection(
        [
            ("heynow", "HeyNow"),
            ("botpress", "Botpress"),
            ("twilio", "Twilio"),
            ("meta", "Meta"),
            ("viber", "Viber"),
            ("whatsapp", "WhatsApp"),
            ("telegram", "Telegram"),
            ("line", "Line"),
            ("messenger", "Messenger"),
            ("instagram", "Instagram"),
            ("facebook", "Facebook"),
            ("google", "Google"),
        ],
        string="Tipo de Proveedor",
        required=True,
    )

    is_active = fields.Boolean(string="Activo", default=True)
    _auth_token_encrypted = fields.Text(string="Encrypted Token", readonly=True)
    _encryption_key = fields.Text(string="Encryption Key", readonly=True)

    # Campo computed para usar en las vistas (reemplaza la propiedad)
    auth_token = fields.Char(
        string="Token de Autenticación",
        compute="_compute_auth_token",
        inverse="_inverse_auth_token",
        password=True,  # Indica que es una contraseña
        store=False,  # No se almacena directamente
        help="Token de autenticación del proveedor (se guarda cifrado)",
    )

    base_url = fields.Char(
        string="URL Base",
        required=True,
        help="URL Base del proveedor para envíos de mensajes",
    )

    allowed_channel_ids = fields.Many2many(
        "chat.channel.type",
        string="Canales Permitidos",
        help="Selecciona los canales que este proveedor manejará.",
    )

    config_extra = fields.Text(
        string="Configuración adicional (JSON)",
        help="Puedes definir configuraciones avanzadas aquí",
    )

    # -----------------------
    # Métodos para el campo computed
    @api.depends("_auth_token_encrypted")
    def _compute_auth_token(self):
        """Compute method para mostrar el token descifrado"""
        for record in self:
            if record._auth_token_encrypted and record._encryption_key:
                record.auth_token = record._decrypt_token(record._auth_token_encrypted)
            else:
                record.auth_token = ""

    def _inverse_auth_token(self):
        """Inverse method para guardar el token cifrado"""
        for record in self:
            if record.auth_token:
                record._auth_token_encrypted = record._encrypt_token(record.auth_token)
            else:
                record._auth_token_encrypted = ""

    # -----------------------
    # Métodos de cifrado personalizados
    def _encrypt_token(self, token):
        """Cifra un token usando Fernet"""
        if not token:
            return ""

        # Generar clave si no existe
        if not self._encryption_key:
            key = Fernet.generate_key()
            self._encryption_key = base64.b64encode(key).decode()
        else:
            key = base64.b64decode(self._encryption_key.encode())

        f = Fernet(key)
        encrypted_token = f.encrypt(token.encode())
        return base64.b64encode(encrypted_token).decode()

    def _decrypt_token(self, encrypted_token):
        """Descifra un token usando Fernet"""
        if not encrypted_token or not self._encryption_key:
            return ""

        try:
            key = base64.b64decode(self._encryption_key.encode())
            f = Fernet(key)
            decrypted_data = base64.b64decode(encrypted_token.encode())
            return f.decrypt(decrypted_data).decode()
        except Exception:
            return ""

    # -----------------------
    # Métodos auxiliares (mantener para compatibilidad)
    def set_auth_token(self, token):
        """Establece el token de autenticación de forma segura"""
        self.ensure_one()
        if token:
            self._auth_token_encrypted = self._encrypt_token(token)
        else:
            self._auth_token_encrypted = ""

    def get_auth_token(self):
        """Obtiene el token de autenticación descifrado"""
        self.ensure_one()
        if self._auth_token_encrypted:
            return self._decrypt_token(self._auth_token_encrypted)
        return ""

    # -----------------------
    # Config Extra como diccionario
    def get_config_extra_dict(self):
        """Convierte config_extra de JSON string a diccionario"""
        self.ensure_one()
        if self.config_extra:
            try:
                return json.loads(self.config_extra)
            except json.JSONDecodeError:
                raise ValidationError(
                    _(
                        "El campo de configuración adicional debe tener formato JSON válido."
                    )
                )
        return {}

    @api.constrains("allowed_channel_ids")
    def _check_allowed_channels(self):
        """Valida que se seleccione al menos un canal"""
        for record in self:
            if not record.allowed_channel_ids:
                raise ValidationError(
                    _("Debes seleccionar al menos un canal permitido.")
                )

    @api.constrains("provider_type", "is_active")
    def _check_unique_active_provider(self):
        """Valida que solo haya un proveedor activo por tipo"""
        for record in self:
            if record.is_active:
                existing = self.search(
                    [
                        ("provider_type", "=", record.provider_type),
                        ("is_active", "=", True),
                        ("id", "!=", record.id),
                    ]
                )
                if existing:
                    raise ValidationError(
                        _(
                            "Ya existe una configuración activa para el proveedor '%s'. Solo puede haber una activa."
                        )
                        % record.provider_type
                    )

    def toggle_active(self):
        """Alterna el estado activo del proveedor"""
        for rec in self:
            rec.is_active = not rec.is_active
