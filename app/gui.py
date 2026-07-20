from typing import Dict, Optional, List
import math

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QLineEdit,
    QComboBox, QDoubleSpinBox, QPushButton, QRadioButton,
    QButtonGroup,
    QApplication, QSizePolicy, QFrame, QScrollArea,
    QTabWidget, QTextBrowser, QDialog,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QDoubleValidator

from .converter import FlowConverter, volumetric_to_molar, molar_to_volumetric, molar_to_mass, mass_to_molar, R, STD_T_K, STD_P_PA
from .units import (
    VOLUMETRIC_UNITS, MASS_UNITS, MOLAR_UNITS, STD_VOL_UNITS,
    VOLUMETRIC_LABELS, MASS_LABELS, MOLAR_LABELS,
    PRESSURE_UNITS, PRESSURE_LABELS,
    get_unit_type, to_base, from_base,
)


def _fmt(val: float, precision: int = 8) -> str:
    if val == 0.0:
        return '0'
    return f'{val:.{precision}g}'


def _parse(text: str) -> Optional[float]:
    t = text.strip().replace(',', '.')
    if t == '' or t == '-' or t == '.':
        return None
    try:
        v = float(t)
        return v
    except ValueError:
        return None


class FlowValueInput(QLineEdit):
    valueChanged = Signal(float, str)

    def __init__(self, unit_key: str, parent=None):
        super().__init__(parent)
        self._unit_key = unit_key
        self._updating = False
        self._last_valid: Optional[float] = None
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setMaximumWidth(130)
        self.setMinimumWidth(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.textChanged.connect(self._on_text_changed)

    @property
    def unit_key(self) -> str:
        return self._unit_key

    def set_value(self, val: float):
        self._updating = True
        self.setText(_fmt(val))
        self._last_valid = val
        self._updating = False

    def clear_value(self):
        self._updating = True
        self.clear()
        self._last_valid = None
        self._updating = False

    def _on_text_changed(self, text: str):
        if self._updating:
            return
        v = _parse(text)
        if v is not None:
            self._last_valid = v
            self.valueChanged.emit(v, self._unit_key)


class FlowSection(QGroupBox):
    def __init__(self, title: str, units: Dict[str, float],
                 labels: Dict[str, str], parent=None):
        super().__init__(title, parent)
        self._units = units
        self._labels = labels
        self._inputs: Dict[str, FlowValueInput] = {}

        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 12, 8, 8)

        keys = list(units.keys())
        cols = 4
        for i, k in enumerate(keys):
            row = i // cols
            col = (i % cols) * 2

            inp = FlowValueInput(k)
            self._inputs[k] = inp
            lbl = QLabel(labels.get(k, k))
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            layout.addWidget(inp, row, col)
            layout.addWidget(lbl, row, col + 1)

    @property
    def inputs(self) -> Dict[str, FlowValueInput]:
        return self._inputs

    def set_values(self, values: Dict[str, float]):
        for k, v in values.items():
            if k in self._inputs:
                self._inputs[k].set_value(v)

    def clear_values(self):
        for inp in self._inputs.values():
            inp.clear_value()

    def connect_value_changed(self, slot):
        for inp in self._inputs.values():
            inp.valueChanged.connect(slot)

    def block_signals(self, blocked: bool):
        for inp in self._inputs.values():
            inp.blockSignals(blocked)


class ConditionPanel(QGroupBox):
    changed = Signal()

    def __init__(self, gas_keys: List[str], gas_display_fn, parent=None):
        super().__init__('\u5de5\u827a\u6761\u4ef6', parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 8)
        layout.setSpacing(8)

        layout.addWidget(QLabel('\u6e29\u5ea6:'))
        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(-273.0, 2000.0)
        self._temp_spin.setDecimals(1)
        self._temp_spin.setValue(25.0)
        self._temp_spin.setSuffix(' \u00b0C')
        self._temp_spin.setSingleStep(10.0)
        self._temp_spin.setFixedWidth(130)
        layout.addWidget(self._temp_spin)

        layout.addSpacing(12)

        layout.addWidget(QLabel('\u538b\u529b:'))
        self._press_spin = QDoubleSpinBox()
        self._press_spin.setRange(0.001, 10000000.0)
        self._press_spin.setDecimals(4)
        self._press_spin.setValue(1.0)
        self._press_spin.setSingleStep(1.0)
        self._press_spin.setFixedWidth(100)
        layout.addWidget(self._press_spin)

        self._press_combo = QComboBox()
        for k in PRESSURE_UNITS:
            self._press_combo.addItem(PRESSURE_LABELS[k], k)
        self._press_combo.setCurrentIndex(self._press_combo.findData('Pa'))
        self._press_combo.setFixedWidth(75)
        layout.addWidget(self._press_combo)

        layout.addSpacing(12)

        layout.addWidget(QLabel('\u6c14\u4f53:'))
        self._gas_combo = QComboBox()
        self._gas_combo.setMinimumWidth(180)
        self._gas_keys = gas_keys
        for k in gas_keys:
            self._gas_combo.addItem(gas_display_fn(k), k)
        layout.addWidget(self._gas_combo)

        layout.addStretch()

        self._temp_spin.valueChanged.connect(self._emit)
        self._press_spin.valueChanged.connect(self._emit)
        self._press_combo.currentIndexChanged.connect(self._on_press_unit_changed)
        self._gas_combo.currentIndexChanged.connect(self._emit)

    @property
    def temp_C(self) -> float:
        return self._temp_spin.value()

    @property
    def pressure_atm(self) -> float:
        return _press_pa(self._press_spin, self._press_combo) / 101325.0

    @property
    def gas_key(self) -> str:
        return self._gas_combo.currentData()

    def block_signals(self, blocked: bool):
        self._temp_spin.blockSignals(blocked)
        self._press_spin.blockSignals(blocked)
        self._press_combo.blockSignals(blocked)
        self._gas_combo.blockSignals(blocked)

    def _emit(self):
        self.changed.emit()

    def _on_press_unit_changed(self):
        self._emit()


