# 数据清洗政策

本文档是主流水线（`python -m src.main`）的**权威政策说明**。政策目前**在代码中实现**，**不**写在 `config/file_rules.yaml` 里。YAML 仅定义 schema（列名、`type`、`date_format`、读入选项、映射等）。

行为变更时，请同步更新本文档、对应代码与测试。

**相关文档：** [docs/clean_pipeline.md](docs/clean_pipeline.md)、[docs/audit_clean_workflow.md](docs/audit_clean_workflow.md)（audit → clean 批次流程）、[audit/README_AUDIT_CN.md](audit/README_AUDIT_CN.md)。英文版政策：[README_DATA_CLEAN_POLICY.md](README_DATA_CLEAN_POLICY.md)。

---

## 政策与配置的分工

| 层级 | 存放位置 | 控制内容 |
|------|----------|----------|
| **Schema** | `config/file_rules.yaml` | 列名、`type`、`date_format`、`read`、`mappings`、前缀 |
| **清洗政策** | 本文档 + `src/` | 如何清洗、何时 fail/warn、行过滤、报告语义 |

未来设想（**未实现**）：在 YAML 中按规则覆盖（例如过渡期 `allow_extra`）。在此之前，下表政策适用于**所有**文件。

---

## 流水线顺序（单文件）

1. 读取 CSV（`src/io.py`）— 编码回退；错位行 → warn 并记录行号后继续  
2. 检测表头行（`src/header_detector.py`）  
3. 表头重命名为标准列名（`src/utils.py`）  
4. **重复列门控** — 两列映射到同一标准名 → fail  
5. **结构门控**（`src/structure.py`）— 缺列/多列 → **fail**；仅顺序不对 → 重排 + **warning**  
6. 科学计数法扫描 — 仅 **warning**（不阻断）  
7. Phantom 尾部行 — **自动删除**  
8. 合计类关键字行 — **warning 报告**，行**不删**  
9. 值清洗（`src/cleaner.py`）  
10. 类型转换（`src/validator.py`）  
11. 写出 `output/` CSV 与 Excel 报告（`src/exporter.py`）

`raw/_audit_fixtures/` 下文件跳过。`.xlsx` → `skipped_xlsx`（无 output）。

---

## 结构与布局

| 情况 | 政策 | 状态 | 是否写出 output？ |
|------|------|------|-------------------|
| 无匹配 YAML 规则 | Fail | `failed` | 否 |
| 找不到表头行 | Fail | `failed` | 否 |
| 缺标准列（rename 后） | Fail | `failed` | 否 |
| 相对标准多列 | Fail | `failed` | 否 |
| 重复映射到同一标准（如两个 `Trade_ID`） | Fail | `failed` | 否 |
| 列集合正确、仅顺序与 YAML 不符 | 按 YAML 重排 | `warning` | 是 |
| CSV 错位行 / 读入 `ParserError` | 跳过坏行后继续 | `warning` | 是（其余通过时） |
| 编码回退（如 utf-8 → cp1252） | 继续 | `warning` | 是 |

**原则：** 列集合错误意味着语义错误，应快速失败并修正 YAML 或源文件；仅顺序问题可安全自动修复。

---

## 行过滤

| 情况 | 政策 |
|------|------|
| **Phantom 行**（文件尾部多为空逗号的行） | **删除** — 阈值与 `audit/constants.py` 一致 |
| **Total / Grand Total** 等合计关键字行 | **保留** — 在 `issues_detail` 中报告，供人工核对 |
| 清洗后整行全空 | **删除** |

---

## 值清洗（`src/cleaner.py`）

按 YAML 中各列的 `type` 应用。

| 输入模式 | 政策 | 说明 |
|----------|------|------|
| `-`、`–`、`—`、`null`、`n/a`、`na` | 清空为空 | 不导致流水线 fail |
| 数值或「像数值」字符串单元格中的 `$` | 去掉 | |
| 千分位逗号（`1,234.56`） | 去逗号 | 欧式 `1.234,56` → `1234.56` |
| 外围引号 | 去掉 | |
| 会计括号 `(5000)`、`($2,364)` | 转为**负数**数值文本 | 会计惯例；与 audit 数值检查一致 |
| **String 列**（`type: string`） | 保留字母 ID（`REF001`、`75512E101`） | 像数值的字符串仍按单元格规则处理 `$`/逗号 |

