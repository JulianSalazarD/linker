"""Modelo de producto y construcción desde respuesta del LLM."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

_PRODUCS_PATH = Path("config/producs.json")
_COTIZATION_PATH = Path("config/cotization.json")


class Product:
    _counter = 0

    def __init__(self, qty: int, desc: str, unit: str, vr_uni_inc: int):
        Product._counter += 1
        self.item = Product._counter
        self.qty = qty
        self.desc = desc
        self.unit = unit
        self.vr_uni_inc = vr_uni_inc
        self.iva = vr_uni_inc * 0.19
        self.vr_total = vr_uni_inc + self.iva

    @property
    def um(self) -> str:
        return self.unit

    @property
    def value(self) -> int:
        return self.vr_uni_inc

    def __str__(self) -> str:
        return (
            f"Product(item={self.item}, qty={self.qty}, desc='{self.desc}', "
            f"unit='{self.unit}', vr_uni_inc={self.vr_uni_inc}, "
            f"iva={self.iva}, vr_total={self.vr_total})"
        )


def flatten_cotization(config_path: str | Path = _COTIZATION_PATH) -> str:
    """Aplana cotization.json al formato {"fields": [...], "models": {...}}
    que espera extract_data. Retorna la ruta de un archivo temporal."""
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    flat_fields = []
    for producto in config["productos"]:
        pid = producto["id"]
        for field in producto["fields"]:
            flat_field = {**field, "name": f"{pid}_{field['name']}"}
            if "description" not in flat_field:
                flat_field["description"] = f"{producto['descripcion']} — {field['name']}"
            flat_fields.append(flat_field)

    flat_config = {"fields": flat_fields, "models": config["models"]}

    fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="cotization_flat_")
    tmp = Path(tmp_path)
    tmp.write_text(json.dumps(flat_config, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(tmp)


def parse_price(price_flat: dict, config_path: str | Path = _COTIZATION_PATH) -> dict:
    """Reagrupa el dict plano del LLM en sub-dicts por producto."""
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    result = {}
    for producto in config["productos"]:
        pid = producto["id"]
        sub = {}
        for field in producto["fields"]:
            key = f"{pid}_{field['name']}"
            sub[field["name"]] = price_flat.get(key)
        result[pid] = sub
    return result


def build_products(price: dict, config_path: str | Path = _PRODUCS_PATH) -> list[Product]:
    """Construye la lista de Product a partir del dict price del LLM."""
    Product._counter = 0
    with open(config_path, encoding="utf-8") as f:
        producs = json.load(f)

    products: list[Product] = []

    # Cotización principal
    p_cfg = next(p for p in producs if p["id"] == "cotizacion")
    cotizacion = price.get("cotizacion", {})
    if cotizacion.get("costo_total"):
        products.append(Product(
            cotizacion["metros"],
            p_cfg["descripción"],
            p_cfg["un. medida"],
            cotizacion["costo_total"],
        ))
    else:
        products.append(Product(
            p_cfg["cantidad"] or 0,
            p_cfg["descripción"],
            p_cfg["un. medida"],
            p_cfg["valor unitario"] or 0,
        ))

    # Productos opcionales
    for pid in ("tiene_nema_14_50", "tiene_wallbox"):
        sub = price.get(pid, {})
        if sub.get("incluido"):
            p_cfg = next(p for p in producs if p["id"] == pid)
            products.append(Product(
                p_cfg["cantidad"],
                p_cfg["descripción"],
                p_cfg["un. medida"],
                sub.get("costo") or p_cfg["valor unitario"],
            ))

    return products
