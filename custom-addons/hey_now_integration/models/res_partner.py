from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    provider_user_id = fields.Char(
        string="ID de Usuario del Proveedor",
        help="ID único del usuario en el proveedor de chat",
        index=True,  # Agregar índice para mejorar búsquedas
    )
    provider_name = fields.Char(
        string="Nombre del Proveedor",
        help="Nombre del proveedor de chat",
        index=True,  # Agregar índice para mejorar búsquedas
    )

    is_provider_chat_user = fields.Boolean(
        string="Es Usuario de un Proveedor de Chat",
        default=False,
        help="Indica si este partner es un usuario que viene de un proveedor de chat",
        index=True,  # Agregar índice para mejorar filtros
    )

    def find_or_create_partner(self, provider_data: object) -> "res.partner":
        """
        Busca un partner existente por ID de usuario del proveedor o crea uno nuevo si no existe.
        Optimizado para evitar conflictos de concurrencia.
        """
        provider_user_id = provider_data.get("user_id")
        provider_name = provider_data.get("provider_name")
        provider_user_name = provider_data.get(
            "user_name", f"Usuario Desconocido {provider_name}"
        )

        if not provider_user_id:
            raise ValueError("provider_user_id is required")

        # Usar FOR UPDATE para evitar condiciones de carrera en la búsqueda
        try:
            self.env.cr.execute(
                """
                SELECT id FROM res_partner 
                WHERE provider_user_id = %s 
                ORDER BY id DESC 
                LIMIT 1
                FOR UPDATE NOWAIT
            """,
                (provider_user_id,),
            )

            result = self.env.cr.fetchone()
            if result:
                partner = self.sudo().browse(result[0])

                # Asegurar que el flag esté activado y actualizar datos si es necesario
                updates = {}
                if not partner.is_provider_chat_user:
                    updates["is_provider_chat_user"] = True

                if updates:
                    partner.write(updates)
                    _logger.info(f"Updated partner {partner.id} with: {updates}")

                return partner

        except Exception as e:
            _logger.warning(f"Error in partner lookup with lock: {e}")
            # Fallback a búsqueda normal
            partner = self.search(
                [
                    ("provider_user_id", "=", provider_user_id),
                ],
                limit=1,
            )

            if partner:
                # Asegurar que el flag esté activado si ya existía
                if not partner.is_provider_chat_user:
                    partner.write({"is_provider_chat_user": True})
                return partner

        # Si no existe, crear nuevo partner
        try:
            partner = self.sudo().create(
                {
                    "name": f"{provider_user_name}",
                    "provider_user_id": provider_user_id,
                    "provider_name": provider_name,
                    "is_provider_chat_user": True,
                }
            )
            _logger.info(
                f"Created new partner {partner.id} for provider_user_id {provider_user_id}"
            )
            return partner

        except Exception as e:
            _logger.error(f"Error creating partner: {e}")

            # Puede que otro proceso haya creado el partner mientras tanto
            # Intentar buscar de nuevo
            partner = self.sudo().search(
                [
                    ("provider_user_id", "=", provider_user_id),
                ],
                limit=1,
            )

            if partner:
                _logger.info(f"Found partner {partner.id} created by another process")
                return partner
            else:
                # Si aún no existe, re-lanzar la excepción
                raise

    _sql_constraints = [
        (
            "unique_provider_user_id",
            "UNIQUE(provider_user_id)",
            "El ID de usuario del proveedor debe ser único.",
        ),
    ]
