# 数据清洗流水线（Python）

## 概述

本项目提供模块化的 Python 流水线，用于清洗金融类原始 CSV、按标准定义校验数据，并生成：

- 清洗后的 CSV，输出到 `output/`
- 每次运行一份 Excel 报告，输出到 `reports/`

可选：在主流水线之前单独运行 **预清洗 audit**，扫描 `raw/`，在 `audit/output/` 下写入一份 Excel；详见本仓库中的 `audit/README_AUDIT_CN.md`（中文说明，自用）。

流水线支持：

- **批量模式**：处理 `raw/` 下文件及 **一层子目录**（`raw/*.csv` 与 `raw/*/*.csv`）。
- **单文件调试**：路径相对于 `--base-dir`，且必须在 `raw/` 下。
- **标准文件自动生成 YAML 规则**。

---

## 项目结构

```text
data_clean/
├─ raw/                 # 原始输入文件
├─ standards/           # 标准定义 CSV
├─ config/
│  └─ file_rules.yaml   # 运行时规则（映射、类型、格式、读入选项）
├─ output/              # 清洗后 CSV
├─ reports/             # Excel 运行报告
├─ audit/               # 预清洗 audit 代码；报告在 audit/output/
├─ logs/                # 流水线日志
├─ src/                 # Python 源码
├─ docs/                # 各脚本说明文档
└─ requirements.txt
```

---

## 环境要求

- Python `3.10+`
- 安装依赖：

```bash
pip install -r requirements.txt
```

---

## 标准规则如何工作

`standards/` 下的标准文件应为 CSV：

- 第 1 行：列名  
- 第 2 行：样本值（用于推断类型与日期格式）

规则配置保存在 `config/file_rules.yaml`。

- 若不存在 `file_rules.yaml`，流水线会从 `standards/` **自动生成**。
- 若已存在 `file_rules.yaml`，流水线**直接使用**。

**日期列：** 在标准第 2 行放代表性样本，并在 YAML 中为每列设置 `date_format`（例如 `'%Y-%m-%d'` 或 `'%m/%d/%Y'`）。原始数据仍可为其它常见写法；解析时先按 YAML 格式再推断。**输出 CSV** 中每个日期/时间列按**该列规则里的 `date_format`** 写入。若日期列未配置 `date_format`，写出时默认使用 **`%Y-%m-%d`**。

---

## 预清洗 audit（可选）

在主流水线之前运行，用于标记结构问题、严格日期解析失败、可疑数值单元格、文件尾部 phantom 行、合计类关键字行等。需要已存在 `config/file_rules.yaml`。

```bash
python -m audit.main --base-dir .
```

CLI、`--file`、`--max-data-rows` 及报表阅读说明见 `audit/README_AUDIT_CN.md`。

---

## 如何运行

### 1）批量模式

处理 `raw/` 下符合条件的文件（根目录一层 + 一级子目录）：

```bash
python -m src.main --base-dir .
```

清洗结果 **镜像** `raw/` 目录结构，例如 `raw/teamA/foo.csv` → `output/teamA/foo.csv`。

说明：流水线会 **跳过** `raw/_audit_fixtures/` 下的 audit 回归夹具。  
说明：`.xlsx` 一律记为 `skipped_xlsx`（流水线不处理 Excel）。

### 2）单文件调试

路径相对于 `--base-dir`，且必须在 `raw/` 下：

```bash
python -m src.main --base-dir . --file raw/BA_CVA_ALLOCATION_20241031_20250527.csv
```

### 3）仅更新 `config/file_rules.yaml`（单独运行 `src/reader.py`）

在不跑完整清洗的情况下，根据 `standards/` 重新生成/合并 YAML：

```bash
python -m src.reader --base-dir .
```

若 **`config/file_rules.yaml` 已存在**，默认会 **merge** 到新内容：

- 保留 `mappings` 与 `raw_prefix_to_standard`
- 保留 `header_match_threshold`，并将 `defaults` 与 CLI 参数合并
- 对已仍存在 standard 文件的条目，合并额外 `aliases` 及每条规则的 `read`

需要完全重来时使用 `--no-merge`（会丢掉手工 `mappings`/前缀等，需自行再加）：

```bash
python -m src.reader --base-dir . --no-merge
```

可选参数示例：

```bash
python -m src.reader --base-dir . --standards-dir ./standards --output-yaml ./config/file_rules.yaml --encoding utf-8 --delimiter "," --skiprows 0
```

---

## 流水线对每个文件做什么

