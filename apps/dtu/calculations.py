"""
DTU 59.1 Calculation Engine
Server-side implementation of all quotation formulas.
"""
import math
from decimal import Decimal, ROUND_HALF_UP

from .constants import (
    PAINT_COVERAGE_RATES, PAINT_PRICES, CONDITION_MULTIPLIERS,
    FILLER_QUANTITIES, FILLER_PRICES, MIN_COATS_PER_LEVEL,
    DTU_COMPLIANCE_FEES, SUBSTRATE_PREPARATIONS, STANDARD_OPENINGS,
    FIRST_COAT_TIME, ADDITIONAL_COAT_TIME,
    PRIMER_COVERAGE_RATE, PRIMER_UNIT_PRICE,
    SANDPAPER_COVERAGE, SANDPAPER_UNIT_PRICE,
    CAULK_COVERAGE, CAULK_UNIT_PRICE,
    TAPE_USEFUL_LENGTH, TAPE_UNIT_PRICE,
    TARP_UNIT_PRICE, DEFAULT_LABOR_PER_M2, DEFAULT_VAT_RATE,
    EXECUTION_CONDITIONS,
)

D = Decimal


def _ceil(val):
    return int(math.ceil(float(val)))


def compute_surface(
    *,
    length: Decimal = D('0'),
    width: Decimal = D('0'),
    height: Decimal = D('0'),
    custom_walls: list | None = None,
    doors: int = 0,
    windows: int = 0,
    include_ceiling: bool = False,
):

    if custom_walls:
        wall_gross = sum(D(str(w['width'])) * D(str(w['height'])) for w in custom_walls)
        perimeter = sum(D(str(w['width'])) for w in custom_walls)
        ceiling_area = length * width if include_ceiling else D('0')
    else:
        perimeter = 2 * (length + width)
        wall_gross = perimeter * height
        ceiling_area = length * width

    doors_sub = doors * STANDARD_OPENINGS['door_area']
    windows_sub = windows * STANDARD_OPENINGS['window_area']
    door_returns = doors * STANDARD_OPENINGS['door_return_area']
    window_returns = windows * STANDARD_OPENINGS['window_return_area']

    wall_net = max(D('0'), wall_gross - doors_sub - windows_sub + door_returns + window_returns)
    total_net = wall_net + (ceiling_area if include_ceiling else D('0'))

    return {
        'perimeter': perimeter,
        'wall_gross_area': wall_gross,
        'ceiling_area': ceiling_area,
        'doors_subtraction': doors_sub,
        'windows_subtraction': windows_sub,
        'door_returns': door_returns,
        'window_returns': window_returns,
        'wall_net_area': wall_net,
        'total_net_area': total_net,
    }