class FlowFromRatioPanel(QGroupBox):
    def __init__(self, gas_keys: List[str], gas_display_fn, parent=None):
        super().__init__(parent=parent)
        self._gas_keys = gas_keys

        layout = QGridLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 12, 10, 10)

        self._gas_a_combo = QComboBox()
        self._gas_b_combo = QComboBox()
        for k in gas_keys:
            self._gas_a_combo.addItem(gas_display_fn(k), k)
            self._gas_b_combo.addItem(gas_display_fn(k), k)

        idx_a = next((i for i in range(len(gas_keys)) if gas_keys[i] == 'MTS'), 0)
        idx_b = next((i for i in range(len(gas_keys)) if gas_keys[i] == 'H2'), 1)
        self._gas_a_combo.setCurrentIndex(idx_a)
        self._gas_b_combo.setCurrentIndex(idx_b)

        self._unit_a_combo = QComboBox()
        self._unit_b_combo = QComboBox()
        self._ratio_a_edit = QLineEdit('1')
        self._ratio_b_edit = QLineEdit('10')
        self._value_a_input = FlowValueInput('ratio_a')
        self._value_b_input = FlowValueInput('ratio_b')

        self._swap_btn = QPushButton('\u4ea4\u6362 A\u2194B')
        self._swap_btn.setFixedWidth(100)

        self._ratio_a_edit.setFixedWidth(55)
        self._ratio_b_edit.setFixedWidth(55)
        self._ratio_a_edit.setAlignment(Qt.AlignCenter)
        self._ratio_b_edit.setAlignment(Qt.AlignCenter)
        self._ratio_a_edit.setValidator(QDoubleValidator(0, 1e6, 4))
        self._ratio_b_edit.setValidator(QDoubleValidator(0, 1e6, 4))

        self._init_unit_combos()

        self._temp_a_spin = self._make_t_spin()
        self._press_a_spin, self._press_a_combo = self._make_press_pair()
        self._temp_b_spin = self._make_t_spin()
        self._press_b_spin, self._press_b_combo = self._make_press_pair()

        self._mode_group = QButtonGroup(self)
        rb_molar = QRadioButton('\u6469\u5c14\u6bd4')
        rb_mass = QRadioButton('\u8d28\u91cf\u6bd4')
        rb_vol = QRadioButton('\u4f53\u79ef\u6bd4')
        self._mode_group.addButton(rb_molar, 0)
        self._mode_group.addButton(rb_mass, 1)
        self._mode_group.addButton(rb_vol, 2)
        rb_molar.setChecked(True)

        layout.addWidget(QLabel('\u6c14\u4f53A:'), 0, 0)
        layout.addWidget(self._gas_a_combo, 0, 1)
        layout.addWidget(self._unit_a_combo, 0, 2)
        layout.addWidget(self._value_a_input, 0, 3)
        layout.addWidget(QLabel('\u6e29\u5ea6:'), 0, 4)
        layout.addWidget(self._temp_a_spin, 0, 5)
        layout.addWidget(QLabel('\u538b\u529b:'), 0, 6)
        layout.addWidget(self._press_a_spin, 0, 7)
        layout.addWidget(self._press_a_combo, 0, 8)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(4)
        mode_row.addWidget(QLabel('\u6bd4\u4f8b\u65b9\u5f0f:'))
        mode_row.addWidget(rb_molar)
        mode_row.addWidget(rb_mass)
        mode_row.addWidget(rb_vol)
        mode_row.addStretch()
        layout.addLayout(mode_row, 1, 0, 1, 9)

        ratio_layout = QHBoxLayout()
        ratio_layout.setSpacing(8)
        ratio_layout.addWidget(QLabel('\u6bd4\u4f8b  A : B ='))
        ratio_layout.addWidget(self._ratio_a_edit)
        ratio_layout.addSpacing(6)
        ratio_layout.addWidget(QLabel(':'))
        ratio_layout.addSpacing(6)
        ratio_layout.addWidget(self._ratio_b_edit)
        ratio_layout.addStretch()
        layout.addLayout(ratio_layout, 2, 0, 1, 9)

        layout.addWidget(QLabel('\u6c14\u4f53B:'), 3, 0)
        layout.addWidget(self._gas_b_combo, 3, 1)
        layout.addWidget(self._unit_b_combo, 3, 2)
        layout.addWidget(self._value_b_input, 3, 3)
        layout.addWidget(QLabel('\u6e29\u5ea6:'), 3, 4)
        layout.addWidget(self._temp_b_spin, 3, 5)
        layout.addWidget(QLabel('\u538b\u529b:'), 3, 6)
        layout.addWidget(self._press_b_spin, 3, 7)
        layout.addWidget(self._press_b_combo, 3, 8)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self._swap_btn)
        btn_layout.addStretch()
        self._detail_btn = QPushButton('\U0001F4CB \u67e5\u770b\u8ba1\u7b97\u6b65\u9aa4')
        self._detail_btn.setFixedHeight(28)
        self._detail_btn.clicked.connect(self._show_detail)
        btn_layout.addWidget(self._detail_btn)
        layout.addLayout(btn_layout, 4, 0, 1, 9)

        self._gas_a_combo.currentIndexChanged.connect(self._on_any_change)
        self._gas_b_combo.currentIndexChanged.connect(self._on_any_change)
        self._unit_a_combo.currentIndexChanged.connect(self._on_any_change)
        self._unit_b_combo.currentIndexChanged.connect(self._on_any_change)
        self._ratio_a_edit.textChanged.connect(self._on_any_change)
        self._ratio_b_edit.textChanged.connect(self._on_any_change)
        self._value_a_input.valueChanged.connect(self._on_value_a_changed)
        self._value_b_input.valueChanged.connect(self._on_value_b_changed)
        self._swap_btn.clicked.connect(self._swap)
        self._temp_a_spin.valueChanged.connect(self._on_any_change)
        self._press_a_spin.valueChanged.connect(self._on_any_change)
        self._press_a_combo.currentIndexChanged.connect(self._on_any_change)
        self._temp_b_spin.valueChanged.connect(self._on_any_change)
        self._press_b_spin.valueChanged.connect(self._on_any_change)
        self._press_b_combo.currentIndexChanged.connect(self._on_any_change)
        self._mode_group.idClicked.connect(lambda: self._on_any_change())

        self._updating = False

    @staticmethod
    def _make_t_spin() -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(-273.0, 2000.0)
        s.setDecimals(1)
        s.setValue(25.0)
        s.setSuffix(' \u00b0C')
        s.setSingleStep(10.0)
        s.setFixedWidth(90)
        return s

    @staticmethod
    def _make_press_pair():
        s = QDoubleSpinBox()
        s.setRange(0.001, 10000000.0)
        s.setDecimals(4)
        s.setValue(1.0)
        s.setSingleStep(1.0)
        s.setFixedWidth(90)
        c = QComboBox()
        for k in PRESSURE_UNITS:
            c.addItem(PRESSURE_LABELS[k], k)
        c.setCurrentIndex(c.findData('Pa'))
        c.setFixedWidth(75)
        return s, c

    def _init_unit_combos(self):
        for combo in [self._unit_a_combo, self._unit_b_combo]:
            for k in VOLUMETRIC_UNITS:
                combo.addItem(VOLUMETRIC_LABELS[k], f'volumetric:{k}')
            for k in MASS_UNITS:
                combo.addItem(MASS_LABELS[k], f'mass:{k}')
            for k in MOLAR_UNITS:
                combo.addItem(MOLAR_LABELS[k], f'molar:{k}')
        self._set_default_units()

    def _set_default_units(self):
        self._unit_a_combo.setCurrentIndex(
            self._unit_a_combo.findData('mass:g/min')
        )
        self._unit_b_combo.setCurrentIndex(
            self._unit_b_combo.findData('volumetric:L/min')
        )

    def get_gas_a_key(self) -> str:
        return self._gas_a_combo.currentData()

    def get_unit_a_key(self) -> str:
        d = self._unit_a_combo.currentData()
        return d.split(':', 1)[1] if d else 'g/min'

    def get_unit_a_type(self) -> str:
        d = self._unit_a_combo.currentData()
        return d.split(':', 1)[0] if d else 'mass'

    def get_gas_b_key(self) -> str:
        return self._gas_b_combo.currentData()

    def get_unit_b_key(self) -> str:
        d = self._unit_b_combo.currentData()
        return d.split(':', 1)[1] if d else 'slm'

    def get_unit_b_type(self) -> str:
        d = self._unit_b_combo.currentData()
        return d.split(':', 1)[0] if d else 'volumetric'

    def get_ratio_mode(self) -> str:
        return ['molar', 'mass', 'volumetric'][self._mode_group.checkedId()]

    def get_ratio_a(self) -> float:
        try:
            return float(self._ratio_a_edit.text())
        except ValueError:
            return 1.0

    def get_ratio_b(self) -> float:
        try:
            return float(self._ratio_b_edit.text())
        except ValueError:
            return 1.0

    def get_value_a(self) -> Optional[float]:
        return _parse(self._value_a_input.text())

    def set_value_a(self, val: float):
        self._value_a_input.set_value(val)

    def set_value_b(self, val: float):
        self._value_b_input.set_value(val)

    def _show_detail(self):
        dlg = FlowFromRatioStepsDialog(self, self.window())
        dlg.exec()

    def _on_any_change(self):
        if self._updating:
            return
        v = self.get_value_a()
        if v is not None:
            self._value_a_input.valueChanged.emit(v, 'ratio_a')

    def _on_value_a_changed(self, val: float, _: str):
        if self._updating:
            return
        self._updating = True
        self._value_b_input.clear_value()
        self._updating = False
        self._emit_calc(val, forward=True)

    def _on_value_b_changed(self, val: float, _: str):
        if self._updating:
            return
        self._updating = True
        self._value_a_input.clear_value()
        self._updating = False
        self._emit_calc(val, forward=False)

    def _emit_calc(self, val: float, forward: bool = True):
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._do_calc(val, forward))

    def _do_calc(self, val: float, forward: bool):
        ratio_a = self.get_ratio_a()
        ratio_b = self.get_ratio_b()
        if ratio_a <= 0 or ratio_b <= 0:
            return
        mode = self.get_ratio_mode()
        temp_a_K = self._temp_a_spin.value() + 273.15
        press_a_Pa = _press_pa(self._press_a_spin, self._press_a_combo)
        temp_b_K = self._temp_b_spin.value() + 273.15
        press_b_Pa = _press_pa(self._press_b_spin, self._press_b_combo)
        mm_a = _get_mm(self.get_gas_a_key())
        mm_b = _get_mm(self.get_gas_b_key())
        try:
            if forward:
                result = _convert_with_ratio(
                    val, self.get_unit_a_key(), mm_a, temp_a_K, press_a_Pa,
                    self.get_unit_b_key(), mm_b, temp_b_K, press_b_Pa,
                    ratio_a, ratio_b, mode,
                )
                self._updating = True
                self._value_a_input.set_value(val)
                self.set_value_b(result)
                self._updating = False
            else:
                result = _convert_with_ratio(
                    val, self.get_unit_b_key(), mm_b, temp_b_K, press_b_Pa,
                    self.get_unit_a_key(), mm_a, temp_a_K, press_a_Pa,
                    ratio_b, ratio_a, mode,
                )
                self._updating = True
                self._value_b_input.set_value(val)
                self.set_value_a(result)
                self._updating = False
        except Exception:
            self._updating = True
            if forward:
                self.set_value_b(0.0)
            else:
                self.set_value_a(0.0)
            self._updating = False

    def _swap(self):
        try:
            self._updating = True

            ga_idx = self._gas_a_combo.currentIndex()
            gb_idx = self._gas_b_combo.currentIndex()
            ua_idx = self._unit_a_combo.currentIndex()
            ub_idx = self._unit_b_combo.currentIndex()
            va = self._value_a_input._last_valid
            vb = self._value_b_input._last_valid
            ta = self._temp_a_spin.value()
            pa = self._press_a_spin.value()
            pau = self._press_a_combo.currentIndex()
            tb = self._temp_b_spin.value()
            pb = self._press_b_spin.value()
            pbu = self._press_b_combo.currentIndex()

            self._gas_a_combo.setCurrentIndex(gb_idx)
            self._gas_b_combo.setCurrentIndex(ga_idx)
            self._unit_a_combo.setCurrentIndex(ub_idx)
            self._unit_b_combo.setCurrentIndex(ua_idx)

            self._temp_a_spin.setValue(tb)
            self._press_a_spin.setValue(pb)
            self._press_a_combo.setCurrentIndex(pbu)
            self._temp_b_spin.setValue(ta)
            self._press_b_spin.setValue(pa)
            self._press_b_combo.setCurrentIndex(pau)

            self._value_a_input.clear_value()
            self._value_b_input.clear_value()

            rt = self._ratio_a_edit.text()
            self._ratio_a_edit.setText(self._ratio_b_edit.text())
            self._ratio_b_edit.setText(rt)

            if vb is not None:
                self._value_a_input.set_value(vb)
            if va is not None:
                self._value_b_input.set_value(va)

            self._updating = False

            if vb is not None:
                self._on_value_a_changed(vb, 'ratio_a')
        except Exception:
            self._updating = False


