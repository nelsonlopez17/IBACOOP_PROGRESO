"""
APPS/core/seguridad.py

Intermediario (Middleware) para incorporar cabeceras de proteccion HTTP,
incluyendo Content Security Policy (CSP), Referrer Policy y restricciones de navegacion.
"""

class CabecerasSeguridadMiddleware:
    """
    Agrega cabeceras de seguridad estandar a todas las respuestas salientes.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Content Security Policy (CSP) sin comodines ni dominios externos superfluos
        csp_directivas = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline'",
            "font-src 'self' data:",
            "img-src 'self' data: https://drive.google.com https://*.googleusercontent.com https://placehold.co https://images.unsplash.com",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers['Content-Security-Policy'] = "; ".join(csp_directivas)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'

        return response
