from odoo import http
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome

class AuthSignupHomeCSPI(AuthSignupHome):

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):

        if request.params.get("enableUserRegister") != "1":
            return request.redirect("/web/login")

        return super().web_auth_signup(*args, **kw)