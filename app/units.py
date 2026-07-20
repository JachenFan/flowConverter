from typing import Dict


VOLUMETRIC_UNITS: Dict[str, float] = {
    'sccm': 1.66667e-8,
    'slm': 1.66667e-5,
    'scfh': 7.86579e-6,
    'L/min': 1.66667e-5,
    'mL/min': 1.66667e-8,
    'm\u00b3/h': 1.0 / 3600.0,
    'CFM': 0.000471947,
}

MASS_UNITS: Dict[str, float] = {
    'g/s': 0.001,
    'g/min': 0.001 / 60.0,
    'kg/h': 1.0 / 3600.0,
    'lb/h': 0.000125998,
}

MOLAR_UNITS: Dict[str, float] = {
    'mol/s': 1.0,
    'mol/min': 1.0 / 60.0,
    'kmol/h': 1000.0 / 3600.0,
}

STD_VOL_UNITS = frozenset({'sccm', 'slm', 'scfh'})

VOLUMETRIC_LABELS: Dict[str, str] = {
    'sccm': 'sccm',
    'slm': 'slm',
    'scfh': 'scfh',
    'L/min': 'L/min',
    'mL/min': 'mL/min',
    'm\u00b3/h': 'm\u00b3/h',
    'CFM': 'CFM',
}

MASS_LABELS: Dict[str, str] = {
    'g/s': 'g/s',
    'g/min': 'g/min',
    'kg/h': 'kg/h',
    'lb/h': 'lb/h',
}

MOLAR_LABELS: Dict[str, str] = {
    'mol/s': 'mol/s',
    'mol/min': 'mol/min',
    'kmol/h': 'kmol/h',
}

PRESSURE_UNITS: Dict[str, float] = {
    'Pa': 1.0,
    'hPa': 100.0,
    'kPa': 1000.0,
    'MPa': 1000000.0,
    'bar': 100000.0,
    'mbar': 100.0,
    'atm': 101325.0,
    'Torr': 133.322,
    'mTorr': 0.133322,
    'psi': 6894.757,
}

PRESSURE_LABELS: Dict[str, str] = {
    'Pa': 'Pa',
    'hPa': 'hPa',
    'kPa': 'kPa',
    'MPa': 'MPa',
    'bar': 'bar',
    'mbar': 'mbar',
    'atm': 'atm',
    'Torr': 'Torr',
    'mTorr': 'mTorr',
    'psi': 'psi',
}


def get_unit_type(unit_key: str) -> str:
    if unit_key in VOLUMETRIC_UNITS:
        return 'volumetric'
    if unit_key in MASS_UNITS:
        return 'mass'
    if unit_key in MOLAR_UNITS:
        return 'molar'
    raise ValueError(f'Unknown unit: {unit_key}')


def to_base(value: float, unit_key: str, unit_type: str) -> float:
    if unit_type == 'volumetric':
        return value * VOLUMETRIC_UNITS[unit_key]
    if unit_type == 'mass':
        return value * MASS_UNITS[unit_key]
    return value * MOLAR_UNITS[unit_key]


def from_base(value_base: float, unit_key: str, unit_type: str) -> float:
    if unit_type == 'volumetric':
        return value_base / VOLUMETRIC_UNITS[unit_key]
    if unit_type == 'mass':
        return value_base / MASS_UNITS[unit_key]
    return value_base / MOLAR_UNITS[unit_key]
