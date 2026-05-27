from decimal import Decimal, ROUND_HALF_UP

from fastapi.templating import Jinja2Templates


def formato_cop(value):
    if value is None:
        return "$0"
    entero = int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"$ {entero:,}".replace(",", ".")


import json

def from_json(value):
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return []

templates = Jinja2Templates(directory="templates")
templates.env.filters["cop"] = formato_cop
templates.env.filters["from_json"] = from_json
