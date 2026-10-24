"""
core/validadores.py

Reglas y validadores centralizados para formatos y longitudes de datos
según estándares oficiales de Guatemala (RENAP, MINEDUC/SIRE, SAT, SIT).
"""
import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


validador_cui_renap = RegexValidator(
    regex=r'^\d{13}$',
    message='El CUI / DPI debe contener exactamente 13 dígitos numéricos según formato RENAP / MINEDUC.'
)

validador_telefono_guatemala = RegexValidator(
    regex=r'^\d{8}$',
    message='El número de teléfono o celular en Guatemala debe contener exactamente 8 dígitos numéricos.'
)

validador_nit_sat = RegexValidator(
    regex=r'^([0-9]{1,12}-?[0-9Kk]|CF|C/F)$',
    message='Ingrese un NIT válido de la SAT (ej. 1234567-8, 1234567K o CF).'
)

validador_codigo_mineduc = RegexValidator(
    regex=r'^[A-Za-z0-9\-]{5,15}$',
    message='El Código Personal MINEDUC debe tener entre 5 y 15 caracteres alfanuméricos.'
)


def limpiar_cui_guatemala(valor: str) -> str:
    """Valida y normaliza el CUI/DPI de Guatemala a exactamente 13 dígitos numéricos."""
    if not valor:
        return valor
    limpio = valor.strip().replace(' ', '').replace('-', '')
    if len(limpio) != 13 or not limpio.isdigit():
        raise ValidationError('El CUI/DPI debe contener exactamente 13 dígitos numéricos.')
    return limpio


def limpiar_telefono_guatemala(valor: str, mensaje_error: str | None = None) -> str:
    """
    Valida que un número telefónico o celular de Guatemala tenga exactamente 8 dígitos numéricos.
    """
    if not valor:
        return valor
    limpio = valor.strip()
    if len(limpio) != 8 or not limpio.isdigit():
        raise ValidationError(
            mensaje_error or 'El número de teléfono o celular en Guatemala debe contener exactamente 8 dígitos numéricos.'
        )
    return limpio


def limpiar_nit_guatemala(valor: str) -> str:
    """
    Valida y normaliza un Número de Identificación Tributaria (NIT) de la SAT en Guatemala.
    Permite 'CF' (Consumidor Final) o dígitos con verificador numérico / K (hasta 15 caracteres).
    """
    if not valor:
        return valor
    limpio = valor.strip().upper().replace(' ', '')
    if limpio in ('CF', 'C/F'):
        return 'CF'
    if len(limpio) < 2 or len(limpio) > 15 or not re.match(r'^\d{1,12}-?[\dK]$', limpio):
        raise ValidationError(
            'Ingrese un NIT válido para Guatemala (ej. 1234567-8, 12345678, 1234567-K o CF).'
        )
    return limpio


def limpiar_codigo_mineduc(valor: str) -> str:
    """
    Valida y normaliza el Código Personal del Estudiante (MINEDUC / SIRE).
    Longitud permitida: 5 a 15 caracteres alfanuméricos o guiones.
    """
    if not valor:
        return valor
    limpio = valor.strip().upper()
    if len(limpio) < 5 or len(limpio) > 15 or not re.match(r'^[A-Z0-9\-]{5,15}$', limpio):
        raise ValidationError(
            'El Código Personal MINEDUC debe tener entre 5 y 15 caracteres alfanuméricos (ej. A123BCD).'
        )
    return limpio


def limpiar_texto_longitud(
    valor: str,
    nombre_campo: str = 'Este campo',
    min_length: int = 2,
    max_length: int = 100,
    obligatorio: bool = False,
    evitar_solo_numeros: bool = False,
) -> str:
    """Valida longitudes mínimas y máximas de cadenas de texto en el backend."""
    if valor is None:
        valor = ''
    limpio = valor.strip()
    if not limpio:
        if obligatorio:
            raise ValidationError(f'{nombre_campo} es obligatorio.')
        return limpio
    if len(limpio) < min_length:
        raise ValidationError(f'{nombre_campo} debe contener al menos {min_length} caracteres.')
    if len(limpio) > max_length:
        raise ValidationError(f'{nombre_campo} no puede exceder los {max_length} caracteres.')
    if evitar_solo_numeros and limpio.isdigit():
        raise ValidationError(f'{nombre_campo} no puede contener únicamente números.')
    return limpio
