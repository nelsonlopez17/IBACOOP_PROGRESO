from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'APPS.core'
    verbose_name = 'Core — Base del Sistema'

    def ready(self):
        """
        Estandariza el formateo numérico y de moneda:
        - floatformat utiliza automáticamente agrupación de millares con coma (ej. 4,100.50).
        - Los enteros regulares (años, IDs, códigos) no sufren agrupación de millares (ej. 2026).
        """
        import django.template.defaultfilters as df
        _orig_floatformat = df.floatformat

        def patched_floatformat(text, arg=-1):
            if isinstance(arg, int):
                arg = f"{arg}g"
            elif isinstance(arg, str) and not (arg.endswith('g') or arg.endswith('u')):
                arg = f"{arg}g"
            return _orig_floatformat(text, arg)

        df.register.filter('floatformat', patched_floatformat, is_safe=True)
        df.floatformat = patched_floatformat