---

## 科学计数法

| 阶段 | 政策 |
|------|------|
| 清洗前扫描 | 匹配 Excel 式科学计数法 → **warning**（不含 `75512E101` 这类字母后缀 ID） |
| float / numeric 列类型转换 | **不**强转为 float — 在 output CSV 中**保留源文字面量** |
| 其他数值单元格 | 正常转换；写出 CSV 时普通 float 不用科学计数法 |

---

## 日期

| 阶段 | 政策 |
|------|------|
| 解析顺序 | 1）YAML `date_format` 严格解析 → 2）Excel 序列号 → 3）常见备用格式 → 4）pandas 推断 |
| 输出 | 一律按**该列 YAML `date_format`** 格式化（未配置时默认 `%Y-%m-%d`） |
| 非 strict 解析成功 | 报告中 **warning**（`DATE` 类），并统计 alternate / Excel serial / inferred 数量 |
| 解析失败（非空单元格） | **warning**（`TYPE` 转换问题）；输出中该格为空 |

同一日期列可混用 `2025-01-15`、`1/16/2025`、序列号 `45674` 等；输出均归一为 YAML 格式。

---

## 类型转换摘要

| YAML `type` | 行为 |
|-------------|------|
| `int` / `integer` | `to_numeric`，四舍五入，可空 `Int64` |
| `float` / `numeric` | `to_numeric`；科学计数字面量保留为字符串 |
| `date` / `datetime` | 灵活解析（见上），归一化到午夜 |
| `string` | 字符串 dtype |

非空单元格转换失败 → `warning`，计入 `type_conversion_issues`。

---

## 运行状态（`file_summary.status`）

| 状态 | 含义 |
|------|------|
| `success` | 已处理，无 warning |
| `warning` | 已写出 output；请查看 `status_reason` 与 `issues_detail` |
| `failed` | 无 output；需修正规则、文件或标准 |
| `skipped_xlsx` | 请先转为 CSV |

会触发 warning 的情况（非穷尽）：列重排、科学计数法、非 strict 日期、类型转换问题、phantom 已删（info）、合计类行、编码回退、错位 CSV 行等。

---

## Excel 报告（5 个工作表）

| 工作表 | 内容 |
|--------|------|
| `file_summary` | 每文件：`status`、`output_written`、`layout_status`、`clean_status`、`status_reason`、行数、路径 |
| `issues_detail` | 每条问题：`phase`（`pre_clean` / `clean_action` / `post_clean`）、`category`、`severity`、`column`、`message`、`sample_rows` |
| `clean_actions` | 文件级：占位符、`$`、括号、逗号、删除的全空行 |
| `clean_actions_by_column` | 同上，按列拆分 |
| `column_stats` | 每列：空值、转换问题、科学计数、日期解析方式统计 |

---

## YAML 中手工修改的 type

运行 `python -m src.reader` 重新生成时，会按 standard 第 2 行样本**重新推断**列 `type`。会合并保留 `mappings`、前缀、`aliases`、`read`。**不会**保留手工改的 `type`（例如 `Trade_ID: string`）。regenerate 后请重点核对关键列，或把 standard 第 2 行样例改成有代表性的字符串（如 `REF001` 而非 `1234567`）。

---

## 如何变更政策

1. 在此文档（及英文版）中达成一致；若需与 audit 对齐，同步与 audit 维护方确认。  
2. 在 `src/` 中实现。  
3. 更新 `tools/generate_pipeline_fixtures.py` 与 `tests/` 下测试。  
4. 若面向用户的行为有变，更新 [docs/clean_pipeline.md](docs/clean_pipeline.md) 与 README。

在团队尚未在代码中支持按规则覆盖之前，**不要**在 YAML 中添加 `clean_policy` 键。
