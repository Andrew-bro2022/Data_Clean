# 配置说明（`config/file_rules.yaml`）

## 公司 / 干净交付

若交接代码库时不希望带上开发用的测试映射或合成标准：

- 以 **`file_rules.company.template.yaml`** 为起点：复制为机器上的 `config/file_rules.yaml`（或替换现有文件）。
  - `mappings` 为空 —— 仅添加你们真实 feed 所需的 raw→standard 映射。
  - 已省略合成规则 **`Test_Wide_*`**、**`Test_Multi_*`**（不在 `standards/` 中）。
- 若不在目标环境跑回归，可删除 **`raw/_audit_fixtures/`**、**`raw/pipeline_tests/`**。
- 保持 **`standards/`** 与 `rules` 下键名一致（或更新 `standards/` 后运行 `python -m src.reader --base-dir .`）。

本项目由 **`config/file_rules.yaml`** 驱动。**audit** 与 **数据清洗** 都依赖它来决定：

- 如何读取 raw（编码、分隔符、`skiprows`）
- 每个 raw 对应哪套标准 schema
- 各列类型与日期格式

## 快速原则

- **新标准**（新域 / 新列集合）：在 `standards/` 增改后，用 `src.reader` 重新生成/合并 YAML。
- **仅新 raw、映射已有标准**：更新匹配方式（`mappings` 或 `raw_prefix_to_standard`）。

## YAML 结构（概要）

- **`defaults`**：全局读入选项（规则未覆盖时使用）。
  - `encoding`（如 `utf-8`、`latin1`）
  - `delimiter`（多为 `,`）
  - `skiprows`（上游有固定前置行时）
- **`header_match_threshold`**：表头匹配比例阈值（默认 `0.6`）。
- **`mappings`**：显式 raw→standard（优先级最高）。
  - 键可为 **`filename.csv`** 或 **`raw/` 下路径**（正斜杠），如 `teamA/foo.csv`。
  - 值为 `rules` 下的键（标准文件名），如 `Desk_RWA_r20260205.csv`。
- **`raw_prefix_to_standard`**：raw **文件名前缀** → 标准规则（适合日期后缀变化）。
  - 例：`DESK_STANDALONE_RWA_: Desk_RWA_r20260205.csv`
- **`rules`**：标准 schema，每个标准文件一条。
  - `aliases`：额外可匹配名称（经 token 归一化）
  - `read`：按标准覆盖读入选项
  - `columns`：列规则列表：`name`、`type`（`int`/`float`/`date`/`string`）、日期的 `date_format`（如 `'%Y-%m-%d'`）

## 匹配优先级（谁生效）

流水线匹配 raw 到规则的顺序：

1. **`mappings`** 按 **`raw/` 下相对路径**（如 `teamA/foo.csv`）
2. **`mappings`** 按 **仅文件名**（如 `foo.csv`）
3. **`raw_prefix_to_standard`**（更长前缀优先）
4. **`rules[*].aliases` / 标准文件名** 的 token 匹配（最弱）

若匹配不稳定，优先用 **`raw_prefix_to_standard`** 或 **`mappings`**。

## 推荐更新流程

### A）有新标准

1. 在 `standards/` 增改 CSV（第 1 行列名，第 2 行样例）。
2. 重新生成/合并 YAML：

```bash
python -m src.reader --base-dir .
```

说明：默认 **merge**，保留手工维护的 `mappings`、`raw_prefix_to_standard`。  
只有需要全盘重来时用 `--no-merge`（需重新补映射/前缀）。

### B）有新 raw，应对应已有标准

任选其一：

- 文件名仅日期/后缀变化 → **`raw_prefix_to_standard`**
- 文件名杂乱或不同子目录同名 → **`mappings`**

更新 YAML 后可验证：

```bash
python -m audit.main --base-dir .
python -m src.main --base-dir .
```

## Audit 与数据清洗的差异（重要）

- **Audit**：必须有 `file_rules.yaml`。raw **未匹配规则**时仍可做 **文件级** 检查。
- **数据清洗**：raw **未匹配规则** → 状态 **failed**（`No matching standard rule`）。

## 常见问题

- **相对标准缺很多列**
  - 在 `header_match_threshold: 0.6` 下，表头行至少要命中标准列名的 60%。例如 4 列标准最多只能「缺 1 列」仍能识别表头。要对 **多个缺列** 做端到端回归时，本仓库使用合成 10 列标准 `Test_Wide_Audit_r20260510.csv` 及对应夹具（见 `audit/generate_test_raw_fixtures.py`、`tools/generate_pipeline_fixtures.py`）。

- **找不到表头**
  - 仅在确实需要时降低阈值；或修正 `skiprows`、分隔符、编码使预览读正确。

- **匹配到错误标准**
  - 增加显式 **`mappings`**（路径级映射最可靠）。

- **raw 嵌套过深**
  - 流水线只扫描 `raw/*` 与 `raw/*/*`；更深路径按设计忽略。
