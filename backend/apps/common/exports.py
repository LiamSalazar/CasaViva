import csv

from django.http import HttpResponse


def csv_response(filename, headers, rows):
    """Build a UTF-8 CSV suitable for spreadsheet applications."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(rows)
    return response
