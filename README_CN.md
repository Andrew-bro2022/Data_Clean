# 数据清洗流水线（Python）

## 概述

本项目提供模块化的 Python 流水线，用于清洗金融类原始 CSV、按标准定义校验数据，并生成：

- 清洗后的 CSV，输出到 `output/`
- 每次运行一份 Excel 报告，输出到 `reports/`

可选：在主流水线之前单独运行 **预清洗 audit**，扫描 `raw/`，在 `audit/output/` 下写入一份 Excel；详见本仓库中的 `audit/README_AUDIT_CN.md`（中文说明，自用）。

**清洗行为**（何时 fail/warn、行过滤、值规则）见 **[README_DATA_CLEAN_POLICY_CN.md](README_DATA_CLEAN_POLICY_CN.md)**。YAML 只定义 schema（`type`、`date_format`、映射），**不包含** clean policy。英文版：[README_DATA_CLEAN_POLICY.md](README_DATA_CLEAN_POLICY.md)。

同事上手流程见 **[docs/clean_pipeline.md](docs/clean_pipeline.md)**（英文）。  
**推荐批次流程 audit → clean：** **[docs/audit_clean_workflow.md](docs/audit_clean_workflow.md)**（英文）。

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

新批次建议在清洗前运行。完整步骤见 **[docs/audit_clean_workflow.md](docs/audit_clean_workflow.md)**（英文）。

```bash
python -m audit.main --base-dir .
```

报告路径：`audit/output/audit_YYYYMMDD_HHMMSS.xlsx`。CLI 与报表说明见 [audit/README_AUDIT_CN.md](audit/README_AUDIT_CN.md)。

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

完整政策见 [README_DATA_CLEAN_POLICY_CN.md](README_DATA_CLEAN_POLICY_CN.md)。摘要：

1. 跳过 `.xlsx` → `skipped_xlsx`；跳过 `raw/_audit_fixtures/`
2. 匹配 `file_rules.yaml` 标准规则
3. 读 CSV（编码回退；错位行 warn 并记录行号）
4. 检测表头行（默认阈值 `0.6`）
5. 表头重命名为标准列名；**重复映射到同一标准列 → fail**
6. **结构门控：** 相对 YAML **缺列或多列 → fail**；仅顺序不对 → 重排并 **warning**
7. 科学计数法 → **warning**（不阻断）
8. 删除尾部 phantom 行；合计类关键字行 **仅报告、不删除**
9. 单元格清洗（占位符、`$`、千分位、会计括号转负数等）
10. 类型转换（日期多格式解析后按 YAML `date_format` 写出；float 科学计数保留原文字）
11. 写入 `output/`（镜像 `raw/` 路径）并生成 Excel 报告

---

## 状态含义

- `success`：已写出 output，无 warning
- `warning`：已写出 output，需看 `status_reason` 与 `issues_detail`（如列重排、非 strict 日期、科学计数、类型转换、编码回退、错位 CSV 等）
- `failed`：**无 output**（无规则、找不到表头、结构/重复列门控失败、未处理异常）
- `skipped_xlsx`：不处理 Excel，请先转 CSV

`file_summary` 上还有 `layout_status`、`clean_status`、`output_written`。

---

## 报告输出

每次运行生成 `reports/report_YYYYMMDD_HHMMSS.xlsx`，含 **5 个工作表**：

| 工作表 | 内容 |
|--------|------|
| `file_summary` | 每文件一行：`status`、`output_written`、`layout_status`、`clean_status`、`status_reason` 等 |
| `issues_detail` | 按 `phase` / `category` 列出的问题与样例行号 |
| `clean_actions` | 文件级清洗计数 |
| `clean_actions_by_column` | 按列清洗计数 |
| `column_stats` | 每列空值、转换问题、科学计数、日期解析方式统计 |

详见 [docs/clean_pipeline.md](docs/clean_pipeline.md)。

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

完整 **audit → clean** 流程及对照表见 **[docs/audit_clean_workflow.md](docs/audit_clean_workflow.md)**。

运行前：

1. 确认 Python 与依赖已安装。
2. 确认 `standards/` 中有标准 CSV。
3. 检查 `config/file_rules.yaml` 中的编码、分隔符、映射是否与本地一致。
4. 将 raw 放入 `raw/`。
5. 运行 audit 并查看 `audit/output/audit_*.xlsx`（新批次建议执行）。

清洗后：

1. 查看 `reports/report_*.xlsx`。
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

- **[docs/audit_clean_workflow.md](docs/audit_clean_workflow.md)** — 推荐 audit → clean 批次流程（英文）
- **[README_DATA_CLEAN_POLICY_CN.md](README_DATA_CLEAN_POLICY_CN.md)** — 清洗政策（权威，不在 YAML 中）
- **[README_DATA_CLEAN_POLICY.md](README_DATA_CLEAN_POLICY.md)** — 英文版
- **[docs/clean_pipeline.md](docs/clean_pipeline.md)** — 同事用流程与读报告说明

`docs/` 下各模块说明：

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