class RatioCalcPanel(QGroupBox):
    def __init__(self, gas_keys: List[str], gas_display_fn, parent=None):
        super().__init__(parent=parent)
        self._gas_keys = gas_keys

        layout = QGridLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 12, 10, 10)

        self._gas_a_combo = QComboBox()
        self._gas_b_combo = QComboBox()
        for k in gas_keys:
            self._gas_a_combo.addItem(gas_display_fn(k), k)
            self._gas_b_combo.addItem(gas_display_fn(k), k)

        idx_a = next((i for i in range(len(gas_keys)) if gas_keys[i] == 'MTS'), 0)
        idx_b = next((i for i in range(len(gas_keys)) if gas_keys[i] == 'H2'), 1)
        self._gas_a_combo.setCurrentIndex(idx_a)
        self._gas_b_combo.setCurrentIndex(idx_b)

        self._unit_a_combo = QComboBox()
        self._unit_b_combo = QComboBox()
        self._value_a_input = FlowValueInput('ratio_a')
        self._value_b_input = FlowValueInput('ratio_b')

        self._result_molar_b = QLabel('0')
        self._result_mass_b = QLabel('0')
        self._result_vol_b = QLabel('0')
        style = 'font-weight: bold; font-size: 13px;'
        for lbl in (self._result_molar_b, self._result_mass_b, self._result_vol_b):
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(style)

        self._swap_btn = QPushButton('\u4ea4\u6362 A\u2194B')
        self._swap_btn.setFixedWidth(100)

        self._init_unit_combos()

        self._temp_a_spin = self._make_t_spin()
        self._press_a_spin, self._press_a_combo = self._make_press_pair()
        self._temp_b_spin = self._make_t_spin()
        self._press_b_spin, self._press_b_combo = self._make_press_pair()

        layout.addWidget(QLabel('\u6c14\u4f53A:'), 0, 0)
        layout.addWidget(self._gas_a_combo, 0, 1)
        layout.addWidget(self._unit_a_combo, 0, 2)
        layout.addWidget(self._value_a_input, 0, 3)
        layout.addWidget(QLabel('\u6e29\u5ea6:'), 0, 4)
        layout.addWidget(self._temp_a_spin, 0, 5)
        layout.addWidget(QLabel('\u538b\u529b:'), 0, 6)
        layout.addWidget(self._press_a_spin, 0, 7)
        layout.addWidget(self._press_a_combo, 0, 8)

        layout.addWidget(QLabel('\u6c14\u4f53B:'), 1, 0)
        layout.addWidget(self._gas_b_combo, 1, 1)
        layout.addWidget(self._unit_b_combo, 1, 2)
        layout.addWidget(self._value_b_input, 1, 3)
        layout.addWidget(QLabel('\u6e29\u5ea6:'), 1, 4)
        layout.addWidget(self._temp_b_spin, 1, 5)
        layout.addWidget(QLabel('\u538b\u529b:'), 1, 6)
        layout.addWidget(self._press_b_spin, 1, 7)
        layout.addWidget(self._press_b_combo, 1, 8)

        def _rr(label, result):
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(QLabel(label))
            row.addWidget(QLabel('1'))
            row.addSpacing(6)
            row.addWidget(QLabel(':'))
            row.addSpacing(6)
            row.addWidget(result)
            row.addStretch()
            return row

        layout.addLayout(_rr('\u6469\u5c14\u6bd4  A : B =', self._result_molar_b), 2, 0, 1, 9)
        layout.addLayout(_rr('\u8d28\u91cf\u6bd4  A : B =', self._result_mass_b), 3, 0, 1, 9)
        layout.addLayout(_rr('\u4f53\u79ef\u6bd4  A : B =', self._result_vol_b), 4, 0, 1, 9)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self._swap_btn)
        btn_layout.addStretch()
        self._detail_btn = QPushButton('\U0001F4CB \u67e5\u770b\u8ba1\u7b97\u6b65\u9aa4')
        self._detail_btn.setFixedHeight(28)
        self._detail_btn.clicked.connect(self._show_detail)
        btn_layout.addWidget(self._detail_btn)
        layout.addLayout(btn_layout, 5, 0, 1, 9)

        self._gas_a_combo.currentIndexChanged.connect(self._on_any_change)
        self._gas_b_combo.currentIndexChanged.connect(self._on_any_change)
        self._unit_a_combo.currentIndexChanged.connect(self._on_any_change)
        self._unit_b_combo.currentIndexChanged.connect(self._on_any_change)
        self._value_a_input.valueChanged.connect(self._on_value_changed)
        self._value_b_input.valueChanged.connect(self._on_value_changed)
        self._swap_btn.clicked.connect(self._swap)
        self._temp_a_spin.valueChanged.connect(self._on_any_change)
        self._press_a_spin.valueChanged.connect(self._on_any_change)
        self._press_a_combo.currentIndexChanged.connect(self._on_any_change)
        self._temp_b_spin.valueChanged.connect(self._on_any_change)
        self._press_b_spin.valueChanged.connect(self._on_any_change)
        self._press_b_combo.currentIndexChanged.connect(self._on_any_change)

        self._updating = False

    @staticmethod
    def _make_t_spin() -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(-273.0, 2000.0)
        s.setDecimals(1)
        s.setValue(25.0)
        s.setSuffix(' \u00b0C')
        s.setSingleStep(10.0)
        s.setFixedWidth(90)
        return s

    @staticmethod
    def _make_press_pair():
        s = QDoubleSpinBox()
        s.setRange(0.001, 10000000.0)
        s.setDecimals(4)
        s.setValue(1.0)
        s.setSingleStep(1.0)
        s.setFixedWidth(90)
        c = QComboBox()
        for k in PRESSURE_UNITS:
            c.addItem(PRESSURE_LABELS[k], k)
        c.setCurrentIndex(c.findData('Pa'))
        c.setFixedWidth(75)
        return s, c

    def _init_unit_combos(self):
        for combo in [self._unit_a_combo, self._unit_b_combo]:
            for k in VOLUMETRIC_UNITS:
                combo.addItem(VOLUMETRIC_LABELS[k], f'volumetric:{k}')
            for k in MASS_UNITS:
                combo.addItem(MASS_LABELS[k], f'mass:{k}')
            for k in MOLAR_UNITS:
                combo.addItem(MOLAR_LABELS[k], f'molar:{k}')
        self._unit_a_combo.setCurrentIndex(
            self._unit_a_combo.findData('mass:g/min')
        )
        self._unit_b_combo.setCurrentIndex(
            self._unit_b_combo.findData('volumetric:L/min')
        )

    def get_gas_a_key(self) -> str:
        return self._gas_a_combo.currentData()

    def get_gas_b_key(self) -> str:
        return self._gas_b_combo.currentData()

    def get_unit_a_key(self) -> str:
        d = self._unit_a_combo.currentData()
        return d.split(':', 1)[1] if d else 'g/min'

    def get_unit_b_key(self) -> str:
        d = self._unit_b_combo.currentData()
        return d.split(':', 1)[1] if d else 'slm'

    def get_value_a(self) -> Optional[float]:
        return _parse(self._value_a_input.text())

    def get_value_b(self) -> Optional[float]:
        return _parse(self._value_b_input.text())

    def _show_detail(self):
        dlg = RatioCalcStepsDialog(self, self.window())
        dlg.exec()

    def _on_any_change(self):
        if self._updating:
            return
        if self.get_value_a() is not None and self.get_value_b() is not None:
            self._recalc()

    def _on_value_changed(self, *args):
        if self._updating:
            return
        va = self.get_value_a()
        vb = self.get_value_b()
        if va is not None and vb is not None:
            self._recalc()

    def _recalc(self):
        va = self.get_value_a()
        vb = self.get_value_b()
        if va is None or vb is None or va == 0:
            return
        temp_a_K = self._temp_a_spin.value() + 273.15
        press_a_Pa = _press_pa(self._press_a_spin, self._press_a_combo)
        temp_b_K = self._temp_b_spin.value() + 273.15
        press_b_Pa = _press_pa(self._press_b_spin, self._press_b_combo)
        mm_a = _get_mm(self.get_gas_a_key())
        mm_b = _get_mm(self.get_gas_b_key())
        try:
            mol_a = _to_molar(va, self.get_unit_a_key(), mm_a, temp_a_K, press_a_Pa)
            mol_b = _to_molar(vb, self.get_unit_b_key(), mm_b, temp_b_K, press_b_Pa)
            mass_a = molar_to_mass(mol_a, mm_a)
            mass_b = molar_to_mass(mol_b, mm_b)
            vol_a = molar_to_volumetric(mol_a, temp_a_K, press_a_Pa, False)
            vol_b = molar_to_volumetric(mol_b, temp_b_K, press_b_Pa, False)
        except Exception:
            return
        molar_r = mol_b / mol_a
        mass_r = mass_b / mass_a
        vol_r = vol_b / vol_a
        self._updating = True
        self._result_molar_b.setText(f'{molar_r:.4f}')
        self._result_mass_b.setText(f'{mass_r:.4f}')
        self._result_vol_b.setText(f'{vol_r:.4f}')
        self._updating = False

    def _swap(self):
        try:
            self._updating = True

            ga_idx = self._gas_a_combo.currentIndex()
            gb_idx = self._gas_b_combo.currentIndex()
            ua_idx = self._unit_a_combo.currentIndex()
            ub_idx = self._unit_b_combo.currentIndex()
            va = self._value_a_input._last_valid
            vb = self._value_b_input._last_valid
            ta = self._temp_a_spin.value()
            pa = self._press_a_spin.value()
            pau = self._press_a_combo.currentIndex()
            tb = self._temp_b_spin.value()
            pb = self._press_b_spin.value()
            pbu = self._press_b_combo.currentIndex()

            self._gas_a_combo.setCurrentIndex(gb_idx)
            self._gas_b_combo.setCurrentIndex(ga_idx)
            self._unit_a_combo.setCurrentIndex(ub_idx)
            self._unit_b_combo.setCurrentIndex(ua_idx)

            self._temp_a_spin.setValue(tb)
            self._press_a_spin.setValue(pb)
            self._press_a_combo.setCurrentIndex(pbu)
            self._temp_b_spin.setValue(ta)
            self._press_b_spin.setValue(pa)
            self._press_b_combo.setCurrentIndex(pau)

            self._value_a_input.clear_value()
            self._value_b_input.clear_value()
            if vb is not None:
                self._value_a_input.set_value(vb)
            if va is not None:
                self._value_b_input.set_value(va)

            self._updating = False
            self._on_value_changed()
        except Exception:
            self._updating = False


