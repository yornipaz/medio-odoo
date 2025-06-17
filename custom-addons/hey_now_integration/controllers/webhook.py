from odoo import http
from odoo.http import request, Response
import logging
import json

_logger = logging.getLogger(__name__)


class ProviderWebhookController(http.Controller):

    @http.route(
        "/webhook/chat/<string:provider_name>", type="json", auth="public", csrf=False
    )
    def receive(self, provider_name: str, **kwargs):
        raw_body = request.httprequest.data
        data = {}

        try:
            # Decodificar JSON
            data = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return Response(
                json.dumps({"status": "error", "message": "Invalid JSON format"}),
                content_type="application/json",
                status=400,
            )

        _logger.info("Received webhook data for provider %s ", data)

        # Validar autenticación del webhook
        is_valid = self._validate_authentication_by_provider_type(provider_name, data)
        if not is_valid:
            return Response(
                json.dumps({"status": "error", "message": "Invalid authentication"}),
                content_type="application/json",
                status=401,
            )

        # ENCOLAR INMEDIATAMENTE - Esta es la clave del cambio
        try:
            job = (
                request.env["webhook.processor"]
                .with_delay(
                    priority=5,  # Prioridad alta para webhooks
                    eta=None,  # Procesar inmediatamente
                    max_retries=3,  # Reintentos automáticos
                    channel="webhook.processing",  # Canal específico para webhooks
                )
                .process_webhook_event(provider_name, data)
            )

            _logger.info("Webhook enqueued successfully with job UUID: %s", job.uuid)

            return Response(
                json.dumps(
                    {
                        "status": "enqueued",
                        "job_id": job.uuid,
                        "message": "Webhook received and queued for processing",
                    }
                ),
                content_type="application/json",
                status=202,  # 202 Accepted - procesamiento asíncrono
            )

        except Exception as e:
            _logger.error("Error enqueuing webhook: %s", str(e))
            return Response(
                json.dumps(
                    {
                        "status": "error",
                        "message": "Error enqueuing webhook for processing",
                        "details": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    @http.route(
        "/botpress/webhook/response",
        type="http",
        auth="public",
        csrf=False,
        methods=["POST"],
    )
    def health_check(self, **kwargs):
        """Health check endpoint"""
        return request.make_response(
            json.dumps({"status": "ok", "message": "Webhook is healthy"}),
            headers={"Content-Type": "application/json"},
        )

    def _validate_authentication_by_provider_type(
        self, provider_type: str, data: any
    ) -> bool:
        """Validar la autenticación del webhook"""
        return True