def compute_materials(
    *,
    area: Decimal,
    perimeter: Decimal,
    floor_area: Decimal,
    paint_type: str,
    dtu_level: str,
    coats: int,
    doors: int = 0,
    windows: int = 0,
):

    items = []
    coverage = PAINT_COVERAGE_RATES.get(paint_type, D('10'))
    paint_price = PAINT_PRICES.get(paint_type, D('55'))

    if dtu_level != 'D':
        qty = _ceil(area / PRIMER_COVERAGE_RATE)
        items.append({
            'material_id': 'primer',
            'name': 'Impression Universelle DTU 59.1',
            'unit': 'L',
            'quantity': qty,
            'unit_price': float(PRIMER_UNIT_PRICE),
        })

    filler_rate = FILLER_QUANTITIES.get(dtu_level, D('0'))
    if filler_rate > 0:
        qty = _ceil(area * filler_rate)
        filler_names = {
            'A': 'Enduit de lissage — Ratissage intégral (2-3 passes)',
            'B': 'Enduit de rebouchage — Lissage localisé',
            'C': 'Enduit de rebouchage — Défauts majeurs',
        }
        items.append({
            'material_id': 'filler',
            'name': filler_names.get(dtu_level, 'Enduit'),
            'unit': 'kg',
            'quantity': qty,
            'unit_price': float(FILLER_PRICES.get(dtu_level, D('4.80'))),
        })

    if dtu_level in ('A', 'B'):
        grain = '180' if dtu_level == 'A' else '120'
        qty = _ceil(area / SANDPAPER_COVERAGE)
        items.append({
            'material_id': 'sandpaper',
            'name': f'Papier abrasif grain {grain} (feuille)',
            'unit': 'pce',
            'quantity': qty,
            'unit_price': float(SANDPAPER_UNIT_PRICE),
        })

    if dtu_level in ('A', 'B'):
        qty = _ceil(perimeter / CAULK_COVERAGE) + _ceil(doors * D('0.5')) + _ceil(windows * D('0.5'))
        qty = max(1, qty)
        items.append({
            'material_id': 'caulk',
            'name': 'Mastic acrylique joints & fissures',
            'unit': 'cartouche',
            'quantity': qty,
            'unit_price': float(CAULK_UNIT_PRICE),
        })

    paint_qty = _ceil((area * coats) / coverage)
    items.append({
        'material_id': 'finish_paint',
        'name': f'Peinture Finition ({paint_type})',
        'unit': 'L',
        'quantity': paint_qty,
        'unit_price': float(paint_price),
    })

    tape_qty = _ceil(perimeter / TAPE_USEFUL_LENGTH) + doors + windows
    tape_qty = max(1, tape_qty)
    items.append({
        'material_id': 'masking_tape',
        'name': 'Ruban de masquage pro (50m)',
        'unit': 'rouleau',
        'quantity': tape_qty,
        'unit_price': float(TAPE_UNIT_PRICE),
    })

    tarp_qty = _ceil(floor_area) if floor_area > 0 else _ceil(max(perimeter, D('4')))
    items.append({
        'material_id': 'floor_protection',
        'name': 'Bâche de protection sol',
        'unit': 'm²',
        'quantity': tarp_qty,
        'unit_price': float(TARP_UNIT_PRICE),
    })

    return items


def compute_costs(
    *,
    area: Decimal,
    paint_type: str,
    dtu_level: str,
    substrate_type: str,
    condition: str,
    coats: int,
    materials: list,
    labor_per_m2: Decimal = DEFAULT_LABOR_PER_M2,
    vat_rate: Decimal = DEFAULT_VAT_RATE,
):

    hourly_rate = labor_per_m2 * 4
    condition_mult = CONDITION_MULTIPLIERS.get(condition, D('1.15'))

    ops = SUBSTRATE_PREPARATIONS.get(substrate_type, {}).get(dtu_level, [])
    prep_time = sum(op['time_per_m2'] for op in ops if op.get('required', True))
    preparation_cost = area * prep_time * hourly_rate * condition_mult

    app_time = FIRST_COAT_TIME + max(0, coats - 1) * ADDITIONAL_COAT_TIME
    application_cost = area * app_time * hourly_rate

    labor_cost = preparation_cost + application_cost

    material_cost = sum(
        D(str(m['quantity'])) * D(str(m['unit_price']))
        for m in materials
    )

    dtu_fee = area * DTU_COMPLIANCE_FEES.get(dtu_level, D('0'))

    subtotal = labor_cost + material_cost + dtu_fee
    tax = subtotal * vat_rate
    total = subtotal + tax

    return {
        'preparation_cost': float(preparation_cost.quantize(D('0.01'), ROUND_HALF_UP)),
        'application_cost': float(application_cost.quantize(D('0.01'), ROUND_HALF_UP)),
        'labor_cost': float(labor_cost.quantize(D('0.01'), ROUND_HALF_UP)),
        'material_cost': float(material_cost.quantize(D('0.01'), ROUND_HALF_UP)),
        'dtu_compliance_fee': float(dtu_fee.quantize(D('0.01'), ROUND_HALF_UP)),
        'subtotal': float(subtotal.quantize(D('0.01'), ROUND_HALF_UP)),
        'tax': float(tax.quantize(D('0.01'), ROUND_HALF_UP)),
        'total': float(total.quantize(D('0.01'), ROUND_HALF_UP)),
        'paint_liters': next(
            (m['quantity'] for m in materials if m['material_id'] == 'finish_paint'), 0
        ),
    }


def get_preparations(substrate_type: str, dtu_level: str) -> list:
    return SUBSTRATE_PREPARATIONS.get(substrate_type, {}).get(dtu_level, [])


def validate_coats(dtu_level: str, coats: int) -> int:
    min_coats = MIN_COATS_PER_LEVEL.get(dtu_level, 1)
    return max(min_coats, coats)