from typing import Optional, Tuple
from .units import (
    VOLUMETRIC_UNITS, MASS_UNITS, MOLAR_UNITS, STD_VOL_UNITS,
    get_unit_type, to_base, from_base,
)
from .gas_db import GasDatabase, GasInfo


R = 8.314462618
STD_T_K = 273.15
STD_P_PA = 101325.0



def volumetric_to_molar(m3s: float, temp_K: float, pressure_Pa: float, is_std: bool) -> float:
    t = STD_T_K if is_std else temp_K
    p = STD_P_PA if is_std else pressure_Pa
    return m3s * p / (R * t)


def molar_to_volumetric(mols: float, temp_K: float, pressure_Pa: float, is_std: bool) -> float:
    t = STD_T_K if is_std else temp_K
    p = STD_P_PA if is_std else pressure_Pa
    return mols * R * t / p


def mass_to_molar(kgs: float, molar_mass: float) -> float:
    if molar_mass <= 0:
        raise ValueError('Molar mass must be positive')
    return kgs * 1000.0 / molar_mass


def molar_to_mass(mols: float, molar_mass: float) -> float:
    if molar_mass <= 0:
        raise ValueError('Molar mass must be positive')
    return mols * molar_mass / 1000.0



class FlowConverter:
    def __init__(self):
        self._gas_db = GasDatabase()
        self._temp_K: float = STD_T_K
        self._pressure_Pa: float = STD_P_PA
        self._molar_mass: float = 28.0134
        self._gas_key: str = 'N2'
        self._molar_flow_mol_s: float = 0.0

    @property
    def temp_K(self) -> float:
        return self._temp_K

    @property
    def temp_C(self) -> float:
        return self._temp_K - 273.15

    @property
    def pressure_Pa(self) -> float:
        return self._pressure_Pa

    @property
    def pressure_atm(self) -> float:
        return self._pressure_Pa / 101325.0

    @property
    def molar_mass(self) -> float:
        return self._molar_mass

    @property
    def gas_key(self) -> str:
        return self._gas_key

    @property
    def gas_db(self) -> GasDatabase:
        return self._gas_db

    def set_temperature(self, temp_C: float):
        k = temp_C + 273.15
        if k <= 0:
            raise ValueError('Temperature must be above absolute zero')
        self._temp_K = k

    def set_pressure(self, pressure_atm: float):
        pa = pressure_atm * 101325.0
        if pa <= 0:
            raise ValueError('Pressure must be positive')
        self._pressure_Pa = pa

    def set_gas(self, gas_key: str) -> bool:
        gas = self._gas_db.get(gas_key)
        if gas is None:
            return False
        self._gas_key = gas_key
        self._molar_mass = gas.molar_mass
        return True

    def set_molar_flow(self, mol_s: float):
        self._molar_flow_mol_s = mol_s

    def set_from(self, value: float, unit_key: str):
        utype = get_unit_type(unit_key)
        base = to_base(value, unit_key, utype)
        if utype == 'volumetric':
            mols = volumetric_to_molar(base, self._temp_K, self._pressure_Pa, unit_key in STD_VOL_UNITS)
        elif utype == 'mass':
            mols = mass_to_molar(base, self._molar_mass)
        else:
            mols = base
        self._molar_flow_mol_s = mols

    def get_volumetric(self, unit_key: str) -> float:
        is_std = unit_key in STD_VOL_UNITS
        m3s = molar_to_volumetric(self._molar_flow_mol_s, self._temp_K, self._pressure_Pa, is_std)
        return from_base(m3s, unit_key, 'volumetric')

    def get_mass(self, unit_key: str) -> float:
        kgs = molar_to_mass(self._molar_flow_mol_s, self._molar_mass)
        return from_base(kgs, unit_key, 'mass')

    def get_molar(self, unit_key: str) -> float:
        return from_base(self._molar_flow_mol_s, unit_key, 'molar')

    def get_all_volumetric(self) -> dict:
        return {k: self.get_volumetric(k) for k in VOLUMETRIC_UNITS}

    def get_all_mass(self) -> dict:
        return {k: self.get_mass(k) for k in MASS_UNITS}

    def get_all_molar(self) -> dict:
        return {k: self.get_molar(k) for k in MOLAR_UNITS}

    def convert_ratio(
        self,
        value_a: float,
        unit_a: str,
        gas_a_mm: float,
        unit_b: str,
        gas_b_mm: float,
        ratio_a: float,
        ratio_b: float,
        temp_K: Optional[float] = None,
        pressure_Pa: Optional[float] = None,
        temp_a_K: Optional[float] = None,
        pressure_a_Pa: Optional[float] = None,
        temp_b_K: Optional[float] = None,
        pressure_b_Pa: Optional[float] = None,
    ) -> float:
        t_a = temp_a_K if temp_a_K is not None else (temp_K if temp_K is not None else self._temp_K)
        p_a = pressure_a_Pa if pressure_a_Pa is not None else (pressure_Pa if pressure_Pa is not None else self._pressure_Pa)
        t_b = temp_b_K if temp_b_K is not None else (temp_K if temp_K is not None else self._temp_K)
        p_b = pressure_b_Pa if pressure_b_Pa is not None else (pressure_Pa if pressure_Pa is not None else self._pressure_Pa)
        if ratio_a == 0:
            raise ValueError('Ratio A cannot be zero')
        utype_a = get_unit_type(unit_a)
        base_a = to_base(value_a, unit_a, utype_a)
        if utype_a == 'volumetric':
            mol_a = volumetric_to_molar(base_a, t_a, p_a, unit_a in STD_VOL_UNITS)
        elif utype_a == 'mass':
            mol_a = mass_to_molar(base_a, gas_a_mm)
        else:
            mol_a = base_a
        mol_b = mol_a * ratio_b / ratio_a
        utype_b = get_unit_type(unit_b)
        if utype_b == 'volumetric':
            base_b = molar_to_volumetric(mol_b, t_b, p_b, unit_b in STD_VOL_UNITS)
        elif utype_b == 'mass':
            base_b = molar_to_mass(mol_b, gas_b_mm)
        else:
            base_b = mol_b
        return from_base(base_b, unit_b, utype_b)

    def calc_ratio(
        self,
        value_a: float,
        unit_a: str,
        gas_a_mm: float,
        value_b: float,
        unit_b: str,
        gas_b_mm: float,
        temp_K: Optional[float] = None,
        pressure_Pa: Optional[float] = None,
        temp_a_K: Optional[float] = None,
        pressure_a_Pa: Optional[float] = None,
        temp_b_K: Optional[float] = None,
        pressure_b_Pa: Optional[float] = None,
    ) -> Tuple[float, float]:
        t_a = temp_a_K if temp_a_K is not None else (temp_K if temp_K is not None else self._temp_K)
        p_a = pressure_a_Pa if pressure_a_Pa is not None else (pressure_Pa if pressure_Pa is not None else self._pressure_Pa)
        t_b = temp_b_K if temp_b_K is not None else (temp_K if temp_K is not None else self._temp_K)
        p_b = pressure_b_Pa if pressure_b_Pa is not None else (pressure_Pa if pressure_Pa is not None else self._pressure_Pa)
        utype_a = get_unit_type(unit_a)
        base_a = to_base(value_a, unit_a, utype_a)
        if utype_a == 'volumetric':
            mol_a = volumetric_to_molar(base_a, t_a, p_a, unit_a in STD_VOL_UNITS)
        elif utype_a == 'mass':
            mol_a = mass_to_molar(base_a, gas_a_mm)
        else:
            mol_a = base_a
        utype_b = get_unit_type(unit_b)
        base_b = to_base(value_b, unit_b, utype_b)
        if utype_b == 'volumetric':
            mol_b = volumetric_to_molar(base_b, t_b, p_b, unit_b in STD_VOL_UNITS)
        elif utype_b == 'mass':
            mol_b = mass_to_molar(base_b, gas_b_mm)
        else:
            mol_b = base_b
        if mol_a == 0:
            raise ValueError('Gas A flow cannot be zero')
        return (1.0, mol_b / mol_a)
