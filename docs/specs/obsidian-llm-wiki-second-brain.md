# Obsidian / LLM Wiki 第二大脑规格

验证日期：2026-06-03

参考：Andrej Karpathy 的 `llm-wiki` gist（2026-04-04）把知识库分为三层：不可变 raw sources、由 LLM 维护的 Markdown wiki、以及约束维护方式的 schema。它的关键不是 RAG 检索，而是把资料逐步“编译”成可链接、可复盘、可继续增长的知识页。

## 1. 结论

本项目应该加入 Karpathy 风格的 LLM Wiki，但它不能替代现有数据库和规则引擎。

正确边界是：

```text
数据库 / JSON store / 后续 SQLite = 结构化事实层、状态机、评分和审计。
Obsidian LLM Wiki = 人可读、可链接、可人工补充的第二大脑。
```

MVP 已采用推荐方案：当 `/api/radar/analyze` 生成雷达报告后，如果设置了 `CIC_OBSIDIAN_WIKI_PATH`，系统会同步写出：

```text
raw/      不可变报告源捕获
company/  公司档案
theme/    产业/主题档案
claim/    claim 证据页
source/   来源/KOL 画像
task/     验证任务
inbox/    Obsidian 人工输入模板
index.md  wiki 目录
log.md    wiki 维护日志
CIC-LLM-WIKI.md  schema 规则
```

## 2. Design Shotgun：三种方案

### 方案 A：数据库驱动的 Wiki 编译层（已选）

流程：

```text
radar JSON / 手动弱信号
  -> 规则引擎生成 RadarReport
  -> JSON store 保存结构化结果
  -> Obsidian wiki 导出 company/theme/claim/source/task 页面
  -> 用户在 Obsidian 的人工笔记区补资料
```

优点：

- 不破坏当前 MVP，最快可用。
- 规则门禁仍由代码控制，wiki 不会把 KOL 或用户笔记误当事实。
- Obsidian 页面可以给人读、给 LLM 读，也能保留人工笔记。

代价：

- 第一版不是完全双向同步。
- Obsidian 输入先沉淀在 `inbox/` 和人工笔记区，后续再由导入器转成 radar JSON。

### 方案 B：Vault-first 输入层

流程：

```text
用户先在 Obsidian 写 raw/inbox 笔记
  -> Agent 读取 inbox
  -> 生成 radar JSON
  -> 系统分析并回写 wiki
```

优点：

- 更贴近“Obsidian 是主工作台”的使用方式。
- 适合大量手动行业观察、访谈、KOL 摘录。

风险：

- 一开始就要处理 Markdown 解析、重复 note、事实/观点归因和导入冲突。
- 用户随手写的判断容易被误升级为 evidence。

### 方案 C：双向知识图谱同步

流程：

```text
SQLite claim graph <-> Obsidian pages
  -> 每个页面 frontmatter 带 stable id
  -> 双向 diff、冲突解决、人工 review queue
```

优点：

- 长期最完整，数据库查询和 Obsidian 编辑可以互相增强。

风险：

- 对 MVP 过重。
- 需要冲突解决、锁定字段、版本迁移和数据一致性检查。

结论：先做 A，保留 B/C 的结构入口。A 能立即让项目拥有“第二大脑”，同时不把事实层复杂度提前引爆。

## 3. 产品原则

1. `raw/` 是不可变事实捕获层，导出后不再修改。
2. `company/`、`theme/`、`claim/`、`source/`、`task/` 是 wiki 编译层，可由系统重写。
3. 用户人工输入只写在 `CIC:USER-NOTES` 标记之间或 `inbox/`。
4. 导出器必须保留用户笔记区，不能覆盖 Obsidian 人工输入。
5. `source_family/source_rank` 仍然表示证据质量；`cost_class/access_mode/license_status` 仍然表示采购和自动化边界。
6. KOL-only、D 级来源、用户 note 不能因为进入 wiki 而自动升级为事实。
7. Wiki 输出可以总结、链接、提出问题，但不能给无条件买卖指令。

## 4. 页面约定

### 4.1 raw page

用途：保存一次雷达分析的完整 JSON。

规则：

- 路径：`raw/YYYY-MM-DD/{report_id}.md`
- `immutable: true`
- 不允许人工修改。
- 任何 wiki claim 都应能回溯到 raw 或用户 inbox。

### 4.2 company page

用途：公司级研究档案。

内容：

- 当前 radar_state 和 E/X/I/U/D。
- 核心 claims。
- 证据摘要表。
- 下一验证任务。
- 人工笔记区。
- 反方和阻断。

### 4.3 theme page

用途：行业/主题级记忆。

内容：

- 主题内公司列表。
- 主题 claims。
- 来源家族分布。
- 人工主题笔记。
- 想补的来源。

### 4.4 claim page

用途：围绕一个 claim 维护证据链。

内容：

- claim 原文。
- 状态、阶段、评分。
- 交叉验证结果。
- 相关证据。
- 阻断原因。
- 验证任务。
- 人工判断和补证记录。

### 4.5 source page

用途：来源和 KOL 画像。

内容：

- 来源家族、等级、可信度、成本类别。
- 偏差和冲突。
- 相关证据。
- 人工来源复盘。

### 4.6 task page

用途：验证任务执行记录。

内容：

- 问题。
- 成功标准。
- 失败标准。
- 验证记录 checklist。

## 5. Obsidian 输入规则

第一版支持两种人工输入位置：

1. 直接在生成页面的 `CIC:USER-NOTES` 区块里写笔记。
2. 在 `inbox/` 下新建 Markdown，使用 `_template.md` 记录公司、主题、来源、原始材料和想验证的问题。

后续导入器只允许把人工输入转成以下草案对象：

```text
user_note
candidate_claim
candidate_evidence
candidate_source_profile_update
candidate_validation_task
```

人工输入默认不能直接成为 `official_disclosure`、`financial_data` 或 A/B 级证据。

## 6. 实现状态

已完成：

- `cic/obsidian_wiki.py`
- `/api/radar/analyze` 自动侧写 wiki。
- `.env.example` 增加 `CIC_OBSIDIAN_WIKI_PATH`。
- `README.md` 增加 Obsidian LLM Wiki 说明。
- 测试覆盖 wiki 页面生成和人工笔记保留。

暂缓：

- Obsidian inbox 自动导入 radar JSON。
- SQLite 级双向同步。
- wiki lint / orphan page / stale claim 检查。
- Dataview 专用 dashboard 页面。

## 7. 下一阶段

Phase B：Obsidian 输入导入器。

```text
读取 inbox/*.md
  -> 提取 frontmatter 和正文
  -> 生成 candidate_claim / candidate_evidence
  -> 要求人工确认
  -> 调用 /api/radar/analyze
  -> 回写 wiki
```

Phase C：Wiki health check。

```text
检查孤儿 claim、断链、过期验证任务、单一来源 claim、KOL-only 未复核项。
```

Phase D：SQLite graph 同步。

```text
每个 wiki page 使用 stable id 对应数据库对象；所有双向更新都进入 review queue。
```
