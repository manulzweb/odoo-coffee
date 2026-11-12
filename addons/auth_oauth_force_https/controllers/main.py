import json
import werkzeug.urls

from odoo import http
from odoo.http import request
from odoo.addons.auth_oauth.controllers.main import OAuthLogin


class OAuthLoginForceHTTPS(OAuthLogin):

    def list_providers(self):
        providers = super().list_providers()

        for provider in providers:
            # reconstruimos el redirect_uri con https forzado
            root = request.httprequest.url_root
            root = root.replace("http://", "https://")

            return_url = root + "auth_oauth/signin"

            state = self.get_state(provider)

            params = dict(
                response_type='token',
                client_id=provider['client_id'],
                redirect_uri=return_url,
                scope=provider['scope'],
                state=json.dumps(state),
            )

            provider['auth_link'] = "%s?%s" % (
                provider['auth_endpoint'],
                werkzeug.urls.url_encode(params)
            )

        return providers
