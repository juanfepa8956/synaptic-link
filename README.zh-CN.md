# Synaptic Link

**一个面向 AI Agent 的、本地优先的第二脑检索层。**

让 Agent 以低成本、按需方式访问你的个人知识库，而不是把整个 Vault 塞进上下文。

[English](README.md)

---

## 它解决什么问题

AI Agent 的上下文窗口是有限的，但个人知识库会持续增长。

你不可能长期把整个 Obsidian Vault 放进 prompt：这会带来高成本、高噪声，以及不可控的上下文膨胀。
你也不能每次都依赖全量文件扫描来找信息：它太慢，也不适合在多轮对话中稳定使用。

真正缺失的是一个中间层：

- 足够轻，可以在每轮对话中调用
- 足够快，可以毫秒级返回结果
- 足够准，可以先召回相关内容，再按需读取原文
- 足够透明，人和 Agent 都知道"查到了什么，为什么查到"

**Synaptic Link，就是这一层。**

---

## 它在整个系统里的位置

一个完整的"第二脑 + Agent"系统，可以拆成四层：

### 1. 宿主层（Host Layer）

Obsidian Vault / Markdown Knowledge Base

负责存放项目、复盘、知识、档案与长期记忆。

### 2. 写入层（Write Layer）

Archivist / 档案管理员 Agent

负责把对话、决策、项目过程、复盘材料沉淀为结构化笔记。

### 3. 检索层（Retrieval Layer）

**Synaptic Link**

负责建立索引、执行搜索、读取原文，是 Agent 访问第二脑时的检索基础设施。

### 4. 行为层（Behavior Layer）

Agent Prompt / Policy / Tool-Use Strategy

负责决定什么时候查、查完是否继续读原文、以及如何将结果融入回答。

**Synaptic Link 只负责第 3 层：检索层。**
它不负责写入笔记，不定义回答策略，也不规定具体平台的调用规则。

---

## 渐进式披露（Progressive Disclosure）

Synaptic Link 的设计核心不是"尽可能多加载信息"，而是：

**只在需要的时候，读取刚好够用的信息。**

它对应的是一套三层访问结构：

### 核心层（Hot Cache）

少量高优先级记忆，始终在线。
例如：SOUL、MEMORY、最近日志、当前工作上下文。

### 突触层（Synapse Index）

中间检索层。
通过 SQLite FTS5 对本地笔记建立轻量索引，先低成本召回相关片段。

### 皮层（Deep Knowledge）

完整 Markdown 原文。
只有在确认需要更多细节时，才继续读取原文内容。

典型流程如下：

1. 先查看核心层，判断现有上下文是否足够
2. 不足时，用 `search` 查询突触层
3. 如果搜索结果已经足够，就直接回答
4. 如果还不够，再用 `read` 读取原文

这种方式避免了"一开始把所有东西都塞进上下文"的粗暴做法，也让 Agent 的记忆访问更接近真实工作流。

---

## 核心能力

Synaptic Link 的 v1.0 只保留最小而清晰的三项能力：

### `index`

为本地第二脑建立可搜索索引。

### `search`

基于查询词，返回最相关的标题、章节、路径和片段。

### `read`

按需读取原始 Markdown 笔记全文。

可选增强：

### `watch`

监听文件变化并自动更新索引。

---

## 示例命令

```bash
# 建立索引
python scripts/synapse.py index

# 搜索
python scripts/synapse.py search "你的查询词"

# 返回 JSON 结果
python scripts/synapse.py search "你的查询词" --json

# 读取原文
python scripts/synapse.py read "/absolute/path/to/note.md"

# 监听变化并自动更新
python scripts/synapse.py watch
```

---

## 搜索结果长什么样

默认输出会包含：标题、章节、路径、命中片段。

```
## 项目复盘 § 检索层设计
   /Users/you/Documents/Obsidian Vault/Projects/复盘.md
   ...这里是命中的相关片段...
```

JSON 模式下，结果会更适合 Agent 或程序消费：

```json
[
  {
    "title": "项目复盘",
    "section": "检索层设计",
    "path": "/absolute/path/to/note.md",
    "snippet": "...命中的相关片段..."
  }
]
```

章节级结果很重要，因为它让 Agent 不只是知道"哪个文件相关"，还知道"相关的是哪一段"。
这有助于它决定：当前片段是否已经足够，还是需要继续读取全文。

---

## 设计原则

### 1. 本地优先（Local-First）

