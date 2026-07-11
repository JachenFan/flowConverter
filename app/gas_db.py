from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class GasInfo:
    name: str
    formula: str
    molar_mass: float


DEFAULT_GASES: Dict[str, GasInfo] = {
    'H2':  GasInfo('氢气', 'H\u2082', 2.01588),
    'N2':  GasInfo('氮气', 'N\u2082', 28.0134),
    'Ar':  GasInfo('氩气', 'Ar', 39.948),
    'He':  GasInfo('氦气', 'He', 4.002602),
    'O2':  GasInfo('氧气', 'O\u2082', 31.9988),
    'SiH4': GasInfo('硅烷', 'SiH\u2084', 32.117),
    'NH3': GasInfo('氨气', 'NH\u2083', 17.03052),
    'CF4': GasInfo('四氟化碳', 'CF\u2084', 88.0043),
    'CH4': GasInfo('甲烷', 'CH\u2084', 16.0425),
    'PH3': GasInfo('磷化氢', 'PH\u2083', 33.99758),
    'Cl2': GasInfo('氯气', 'Cl\u2082', 70.906),
    'HCl': GasInfo('氯化氢', 'HCl', 36.461),
    'WF6': GasInfo('六氟化钨', 'WF\u2086', 297.84),
    'SF6': GasInfo('六氟化硫', 'SF\u2086', 146.055),
    'GeH4': GasInfo('锗烷', 'GeH\u2084', 76.64),
    'B2H6': GasInfo('乙硼烷', 'B\u2082H\u2086', 27.67),
    'MTS': GasInfo('甲基三氯硅烷', 'CH\u2083SiCl\u2083', 149.48),
    'DCS': GasInfo('二氯硅烷', 'SiH\u2082Cl\u2082', 101.0),
    'STC': GasInfo('四氯化硅', 'SiCl\u2084', 169.9),
    'N2O': GasInfo('一氧化二氮', 'N\u2082O', 44.0129),
    'CO2': GasInfo('二氧化碳', 'CO\u2082', 44.0095),
    'CO':  GasInfo('一氧化碳', 'CO', 28.0101),
    'C3H6': GasInfo('丙烯', 'C\u2083H\u2086', 42.08),
}


class GasDatabase:
    def __init__(self):
        self._gases: Dict[str, GasInfo] = {}
        for k, v in DEFAULT_GASES.items():
            self._gases[k] = v

    def get(self, key: str) -> Optional[GasInfo]:
        return self._gases.get(key)

    def all(self) -> Dict[str, GasInfo]:
        return dict(self._gases)

    def add(self, key: str, gas: GasInfo):
        self._gases[key] = gas

    @property
    def keys(self) -> List[str]:
        return list(self._gases.keys())

    def display_name(self, key: str) -> str:
        g = self._gases.get(key)
        if g is None:
            return key
        return f'{g.name} ({g.formula})'
