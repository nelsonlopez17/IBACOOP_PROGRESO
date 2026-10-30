"""
reportes/generadores/base_csv.py

Motor de exportación tabular a CSV con codificación UTF-8 BOM.
Garantiza apertura nativa y correcta de tildes y columnas en Microsoft Excel y Google Sheets.
"""
import csv
from django.http import HttpResponse
from django.utils import timezone


class IBACOOPReportCSV:
    """Constructor de archivos CSV tabulares compatibles con Excel."""

    @staticmethod
    def generate_csv_response(filename_prefix, headers, rows):
        """
        Genera y retorna un HttpResponse con el contenido CSV.
        """
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        fecha_str = timezone.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{fecha_str}.csv"'

        # inclusion de marca de orden de bytes utf ocho para hojas de calculo
        response.write('\ufeff')
        writer = csv.writer(response)

        writer.writerow(['INSTITUTO DE EDUCACIÓN BÁSICA EL PROGRESO (IBACOOP)'])
        writer.writerow([f'REPORTE: {filename_prefix.upper()}', f'EMISIÓN: {timezone.now().strftime("%d/%m/%Y %H:%M:%S")}'])
        writer.writerow([])  # fila vacia separadora

        writer.writerow(headers)

        # saneamiento de celdas para prevenir inyeccion de formulas csv
        for row in rows:
            sanitized_row = [
                f"'{c}" if isinstance(c, str) and c and c[0] in ('=', '+', '-', '@', '\t', '\r') else c
                for c in row
            ]
            writer.writerow(sanitized_row)

        return response
