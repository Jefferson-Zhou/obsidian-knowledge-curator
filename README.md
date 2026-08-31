# Obsidian Knowledge Curator

一个面向 Codex 的 Obsidian 知识库整理 Skill。它会分析文章、补充兼容的 Frontmatter、建立浅层主题目录、移动完整文章资源包，并通过隐藏 JSON 状态支持后续增量维护。

仓库只提供一套固定协议，不要求用户选择版本、存储模式或目录方案。

## 固定结构

用户每次明确指定的文件夹就是最高管理根目录，文件夹名称没有限制：

```text
<run-root>/
├── <primary_topic>/
│   └── <原文章文件夹>/
│       ├── <文章>.md
│       └── assets/
└── .knowledge-curator/
    ├── state.json
    └── relations.json
```

- `primary_topic` 是唯一会物理化的主题层级。
- `topics` 是额外的普通 YAML 字符串，不产生目录。
- 文章 Markdown、`assets/`、隐藏文件和其他资源作为一个完整 bundle 移动。
- 不创建 `AI`、`wiki`、`concept`、`知识体系` 等公共包装目录。
- 不创建概念笔记、主题 registry、主题规范 Markdown/JSON 或生成式导航文件。
- 跨文章关系只写入 `.knowledge-curator/relations.json`。
- 增量指纹和已验证分类只写入 `.knowledge-curator/state.json`。

## 能力

- `Analyze`：只分析和分类。
- `Plan`：生成包含准确路径、前置条件、指纹和回滚方式的变更计划。
- `Apply`：只执行用户明确批准的操作 ID。
- `Maintain`：跳过未变化文章，只处理新增、修改或漂移的 bundle。
- `Audit`：只读检查目录、Frontmatter、关系和增量状态。
- `Governance`：只提出主题标签或关系词汇调整建议。

这些是执行阶段，不是不同版本或可选的数据模型。

## 安装

### SSH

```bash
git clone git@github.com:Jefferson-Zhou/obsidian-knowledge-curator.git ~/.codex/skills/obsidian-knowledge-curator
```

### HTTPS

```bash
git clone https://github.com/Jefferson-Zhou/obsidian-knowledge-curator.git ~/.codex/skills/obsidian-knowledge-curator
```

如果目标目录已经存在，请先在其他位置克隆并人工核对，再替换现有安装；不要把两个副本同时放进 skills 搜索路径。

## 使用

首次整理建议先生成计划：

```text
使用 $obsidian-knowledge-curator 整理以下根目录：

<实际根目录>

该目录本身就是最高层。先分析并给出完整物理移动计划，未经批准不要写入。
```

后续增量维护：

```text
使用 $obsidian-knowledge-curator，以 Maintain 模式维护以下根目录：

<实际根目录>

只处理新增、修改或漂移的文章，跳过未变化内容，先给出计划。
```

## 安全约束

- 不读取或写入所选根目录的父目录。
- 现有 Frontmatter 的键名、值、顺序和 YAML 表示默认保持不变。
- 所有写操作先 dry-run，并绑定 SHA-256 或完整 bundle manifest。
- 文件移动、主题新增、关系修改和状态提交均需要准确操作批准。
- 无变化的 Maintain 运行执行零写入。
- 某个增量 bundle 失败时，不会授权修改其他未批准内容。

## 运行要求

- Codex Skills 支持环境。
- Python 3.9 或更高版本。
- 脚本仅使用 Python 标准库。

## 仓库结构

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── knowledge-model.md
│   ├── workflow-contracts.md
│   └── stages/
└── scripts/
    ├── frontmatter_merge.py
    ├── frontmatter_update.py
    ├── move_bundle.py
    ├── scan_incremental.py
    ├── validate_artifact.py
    └── validate_relations.py
```

`SKILL.md` 是唯一运行入口；README 只用于仓库说明，不参与 Skill 的提示词加载。

## 本地校验

```bash
python3 -m py_compile scripts/*.py
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

行为测试应在隔离的临时根目录中执行，不要直接使用真实 Obsidian 资料作为测试夹具。
