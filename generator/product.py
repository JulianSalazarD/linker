"""Modelo de producto para cotizaciones."""
from __future__ import annotations


class Product:
    """Representa un ítem/producto en la cotización."""

    _counter = 0

    def __init__(self, qty: int, desc: str, unit: str, vr_uni_inc: int):
        Product._counter += 1
        self.item = Product._counter
        self.qty = qty
        self.desc = desc
        self.unit = unit
        self.vr_uni_inc = vr_uni_inc
        self.iva = self.vr_uni_inc * 0.19
        self.vr_total = self.vr_uni_inc + self.iva

    def get_list(self) -> list:
        return [self.qty, self.desc, self.unit, self.vr_uni_inc, self.iva, self.vr_total]

    @property
    def um(self) -> str:
        return self.unit

    @property
    def value(self) -> int:
        return self.vr_uni_inc

    @classmethod
    def reset_counter(cls) -> None:
        cls._counter = 0

    def __str__(self) -> str:
        return (
            f"Product(item={self.item}, qty={self.qty}, desc='{self.desc}', "
            f"unit='{self.unit}', vr_uni_inc={self.vr_uni_inc}, "
            f"iva={self.iva}, vr_total={self.vr_total})"
        )
