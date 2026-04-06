#!/usr/bin/env python3

"""Formatting helpers for effect-size units in analysis reports."""


def to_percentage_points(value: float) -> float:
    return float(value) * 100.0


def format_percentage_point_delta(value: float, decimals: int = 2) -> str:
    return f"{to_percentage_points(value):+.{decimals}f} pp"