def _to_molar(value: float, unit_key: str, mm: float, temp_K: float, pressure_Pa: float) -> float:
    utype = get_unit_type(unit_key)
    base = to_base(value, unit_key, utype)
    if utype == 'volumetric':
        return volumetric_to_molar(base, temp_K, pressure_Pa, unit_key in STD_VOL_UNITS)
    elif utype == 'mass':
        return mass_to_molar(base, mm)
    return base


def _from_molar(mol: float, unit_key: str, mm: float,
                 temp_K: float, pressure_Pa: float) -> float:
    utype = get_unit_type(unit_key)
    if utype == 'volumetric':
        base = molar_to_volumetric(mol, temp_K, pressure_Pa, unit_key in STD_VOL_UNITS)
    elif utype == 'mass':
        base = molar_to_mass(mol, mm)
    else:
        base = mol
    return from_base(base, unit_key, utype)


def _convert_with_ratio(
    value_src: float, unit_src: str, mm_src: float,
    temp_src_K: float, press_src_Pa: float,
    unit_dst: str, mm_dst: float,
    temp_dst_K: float, press_dst_Pa: float,
    ratio_src: float, ratio_dst: float,
    mode: str,
) -> float:
    mol_src = _to_molar(value_src, unit_src, mm_src, temp_src_K, press_src_Pa)
    if mode == 'molar':
        target_src = mol_src
    elif mode == 'mass':
        target_src = molar_to_mass(mol_src, mm_src)
    elif mode == 'volumetric':
        target_src = molar_to_volumetric(mol_src, temp_src_K, press_src_Pa, False)
    else:
        raise ValueError(f'Unknown ratio mode: {mode}')
    target_dst = target_src * ratio_dst / ratio_src
    if mode == 'molar':
        mol_dst = target_dst
    elif mode == 'mass':
        mol_dst = mass_to_molar(target_dst, mm_dst)
    elif mode == 'volumetric':
        mol_dst = volumetric_to_molar(target_dst, temp_dst_K, press_dst_Pa, False)
    else:
        mol_dst = target_dst
    return _from_molar(mol_dst, unit_dst, mm_dst, temp_dst_K, press_dst_Pa)


def _press_pa(spin: QDoubleSpinBox, combo: QComboBox) -> float:
    return spin.value() * PRESSURE_UNITS[combo.currentData()]


def _gas_name(gas_key: str) -> str:
    app = QApplication.instance()
    db = app.property('gas_db')
    if db is None:
        return gas_key
    return db.display_name(gas_key) if hasattr(db, 'display_name') else gas_key


def _get_mm(gas_key: str) -> float:
    app = QApplication.instance()
    db = app.property('gas_db')
    if db is None:
        return 28.0134
    g = db.get(gas_key)
    return g.molar_mass if g else 28.0134


def _unit_label(key: str) -> str:
    for d in (VOLUMETRIC_LABELS, MASS_LABELS, MOLAR_LABELS):
        if key in d:
            return d[key]
    return key