1. 跳过 `.xlsx`，标记为 `skipped_xlsx`
2. 将 raw 文件匹配到标准规则
3. 用匹配比例阈值检测表头行（默认 `0.6`）
4. 清洗单元格（去空白、空值归一、货币/引号、数值归一）
5. 仅删除**整行全空**的行（表头中出现的列即使清洗后全空也保留）
6. 将表头列名与标准列对比：
   - 额外列保留在输出中（并在报告中记为 `extra_columns`）
   - `missing_columns` 仅当 YAML 标准列名在 raw 表头中不存在时报告（不会输出从未出现在 raw 表头中的列）
7. 按 YAML 规则做类型转换
8. 以原始文件名为名保存清洗后 CSV
9. 在 Excel 报告中写入汇总与列统计

---

## 状态含义

- `success`：处理成功（允许缺列/多列）
- `warning`：处理完成但有类型转换问题
- `failed`：无法恢复的错误（例如无匹配规则或找不到表头）
- `skipped_xlsx`：按设计跳过

---

## 报告输出

每次运行生成：

- `reports/report_YYYYMMDD_HHMMSS.xlsx`

工作表：

- `file_summary`：每个文件一行（含 `raw_subfolder`：`raw/` 正下方文件夹名，根目录文件为空）
- `column_stats`：按文件、按列统计空值与转换问题（同样含 `raw_subfolder`，便于区分不同子目录下同文件名）

---

## 协作上手：通常要改哪里

若在新环境或接入新文件，重点看：

### 1）`config/file_rules.yaml`（最重要）

按需更新：

- `defaults`：`encoding`、`delimiter`、`skiprows`（上游有固定前置行时）
- `header_match_threshold`（默认 `0.6`）
- `mappings`  
  - 将 **raw 文件名** 映射到 **标准文件名**（例如 `foo.csv: MyStandard_r20260217.csv`）  
  - 可选：将 **`raw/` 下路径**（正斜杠）映射到标准，避免不同子目录同名冲突（例如 `teamA/foo.csv: ...`）；路径匹配优先于仅文件名
- `raw_prefix_to_standard`（可选）  
  - raw **文件名前缀** → `rules` 下的标准键（例如 `DESK_STANDALONE_RWA_: Desk_RWA_r20260205.csv`），日期后缀变化时不必逐文件列举
- `rules`  
  - 每个标准文件的列：`name`、`type`（`int`/`float`/`date`/`string`）、日期列的 `date_format`

### 2）`standards/`

- 新数据域出现时增删改标准 CSV。
- 保持「第 1 行列名、第 2 行样例」格式一致。

### 3）`raw/`

- 运行前把原始文件放在此处。
- `.xlsx` 会跳过，需要时请手工转为 CSV。
- `raw/_audit_fixtures/` 保留给 audit 回归夹具（流水线会跳过该文件夹）。
- `raw/pipeline_tests/` 可放用于主流程回归的合成 CSV（见下文）。

### 4）可选：修改 `src/` 下代码

仅在业务规则变化时需要：

- `src/cleaner.py`：单元格清洗
- `src/header_detector.py`：表头检测策略
- `src/validator.py`：类型转换
- `src/file_matcher.py`、`src/utils.py`：文件名归一化与匹配

---

## 团队使用清单

运行前：

1. 确认 Python 与依赖已安装。
2. 确认 `standards/` 中有标准 CSV。
3. 检查 `config/file_rules.yaml` 中的编码、分隔符、映射是否与本地一致。
4. 将 raw 放入 `raw/`。
5. （可选）先运行 `python -m audit.main --base-dir .`，查看 `audit/output/audit_*.xlsx`，再跑完整清洗。

运行后：

1. 先看 `reports/report_*.xlsx`。
2. 查看 `failed` 与 `warning` 行。
3. 对照查看 `output/` 中清洗结果。

---

## 主流水线回归夹具

生成覆盖常见流水线状态（success/warning/failed/skipped_xlsx）的合成 raw 文件：

```bash
python tools/generate_pipeline_fixtures.py
```

文件写入 `raw/pipeline_tests/`（与仅用于 audit 的 `raw/_audit_fixtures/` 不同）。

`Test_Wide_multi_*.csv` 使用合成的 10 列标准 `Test_Wide_Audit_r20260510.csv`，以便在默认 `header_match_threshold` 下仍能出现 **多个** 缺列/多列（仅 4 列的标准无法在 0.6 阈值下同时「缺两列」仍匹配表头）。

---

## 脚本文档

各脚本详细说明见 `docs/`：

- `docs/main.md`
- `docs/reader.md`
- `docs/file_matcher.md`
- `docs/header_detector.md`
- `docs/cleaner.md`
- `docs/validator.md`
- `docs/exporter.md`
- `docs/utils.md`
- `docs/types.md`

索引说明见 `docs/README_CN.md`。
