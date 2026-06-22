# 脚本文档索引

本目录包含 `src/` 下各脚本对应的说明文档（README 风格）。

**流水线总览：** [clean_pipeline.md](clean_pipeline.md)（英文）  
**audit → clean 批次流程：** [audit_clean_workflow.md](audit_clean_workflow.md)（英文）  
**清洗政策：** [README_DATA_CLEAN_POLICY_CN.md](../README_DATA_CLEAN_POLICY_CN.md)（[英文](../README_DATA_CLEAN_POLICY.md)）

- `audit_clean_workflow.md`：推荐 audit → clean 步骤与行为对照表
- `clean_pipeline.md`：清洗端到端流程、报告表、常见场景
- `main.md`：流水线入口与运行时流程
- `reader.md`：标准 CSV 解析与 YAML 规则加载/生成
- `file_matcher.md`：raw 与 standard 的文件匹配
- `header_detector.md`：表头行打分与检测
- `cleaner.md`：单元格级清洗逻辑
- `validator.md`：类型转换与状态推导
- `exporter.md`：清洗后 CSV 导出与 Excel 报告
- `utils.md`：共享工具函数
- `types.md`：数据类约定
- `__init__.md`：包标记说明