class CalcStepsDialog(QDialog):
    STYLE = '''
    <style>
    body { font-family: "Microsoft YaHei", "Consolas", monospace; padding: 12px 16px; line-height: 1.6; }
    h2 { color: #1565C0; border-bottom: 2px solid #1565C0; padding-bottom: 4px; }
    h3 { color: #2E7D32; margin-top: 16px; margin-bottom: 4px; }
    h4 { color: #E65100; margin-top: 12px; margin-bottom: 2px; }
    .formula { background: #f5f5f5; padding: 6px 10px; border-radius: 4px; font-family: "Consolas", monospace; margin: 4px 0; }
    .result { color: #1565C0; font-weight: bold; }
    .note { background: #fff3e0; padding: 4px 8px; border-left: 3px solid #ff9800; margin: 6px 0; font-size: 13px; }
    table { border-collapse: collapse; margin: 6px 0; }
    td { border: 1px solid #ccc; padding: 3px 10px; }
    td:first-child { background: #f5f5f5; font-weight: bold; white-space: nowrap; }
    </style>
    '''

    def __init__(self, converter, source_unit: str, source_value: Optional[float], parent=None):
        super().__init__(parent)
        self.setWindowTitle('\u8ba1\u7b97\u8be6\u60c5')
        self.setMinimumSize(560, 520)
        self.resize(620, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(self.STYLE + self._build_html(converter, source_unit, source_value))
        layout.addWidget(browser)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cb = QPushButton('\u5173\u95ed')
        cb.clicked.connect(self.accept)
        btn_row.addWidget(cb)
        btn_row.setContentsMargins(12, 4, 12, 0)
        layout.addLayout(btn_row)

    def _build_html(self, cvt, src_unit: str, src_val: Optional[float]) -> str:
        lines = []
        mm = cvt.molar_mass
        gas_key = cvt.gas_key
        db = cvt.gas_db
        gas_name = db.display_name(gas_key) if hasattr(db, 'display_name') else gas_key
        temp_C = cvt.temp_C
        temp_K = cvt.temp_K
        press_Pa = cvt.pressure_Pa
        press_atm = cvt.pressure_atm
        mol_s = cvt._molar_flow_mol_s

        lines.append('<h2>\u8ba1\u7b97\u8be6\u60c5</h2>')

        lines.append('<h3>\u8f93\u5165\u53c2\u6570</h3>')
        lines.append(f'<table>')
        if src_val is not None:
            lines.append(f'<tr><td>\u6e90\u503c</td><td>{_fmt(src_val)} {_unit_label(src_unit)}</td></tr>')
        lines.append(f'<tr><td>\u6c14\u4f53</td><td>{gas_name} (M = {mm} g/mol)</td></tr>')
        lines.append(f'<tr><td>\u5de5\u827a\u6e29\u5ea6</td><td>{temp_C:.1f} \u00b0C ({temp_K:.2f} K)</td></tr>')
        lines.append(f'<tr><td>\u5de5\u827a\u538b\u529b</td><td>{press_Pa:.4f} Pa ({press_atm:.6f} atm)</td></tr>')
        lines.append(f'<tr><td>\u6469\u5c14\u6d41\u91cf</td><td>{_fmt(mol_s)} mol/s</td></tr>')
        lines.append(f'</table>')

        if src_val is None or src_unit is None:
            lines.append('<div class="note">\u672a\u68c0\u6d4b\u5230\u8f93\u5165\u6e90\u503c\uff0c\u4ee5\u4e0b\u4e3a\u5f53\u524d\u72b6\u6001\u7684\u6362\u7b97\u7ed3\u679c\u3002</div>')
        else:
            utype = get_unit_type(src_unit)
            base = to_base(src_val, src_unit, utype)
            base_unit = {'volumetric': 'm\u00b3/s', 'mass': 'kg/s', 'molar': 'mol/s'}[utype]

            lines.append(f'<h3>\u6b65\u9aa41: \u8f6c\u6362\u4e3a\u57fa\u51c6\u5355\u4f4d</h3>')
            if base != 0:
                factor = src_val / base
                lines.append(f'<div class="formula">{_fmt(src_val)} {_unit_label(src_unit)} \u00f7 {_fmt(factor)} = {_fmt(base)} {base_unit}</div>')
            else:
                lines.append(f'<div class="formula">{_fmt(src_val)} {_unit_label(src_unit)} = {_fmt(base)} {base_unit}</div>')

            lines.append(f'<h3>\u6b65\u9aa42: \u8f6c\u6362\u4e3a\u6469\u5c14\u6d41\u91cf (mol/s)</h3>')
            if utype == 'volumetric':
                is_std = src_unit in STD_VOL_UNITS
                if is_std:
                    t_used, p_used = STD_T_K, STD_P_PA
                    lines.append(f'<div class="note">{_unit_label(src_unit)} \u662f\u6807\u51c6\u4f53\u79ef\u6d41\u91cf\uff0c\u59cb\u7ec8\u4f7f\u7528 STP (0\u00b0C, 1 atm)</div>')
                else:
                    t_used, p_used = temp_K, press_Pa
                    lines.append(f'<div class="note">{_unit_label(src_unit)} \u662f\u5b9e\u9645\u4f53\u79ef\u6d41\u91cf\uff0c\u4f7f\u7528\u5de5\u827a\u6e29\u538b</div>')
                lines.append(f'<div class="formula">n = PV / (RT)</div>')
                lines.append(f'<div class="formula">= {_fmt(p_used)} \u00d7 {_fmt(base)} / ({_fmt(R, 10)} \u00d7 {_fmt(t_used)})</div>')
                lines.append(f'<div class="formula">= <span class="result">{_fmt(mol_s)} mol/s</span></div>')
            elif utype == 'mass':
                lines.append(f'<div class="formula">n = m / M</div>')
                lines.append(f'<div class="formula">= {_fmt(base)} / ({_fmt(mm / 1000.0)})</div>')
                lines.append(f'<div class="formula">= <span class="result">{_fmt(mol_s)} mol/s</span></div>')
            else:
                lines.append(f'<div class="formula">\u76f4\u63a5\u8f93\u5165\u6469\u5c14\u6d41\u91cf: {_fmt(mol_s)} mol/s</div>')

        lines.append(f'<h3>\u6b65\u9aa43: \u4ece\u6469\u5c14\u6d41\u91cf\u6362\u7b97\u5230\u5404\u7ec4\u5355\u4f4d</h3>')

        lines.append(f'<h4>\u4f53\u79ef\u6d41\u91cf</h4>')
        lines.append('<table>')
        for k in VOLUMETRIC_UNITS:
            label = VOLUMETRIC_LABELS.get(k, k)
            val = cvt.get_volumetric(k)
            tag = '\u2713 STP' if k in STD_VOL_UNITS else '\u5de5\u827a\u6e29\u538b'
            lines.append(f'<tr><td>{label}</td><td>{_fmt(val)}</td><td style="font-size:12px;color:#666;">({tag})</td></tr>')
        lines.append('</table>')

        lines.append(f'<h4>\u8d28\u91cf\u6d41\u91cf</h4>')
        lines.append(f'<div class="formula">m = n \u00d7 M = {_fmt(mol_s)} \u00d7 {_fmt(mm / 1000.0)} = {_fmt(mol_s * mm / 1000.0)} kg/s</div>')
        lines.append('<table>')
        for k in MASS_UNITS:
            label = MASS_LABELS.get(k, k)
            val = cvt.get_mass(k)
            lines.append(f'<tr><td>{label}</td><td>{_fmt(val)}</td></tr>')
        lines.append('</table>')

        lines.append(f'<h4>\u6469\u5c14\u6d41\u91cf</h4>')
        lines.append('<table>')
        for k in MOLAR_UNITS:
            label = MOLAR_LABELS.get(k, k)
            val = cvt.get_molar(k)
            lines.append(f'<tr><td>{label}</td><td>{_fmt(val)}</td></tr>')
        lines.append('</table>')

        return '\n'.join(lines)


class RatioCalcStepsDialog(QDialog):
    STYLE = CalcStepsDialog.STYLE

    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self.setWindowTitle('\u6d41\u91cf\u6bd4\u4f8b\u8ba1\u7b97\u8be6\u60c5')
        self.setMinimumSize(560, 480)
        self.resize(620, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(self.STYLE + self._build_html(panel))
        layout.addWidget(browser)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cb = QPushButton('\u5173\u95ed')
        cb.clicked.connect(self.accept)
        btn_row.addWidget(cb)
        btn_row.setContentsMargins(12, 4, 12, 0)
        layout.addLayout(btn_row)

    @staticmethod
    def _build_html(p) -> str:
        lines = []

        va = p.get_value_a()
        vb = p.get_value_b()
        if va is None or vb is None:
            return '<h2>\u6d41\u91cf\u6bd4\u4f8b\u8ba1\u7b97\u8be6\u60c5</h2><p>\u8bf7\u5148\u8f93\u5165\u4e24\u79cd\u6c14\u4f53\u7684\u6d41\u91cf\u503c\u3002</p>'

        ga_key = p.get_gas_a_key()
        gb_key = p.get_gas_b_key()
        ua_key = p.get_unit_a_key()
        ub_key = p.get_unit_b_key()
        mm_a = _get_mm(ga_key)
        mm_b = _get_mm(gb_key)
        t_aK = p._temp_a_spin.value() + 273.15
        p_aPa = _press_pa(p._press_a_spin, p._press_a_combo)
        t_bK = p._temp_b_spin.value() + 273.15
        p_bPa = _press_pa(p._press_b_spin, p._press_b_combo)

        mol_a = _to_molar(va, ua_key, mm_a, t_aK, p_aPa)
        mol_b = _to_molar(vb, ub_key, mm_b, t_bK, p_bPa)
        mass_a = molar_to_mass(mol_a, mm_a)
        mass_b = molar_to_mass(mol_b, mm_b)
        vol_a = molar_to_volumetric(mol_a, t_aK, p_aPa, False)
        vol_b = molar_to_volumetric(mol_b, t_bK, p_bPa, False)

        molar_r = mol_b / mol_a
        mass_r = mass_b / mass_a
        vol_r = vol_b / vol_a

        lines.append('<h2>\u6d41\u91cf\u6bd4\u4f8b\u8ba1\u7b97\u8be6\u60c5</h2>')

        lines.append('<h3>\u8f93\u5165\u53c2\u6570</h3>')
        lines.append('<table>')
        lines.append(f'<tr><td>\u6c14\u4f53A</td><td>{_gas_name(ga_key)}</td><td>{_fmt(va)} {_unit_label(ua_key)}</td></tr>')
        lines.append(f'<tr><td>\u6c14\u4f53B</td><td>{_gas_name(gb_key)}</td><td>{_fmt(vb)} {_unit_label(ub_key)}</td></tr>')
        lines.append(f'<tr><td>A \u6e29\u5ea6</td><td colspan="2">{p._temp_a_spin.value():.1f} \u00b0C ({t_aK:.2f} K)</td></tr>')
        lines.append(f'<tr><td>A \u538b\u529b</td><td colspan="2">{_fmt(p_aPa)} Pa</td></tr>')
        lines.append(f'<tr><td>B \u6e29\u5ea6</td><td colspan="2">{p._temp_b_spin.value():.1f} \u00b0C ({t_bK:.2f} K)</td></tr>')
        lines.append(f'<tr><td>B \u538b\u529b</td><td colspan="2">{_fmt(p_bPa)} Pa</td></tr>')
        lines.append(f'<tr><td>A \u6469\u5c14\u8d28\u91cf</td><td colspan="2">{mm_a} g/mol</td></tr>')
        lines.append(f'<tr><td>B \u6469\u5c14\u8d28\u91cf</td><td colspan="2">{mm_b} g/mol</td></tr>')
        lines.append('</table>')

        lines.append('<h3>\u6b65\u9aa41: \u6c14\u4f53A \u2192 \u6469\u5c14\u6d41\u91cf</h3>')
        lines.append(f'<div class="formula">{_fmt(mol_a)} mol/s</div>')

        lines.append('<h3>\u6b65\u9aa42: \u6c14\u4f53B \u2192 \u6469\u5c14\u6d41\u91cf</h3>')
        lines.append(f'<div class="formula">{_fmt(mol_b)} mol/s</div>')

        lines.append('<h3>\u6b65\u9aa43: \u8ba1\u7b97\u5404\u7c7b\u6bd4\u503c (A = 1)</h3>')
        lines.append(f'<div class="formula"><b>\u6469\u5c14\u6bd4</b>  1 : {molar_r:.4f}</div>')
        lines.append(f'<div class="formula"><b>\u8d28\u91cf\u6bd4</b>  1 : {mass_r:.4f}</div>')
        lines.append(f'<div class="formula"><b>\u4f53\u79ef\u6bd4</b>  1 : {vol_r:.4f}</div>')

        lines.append('<div class="note">\u6469\u5c14\u6bd4 = n<sub>B</sub> / n<sub>A</sub><br>'
                     '\u8d28\u91cf\u6bd4 = m<sub>B</sub> / m<sub>A</sub><br>'
                     '\u4f53\u79ef\u6bd4 = V<sub>B</sub> / V<sub>A</sub> (\u5b9e\u9645\u4f53\u79ef)</div>')

        return '\n'.join(lines)


class FlowFromRatioStepsDialog(QDialog):
    STYLE = CalcStepsDialog.STYLE

    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self.setWindowTitle('\u5df2\u77e5\u6d41\u91cf\u4e0e\u6bd4\u4f8b\u8ba1\u7b97\u8be6\u60c5')
        self.setMinimumSize(560, 500)
        self.resize(620, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(self.STYLE + self._build_html(panel))
        layout.addWidget(browser)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cb = QPushButton('\u5173\u95ed')
        cb.clicked.connect(self.accept)
        btn_row.addWidget(cb)
        btn_row.setContentsMargins(12, 4, 12, 0)
        layout.addLayout(btn_row)

    @staticmethod
    def _build_html(p) -> str:
        lines = []

        mode_names = ['\u6469\u5c14\u6bd4', '\u8d28\u91cf\u6bd4', '\u4f53\u79ef\u6bd4']
        mode = mode_names[p._mode_group.checkedId()]

        va = p.get_value_a()
        if va is None:
            return '<h2>\u5df2\u77e5\u6d41\u91cf\u4e0e\u6bd4\u4f8b\u8ba1\u7b97\u8be6\u60c5</h2><p>\u8bf7\u5148\u8f93\u5165\u6c14\u4f53A\u7684\u6d41\u91cf\u503c\u3002</p>'

        ga_key = p.get_gas_a_key()
        gb_key = p.get_gas_b_key()
        ua_key = p.get_unit_a_key()
        ub_key = p.get_unit_b_key()
        mm_a = _get_mm(ga_key)
        mm_b = _get_mm(gb_key)
        t_aK = p._temp_a_spin.value() + 273.15
        p_aPa = _press_pa(p._press_a_spin, p._press_a_combo)
        t_bK = p._temp_b_spin.value() + 273.15
        p_bPa = _press_pa(p._press_b_spin, p._press_b_combo)
        ratio_a = p.get_ratio_a()
        ratio_b = p.get_ratio_b()

        lines.append('<h2>\u5df2\u77e5\u6d41\u91cf\u4e0e\u6bd4\u4f8b\u8ba1\u7b97\u8be6\u60c5</h2>')

        lines.append('<h3>\u8f93\u5165\u53c2\u6570</h3>')
        lines.append('<table>')
        lines.append(f'<tr><td>\u6a21\u5f0f</td><td>{mode}</td></tr>')
        lines.append(f'<tr><td>\u6c14\u4f53A</td><td>{_gas_name(ga_key)}</td><td>{_fmt(va)} {_unit_label(ua_key)}</td></tr>')
        lines.append(f'<tr><td>\u6c14\u4f53B</td><td>{_gas_name(gb_key)}</td><td>{_unit_label(ub_key)}</td></tr>')
        lines.append(f'<tr><td>A \u6e29\u5ea6</td><td colspan="2">{p._temp_a_spin.value():.1f} \u00b0C ({t_aK:.2f} K)</td></tr>')
        lines.append(f'<tr><td>A \u538b\u529b</td><td colspan="2">{_fmt(p_aPa)} Pa</td></tr>')
        lines.append(f'<tr><td>B \u6e29\u5ea6</td><td colspan="2">{p._temp_b_spin.value():.1f} \u00b0C ({t_bK:.2f} K)</td></tr>')
        lines.append(f'<tr><td>B \u538b\u529b</td><td colspan="2">{_fmt(p_bPa)} Pa</td></tr>')
        lines.append(f'<tr><td>\u6bd4\u4f8b A:B</td><td colspan="2">{_fmt(ratio_a)} : {_fmt(ratio_b)}</td></tr>')
        lines.append(f'<tr><td>A \u6469\u5c14\u8d28\u91cf</td><td colspan="2">{mm_a} g/mol</td></tr>')
        lines.append(f'<tr><td>B \u6469\u5c14\u8d28\u91cf</td><td colspan="2">{mm_b} g/mol</td></tr>')
        lines.append('</table>')

        lines.append('<h3>\u6b65\u9aa41: \u6c14\u4f53A \u2192 \u76ee\u6807\u91cf</h3>')
        mol_a = _to_molar(va, ua_key, mm_a, t_aK, p_aPa)
        if p._mode_group.checkedId() == 0:
            target_a = mol_a
            target_unit = 'mol/s'
            lines.append(f'<div class="formula">\u8f6c\u6362\u4e3a\u6469\u5c14\u6d41\u91cf: {_fmt(mol_a)} mol/s</div>')
        elif p._mode_group.checkedId() == 1:
            target_a = molar_to_mass(mol_a, mm_a)
            target_unit = 'kg/s'
            lines.append(f'<div class="formula">\u8f6c\u6362\u4e3a\u8d28\u91cf\u6d41\u91cf: {_fmt(target_a)} kg/s</div>')
        else:
            target_a = molar_to_volumetric(mol_a, t_aK, p_aPa, False)
            target_unit = 'm\u00b3/s'
            lines.append(f'<div class="formula">\u8f6c\u6362\u4e3a\u5b9e\u9645\u4f53\u79ef\u6d41\u91cf: {_fmt(target_a)} m\u00b3/s</div>')

        lines.append(f'<h3>\u6b65\u9aa42: \u6309\u6bd4\u4f8b\u8ba1\u7b97\u6c14\u4f53B\u76ee\u6807\u91cf</h3>')
        target_b = target_a * ratio_b / ratio_a
        lines.append(f'<div class="formula">B = A \u00d7 ({_fmt(ratio_b)} / {_fmt(ratio_a)}) = {_fmt(target_b)} {target_unit}</div>')

        lines.append('<h3>\u6b65\u9aa43: \u6c14\u4f53B \u76ee\u6807\u91cf \u2192 \u663e\u793a\u5355\u4f4d</h3>')
        if p._mode_group.checkedId() == 0:
            mol_b = target_b
        elif p._mode_group.checkedId() == 1:
            mol_b = mass_to_molar(target_b, mm_b)
        else:
            mol_b = volumetric_to_molar(target_b, t_bK, p_bPa, False)

        vb_result = _from_molar(mol_b, ub_key, mm_b, t_bK, p_bPa)
        lines.append(f'<div class="formula"><span class="result">{_fmt(vb_result)} {_unit_label(ub_key)}</span></div>')

        return '\n'.join(lines)


GUIDE_HTML = '''
<style>
body { font-family: "Microsoft YaHei", "Segoe UI", sans-serif; padding: 16px 20px; line-height: 1.7; }
h2 { color: #1565C0; border-bottom: 2px solid #1565C0; padding-bottom: 4px; margin-top: 24px; }
h3 { color: #2E7D32; margin-top: 18px; }
table { border-collapse: collapse; margin: 10px 0; }
td, th { border: 1px solid #ccc; padding: 5px 10px; text-align: center; }
th { background: #e3f2fd; }
code { background: #f5f5f5; padding: 1px 5px; border-radius: 3px; font-family: "Consolas", monospace; }
.note { background: #fff3e0; padding: 8px 12px; border-left: 4px solid #ff9800; margin: 10px 0; }
</style>

<h2>\u4e00\u3001\u6e29\u5ea6\u4e0e\u538b\u529b</h2>
<p>\u7528\u6237\u5728\u5de5\u827a\u6761\u4ef6\u9762\u677f\u4e2d\u8bbe\u7f6e\u5de5\u827a\u6e29\u5ea6\u4e0e\u538b\u529b\uff0c
\u6240\u6709\u6d41\u91cf\u6362\u7b97\u57fa\u4e8e\u7406\u60f3\u6c14\u4f53\u72b6\u6001\u65b9\u7a0b\uff1a</p>
<p style="text-align:center; font-size:16px; margin:12px 0;">
  <b>PV = nRT</b>
</p>
<p>\u5176\u4e2d\uff1a</p>
<ul>
  <li><b>P</b> \u2014 \u538b\u529b (Pa)</li>
  <li><b>V</b> \u2014 \u4f53\u79ef (m\u00b3)</li>
  <li><b>n</b> \u2014 \u7269\u8d28\u7684\u91cf (mol)</li>
  <li><b>R</b> \u2014 \u7406\u60f3\u6c14\u4f53\u5e38\u6570 = 8.314462618 J/(mol\u00b7K)</li>
  <li><b>T</b> \u2014 \u70ed\u529b\u5b66\u6e29\u5ea6 (K)</li>
</ul>

<h2>\u4e8c\u3001\u6807\u51c6\u72b6\u6001 (\u56fa\u5b9a\u53c2\u6570)</h2>
<table>
<tr><th>\u53c2\u6570</th><th>\u503c</th><th>\u8bf4\u660e</th></tr>
<tr><td>\u6807\u51c6\u6e29\u5ea6 T\u2080</td><td>273.15 K (0\u00b0C)</td><td>SEMI \u6807\u51c6</td></tr>
<tr><td>\u6807\u51c6\u538b\u529b P\u2080</td><td>101325 Pa (1 atm)</td><td></td></tr>
<tr><td>\u7406\u60f3\u6c14\u4f53\u5e38\u6570 R</td><td>8.314462618 J/(mol\u00b7K)</td><td></td></tr>
</table>
<p>\u6ce8\u610f\uff1a<code>sccm</code>\u3001<code>slm</code>\u3001<code>scfh</code> \u5929\u751f\u5df2\u5e26\u201c\u6807\u51c6\u201d\u5c5e\u6027\uff0c\u8f6c\u6469\u5c14\u65f6\u59cb\u7ec8\u4f7f\u7528\u6807\u51c6\u72b6\u6001\uff0c
<b>\u4e0d\u53d7\u7528\u6237\u6e29\u538b\u5f71\u54cd</b>\u3002</p>

<h2>\u4e09\u3001\u6362\u7b97\u5f15\u64ce\u4e09\u5c42\u67b6\u6784</h2>

<h3>\u5c42 1 \u2014 \u540c\u7c7b\u5355\u4f4d\u4e92\u8f6c</h3>
<p>\u4ec5\u4f9d\u8d56\u56fa\u5b9a\u7cfb\u6570\uff0c\u5982 <code>1 sccm = 0.001 slm</code>\u3002
\u6240\u6709\u5355\u4f4d\u7684\u6362\u7b97\u7cfb\u6570\u5b9a\u4e49\u5728 <code>units.py</code> \u7684\u5b57\u5178\u4e2d\uff0c
\u57fa\u51c6\u5355\u4f4d\u4e3a m\u00b3/s\uff08\u4f53\u79ef\uff09\u3001kg/s\uff08\u8d28\u91cf\uff09\u3001mol/s\uff08\u6469\u5c14\uff09\u3002</p>

<h3>\u5c42 2 \u2014 \u6807\u51c6\u72b6\u6001 \u2194 \u5b9e\u9645\u72b6\u6001</h3>
<p>\u5bf9\u4e8e\u5b9e\u9645\u4f53\u79ef\u6d41\u91cf\u5355\u4f4d (L/min, mL/min, m\u00b3/h, CFM)\uff0c
\u8f6c\u6469\u5c14\u65f6\u4f7f\u7528\u7528\u6237\u8bbe\u7f6e\u7684\u5de5\u827a\u6e29\u538b\uff1a</p>
<p style="text-align:center"><b>n = P\u00b7V / (R\u00b7T)</b></p>
<p>\u5bf9\u4e8e\u6807\u51c6\u4f53\u79ef\u6d41\u91cf\u5355\u4f4d (sccm, slm, scfh)\uff0c
\u59cb\u7ec8\u4f7f\u7528\u56fa\u5b9a\u6807\u51c6\u72b6\u6001\uff1a</p>
<p style="text-align:center"><b>n = P\u2080\u00b7V / (R\u00b7T\u2080)</b></p>

<h3>\u5c42 3 \u2014 \u4f53\u79ef \u2194 \u8d28\u91cf \u2194 \u6469\u5c14 \u4e92\u8f6c</h3>
<p>\u8d28\u91cf\u6d41\u91cf\u4e0e\u6469\u5c14\u6d41\u91cf\u4e4b\u95f4\u7684\u8f6c\u6362\u4f9d\u8d56\u4e8e\u6c14\u4f53\u6469\u5c14\u8d28\u91cf <b>M</b>\uff1a</p>
<p style="text-align:center"><b>m = n \u00d7 M</b></p>
<p>\u5176\u4e2d <b>M</b> \u5355\u4f4d\u4e3a g/mol\uff0c\u5404\u6c14\u4f53\u7684\u6469\u5c14\u8d28\u91cf\u5b58\u50a8\u5728\u6c14\u4f53\u6570\u636e\u5e93\u4e2d\u3002
\u6362\u7b97\u65f6\u5fc5\u987b\u9009\u62e9\u6c14\u4f53\uff0c\u5426\u5219\u8d28\u91cf\u2194\u6469\u5c14\u8f6c\u6362\u65e0\u6cd5\u8fdb\u884c\u3002</p>

<div class="note">
<b>\u5355\u4f4d\u5206\u7c7b\u660e\u7ec6\uff1a</b><br>
\u2605 <b>\u6807\u51c6\u4f53\u79ef\u6d41\u91cf</b> (sccm / slm / scfh) \u2014 \u8f6c\u6469\u5c14\u65f6\u4f7f\u7528\u6807\u51c6\u6e29\u538b<br>
\u2605 <b>\u5b9e\u9645\u4f53\u79ef\u6d41\u91cf</b> (L/min / mL/min / m\u00b3/h / CFM) \u2014 \u8f6c\u6469\u5c14\u65f6\u4f7f\u7528\u7528\u6237\u6e29\u538b<br>
\u2605 <b>\u8d28\u91cf\u6d41\u91cf</b> (g/s / g/min / kg/h / lb/h) \u2014 \u8f6c\u6469\u5c14\u9700\u8981\u6c14\u4f53\u6469\u5c14\u8d28\u91cf<br>
\u2605 <b>\u6469\u5c14\u6d41\u91cf</b> (mol/s / mol/min / kmol/h) \u2014 \u5185\u90e8\u6838\u5fc3\u8868\u793a
</div>

<h2>\u56db\u3001\u6bd4\u4f8b\u8ba1\u7b97</h2>
<h3>\u6d41\u91cf\u6bd4\u4f8b\u6362\u7b97 (\u533a 2)</h3>
<p>\u8f93\u5165\u4e24\u79cd\u6c14\u4f53\u7684\u6d41\u91cf\uff0c\u7cfb\u7edf\u81ea\u52a8\u5c06\u4e24\u8005\u8f6c\u6362\u4e3a\u6469\u5c14\u6d41\u91cf\uff0c
\u5e76\u8ba1\u7b97\u6469\u5c14\u6bd4 <b>A : B</b>\uff0c\u5f52\u4e00\u5316\u4e3a A = 1\u3002</p>

<h3>\u5df2\u77e5\u6d41\u91cf\u4e0e\u6bd4\u4f8b\u6c42\u53e6\u4e00\u6d41\u91cf (\u533a 3)</h3>
<p>\u8f93\u5165\u6c14\u4f53 A \u7684\u6d41\u91cf\u548c\u6bd4\u4f8b <b>A : B</b>\uff0c\u7cfb\u7edf\u81ea\u52a8\u8ba1\u7b97\u6c14\u4f53 B \u7684\u6d41\u91cf\u3002
\u652f\u6301\u53cc\u5411\u8ba1\u7b97\uff1a\u7f16\u8f91 A \u5219\u81ea\u52a8\u7b97 B\uff0c\u7f16\u8f91 B \u5219\u53cd\u7b97 A\u3002</p>
<p>\u6bd4\u4f8b A:B \u59cb\u7ec8\u662f\u6469\u5c14\u6bd4\uff0c\u7b49\u4e8e\u6807\u51c6\u72b6\u6001\u4e0b\u7684\u4f53\u79ef\u6bd4\u3002
\u4f8b\u5982 MTS:H\u2082 = 1:10 \u8868\u793a 1 \u4efd\u6469\u5c14\u7684 MTS \u5bf9\u5e94 10 \u4efd\u6469\u5c14\u7684 H\u2082\u3002</p>

<h2>\u4e94\u3001\u6c14\u4f53\u6570\u636e\u5e93</h2>
<p>\u5e94\u7528\u5185\u7f6e 23 \u79cd\u5e38\u89c1 CVD \u6c14\u4f53\uff0c\u6bcf\u79cd\u6c14\u4f53\u5305\u542b\u6469\u5c14\u8d28\u91cf\uff08g/mol\uff09\u3002
\u6c14\u4f53\u6570\u636e\u5b9a\u4e49\u5728 <code>gas_db.py</code> \u4e2d\u3002\u9700\u8981\u6dfb\u52a0\u81ea\u5b9a\u4e49\u6c14\u4f53\u65f6\uff0c
\u53ef\u76f4\u63a5\u7f16\u8f91\u8be5\u6587\u4ef6\u7684 DEFAULT_GASES \u5b57\u5178\u3002</p>
'''


class FlowConvertWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('\u6d41\u91cf\u6362\u7b97')
        self.setFixedSize(700, 480)

        self._converter = FlowConverter()
        QApplication.instance().setProperty('converter', self._converter)
        QApplication.instance().setProperty('gas_db', self._converter.gas_db)

        tabs = QTabWidget()
        tabs.addTab(self._make_flow_tab(), '\u6d41\u91cf\u6362\u7b97')
        tabs.addTab(RatioCalcPanel(self._converter.gas_db.keys, self._converter.gas_db.display_name), '\u6d41\u91cf\u6bd4\u4f8b\u6362\u7b97')
        tabs.addTab(FlowFromRatioPanel(self._converter.gas_db.keys, self._converter.gas_db.display_name), '\u5df2\u77e5\u6d41\u91cf\u4e0e\u6bd4\u4f8b')
        tabs.addTab(self._make_guide_tab(), '\u8ba1\u7b97\u8bf4\u660e')
        self.setCentralWidget(tabs)

    def _make_flow_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        flow_group = QGroupBox()
        flow_layout = QVBoxLayout(flow_group)
        flow_layout.setSpacing(4)
        flow_layout.setContentsMargins(8, 12, 8, 8)

        self._condition = ConditionPanel(self._converter.gas_db.keys, self._converter.gas_db.display_name)
        flow_layout.addWidget(self._condition)

        self._vol_section = FlowSection('\u4f53\u79ef\u6d41\u91cf', VOLUMETRIC_UNITS, VOLUMETRIC_LABELS)
        flow_layout.addWidget(self._vol_section)

        self._mass_section = FlowSection('\u8d28\u91cf\u6d41\u91cf', MASS_UNITS, MASS_LABELS)
        flow_layout.addWidget(self._mass_section)

        self._molar_section = FlowSection('\u6469\u5c14\u6d41\u91cf', MOLAR_UNITS, MOLAR_LABELS)
        flow_layout.addWidget(self._molar_section)

        layout.addWidget(flow_group)

        self._last_source: Optional[str] = None
        self._last_source_value: Optional[float] = None
        self._block_recalc = False

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        self._detail_btn = QPushButton('\U0001F4CB \u67e5\u770b\u8ba1\u7b97\u6b65\u9aa4')
        self._detail_btn.setFixedHeight(28)
        self._detail_btn.setEnabled(False)
        self._detail_btn.clicked.connect(self._show_calc_steps)
        btn_row.addStretch()
        btn_row.addWidget(self._detail_btn)

        self._vol_section.connect_value_changed(self._on_flow_changed)
        self._mass_section.connect_value_changed(self._on_flow_changed)
        self._molar_section.connect_value_changed(self._on_flow_changed)

        self._condition.changed.connect(self._on_condition_changed)

        layout.addLayout(btn_row)

        return scroll

    def _make_guide_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(GUIDE_HTML)
        layout.addWidget(browser)
        return w

    def _on_flow_changed(self, val: float, unit_key: str):
        if self._block_recalc:
            return
        self._block_recalc = True
        try:
            self._converter.set_from(val, unit_key)
            self._last_source = unit_key
            self._last_source_value = val
            self._detail_btn.setEnabled(True)
            self._update_all_from_converter()
        except Exception:
            pass
        self._block_recalc = False

    def _show_calc_steps(self):
        dlg = CalcStepsDialog(self._converter, self._last_source, self._last_source_value, self)
        dlg.exec()

    def _on_condition_changed(self):
        if self._block_recalc:
            return
        try:
            self._converter.set_temperature(self._condition.temp_C)
            self._converter.set_pressure(self._condition.pressure_atm)
            self._converter.set_gas(self._condition.gas_key)
        except ValueError:
            pass
        self._block_recalc = True
        try:
            self._update_all_from_converter()
        except Exception:
            pass
        self._block_recalc = False

    def _update_all_from_converter(self):
        self._vol_section.block_signals(True)
        self._mass_section.block_signals(True)
        self._molar_section.block_signals(True)

        self._vol_section.set_values(self._converter.get_all_volumetric())
        self._mass_section.set_values(self._converter.get_all_mass())
        self._molar_section.set_values(self._converter.get_all_molar())

        self._vol_section.block_signals(False)
        self._mass_section.block_signals(False)
        self._molar_section.block_signals(False)