所有笔记都保留在本机。
核心功能不依赖云端服务，不依赖外部向量数据库，也不强制依赖 embedding API。

### 2. 渐进式披露（Progressive Disclosure）

先检索，再读取。
信息按需展开，而不是预加载全部内容。

### 3. 工具与策略分离（Tool / Policy Separation）

Synaptic Link 只提供检索能力。
什么时候调用、如何融入回答、是否继续读原文，交给各平台 Agent 自己决定。

### 4. 轻量优先（Lightweight by Design）

核心功能聚焦于 `index / search / read`。
避免在 v1.0 过早引入过重依赖或复杂特性。

### 5. 跨平台可接入（Agent-Compatible）

它不是某个框架专属插件。
任何能执行 Shell 命令或调用工具接口的 Agent，都可以接入 Synaptic Link。

---

## 它不是什么

Synaptic Link 不是：

- 不是完整记忆系统
- 不是笔记写入系统
- 不是第二脑本体
- 不是 Obsidian 插件
- 不是 SaaS 产品
- 不是默认带向量检索的重型 RAG 框架
- 不是只属于某一个 Agent 平台的私有 skill

它的边界很明确：**它是第二脑之上的检索层。**

---

## 适用场景

Synaptic Link 特别适合以下场景：

- Agent 需要回忆历史项目决策
- Agent 需要基于过往复盘继续推进当前任务
- Agent 需要访问个人知识库，而不是通识知识
- Agent 需要在低 token 成本下获得稳定上下文
- 你希望把 Obsidian / Markdown 第二脑接入多种 Agent Runtime

---

## 集成方式

### OpenClaw

可作为 skill 接入，让 Agent 在需要时主动执行 `search` 和 `read`。

### Claude Code

可在 `CLAUDE.md` 中定义调用规则，例如：

- 涉及项目历史、个人知识、过往决策时先 `search`
- snippet 不够再 `read`
- 不要只靠模型记忆回答历史问题

### 任意支持 Shell 的 Agent

只要能执行命令行工具，就可以调用 Synaptic Link。
使用 `--json` 可以把结果作为结构化输出交给其他程序消费。

---

## 快速开始

**环境要求**

- Python 3.8+
- SQLite 3.35+（Python 3.9+ 在大多数平台上随附）

**配置 Vault 路径**

可以通过环境变量指定：

```bash
export OBSIDIAN_VAULT=/path/to/your/vault
export SYNAPTIC_DB=~/.synaptic-link/synapse.db
```

也可以通过命令行参数覆盖：

```bash
python scripts/synapse.py index --vault /path/to/vault --db /path/to/db
```

**建立索引**

```bash
python scripts/synapse.py index
```

**开始搜索**

```bash
python scripts/synapse.py search "你的查询词"
```

**读取原文**

```bash
python scripts/synapse.py read "/absolute/path/to/note.md"
```

---

## 当前范围（v1.0）

v1.0 的目标不是做"大而全"的记忆平台，而是先把最小核心打磨清楚：

- 本地 Markdown / Obsidian 检索
- SQLite FTS5 索引
- 章节级召回
- JSON 结构化输出
- 面向 Agent 的最小调用接口
- 清晰的系统边界与集成方式

---

## 路线图

| 版本 | 范围 |
|------|------|
| **v1.0** | `index / search / read`，SQLite FTS5 trigram，章节级切分，JSON 输出，本地优先、零依赖核心 |
| v1.1 | 增量索引优化，文件变化监听，更稳的 frontmatter 解析 |
| v1.2 | 可选向量检索接口，本地 embedding / OpenAI-compatible embedding backend |
| v1.3 | 混合检索，更丰富的 ranking / reranking 策略 |
| future | MCP 包装层，更多 Agent Runtime 集成示例 |

---

## 项目背景

这个项目起源于一个真实运行中的多 Agent 系统。

在这个系统里：

- 一个 Agent 负责对话与协作
- 一个档案管理员 Agent 负责维护第二脑
- 第二脑本体是 Obsidian / Markdown Knowledge Base

于是出现了一个关键问题：**对话 Agent 怎样在不加载整个知识库的前提下，稳定访问第二脑中的相关知识？**

Synaptic Link 就是这个问题的答案。
它把"热缓存 → 检索层 → 原文读取"这套渐进式访问模式，落实成了一个轻量、可复用、可被 Agent 调用的检索工具。

---

## License

MIT License. Copyright (c) 2026 Lingxiao Du (dlxeva).
