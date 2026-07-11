# AGENTS.md

CVD 流量换算桌面工具（Python + PySide6）。支持体积流量（sccm/slm/L/min 等）、质量流量、摩尔流量三类互转，含温度/压力修正和流量比例计算。

## 快速命令

```powershell
pip install -r requirements.txt        # 装依赖（pyside6, pyinstaller）
python main.py                         # 运行
python build_exe.py                    # 打包成单文件 exe -> dist/FlowConvert.exe
```

## 项目结构

```
flow-converter/
├── app/
│   ├── units.py       # 单位定义 + 换算系数
│   ├── gas_db.py      # 气体属性库（25 种常见 CVD 气体，含摩尔质量）
│   ├── converter.py   # 换算引擎（三层：系数层 / 状态修正层 / 无量纲转换层）
│   └── gui.py         # 主窗口 UI（条件面板 + 三流量区 + 比例计算区）
├── main.py            # 入口
├── build_exe.py       # PyInstaller 打包
└── requirements.txt
```

## 换算引擎架构（converter.py）

- **层1** — 同类单位互转：纯系数（定义在 units.py 的 *`_UNITS` dict）
- **层2** — 标准↔实际状态修正：`PV = nRT`，标准状态固定 0°C / 1 atm
- **层3** — 体积↔质量↔摩尔互转：`n = PV/RT` + `m = n×M`

关键约定：
- `sccm` / `slm` / `scfh` 是**标准体积流量**单位，转摩尔时始终使用 STP，不受用户温压影响
- `L/min` / `mL/min` / `m³/h` / `CFM` 是**实际体积流量**单位，转摩尔时使用用户设置的工艺温压
- 质量↔摩尔转换依赖气体摩尔质量，必须选择气体

## 三大功能区（gui.py）

| # | 区域 | 类 | 行为 |
|---|------|-----|------|
| 1 | 气体流量换算 | `FlowSection` × 3 | 输入任意单位值 → 全部单位自动更新；T/P/气体变化时重算 |
| 2 | 流量比例换算 | `RatioCalcPanel` | 输入两种气体流量 → 自动计算并显示摩尔比 A:B（归一化为 A=1） |
| 3 | 已知流量与比例求另一流量 | `FlowFromRatioPanel` | 输入气体 A 值 + 比例 A:B → 自动算出气体 B；编辑 B 反算 A |

比例 A:B 始终是**摩尔比**（等于标准体积比）。`Swap` 按钮可交换 A↔B。

## Unit Tests

项目无正式测试框架。验算用 Python inline test：

```powershell
python -c "from app.converter import FlowConverter; c=FlowConverter(); ..."
```

关键验算点：sccm 与温度无关、L/min 随温度变化、g↔mol↔sccm 往返误差 < 1e-4、比例正算/反算往返一致。
