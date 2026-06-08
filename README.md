# astrbOT_plugin_tool_router 🧠

**动态工具路由插件** —— 基于语义匹配，每次只给 LLM 注入最相关的工具，大幅降本增效。

---

## 解决的问题

AstrBot 挂载大量 Skill 后，LLM 每次请求会携带 **200+ 个工具**，导致：

- ❌ Token 严重浪费（工具描述占大量 context）
- ❌ 工具太多，LLM 选择困难，频繁选错
- ❌ 响应慢、成本高

**工具路由** 在每次 LLM 请求前拦截，从海量工具中 **只保留最相关的少数工具**，让 LLM 在精选中做选择。

---

## 工作原理

```
用户消息
    │
    ▼
语义匹配 ──┬── Embedding 可用 → 余弦相似度排序
           │
           └── 不可用/出错 → 关键词匹配回退
    │
    ▼
白名单保留（基础工具永远可用）
    │
    ▼
取 Top-K 个最相关工具注入 LLM
```

### 三步过滤机制

| 阶段 | 说明 |
|------|------|
| **① 白名单保护** | 基础工具（Shell/Python/文件读写等）始终保留，核心能力不受影响 |
| **② 语义排序** | 对数百个工具做 Embedding 余弦相似度评分，按相关性排序 |
| **③ 阈值裁剪** | 只保留分数 ≥ `min_similarity` 且排名 Top-K 的工具 |

### 双引擎匹配

| 引擎 | 条件 | 特点 |
|------|------|------|
| **语义匹配** ✅ | Embedding Provider 已配置并加载 | 理解用户意图，不依赖关键词匹配 |
| **关键词回退** 🔄 | 无 Embedding / 请求异常 | 基于工具名 + 描述词频打分，保证可用 |

---

## 配置

通过 AstrBot 管理后台编辑以下配置项：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `top_k` | int | `10` | 每次保留的普通工具数量（越小越省 token） |
| `min_similarity` | float | `0.3` | 语义相似度阈值 (0-1)，越高过滤越严格 |
| `embedding_provider_id` | string | `""` | 指定 Embedding Provider（留空自动选第一个可用） |
| `embedding_model_name` | string | `""` | 覆盖 Embedding 模型名称（留空使用提供商默认） |
| `whitelist_tools` | list | 见下方 | **用户可自由编辑的白名单工具列表** |

> 💡 **调参建议**：Embedding 效果好 → `min_similarity: 0.35`；仅关键词匹配 → `min_similarity: 0.2~0.25`

### 白名单（默认）

以下工具始终保留，确保 Agent 基础能力不受影响。可通过 `whitelist_tools` 配置项自由增删：

| 工具 | 用途 |
|------|------|
| `astrbot_execute_shell` | 执行 Shell 命令 |
| `astrbot_execute_python` | 执行 Python 代码 |
| `astrbot_file_read_tool` | 读取文件 |
| `astrbot_file_write_tool` | 写入文件 |
| `astrbot_file_edit_tool` | 编辑文件 |
| `astrbot_grep_tool` | 文件内容搜索 |
| `send_message_to_user` | 发送消息 |
| `future_task_tool` | 定时任务管理 |
| `astrbot_web_search` | 联网搜索 |
| `astrbot_fetch_webpage` | 抓取网页内容 |

---

## 效果实测

日志输出示例：

```
# 未启用路由（235 个工具全量注入）
工具路由: 保留 235/235 个 (基础=0, 语义=0, 移除=0)

# 启用后（用户问"画图"）
工具路由: 保留 15/235 个 (基础=5, 语义=10, 移除=220)
```

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 注入工具数 | 235 | **~15** | **↓ 94%** |
| Token 消耗 | 基准 | **大幅降低** | 省到就是赚到 |
| LLM 选择难度 | 极高 | 极低 | 几乎不会选错 |

---

## 安装

```bash
cd /path/to/astrbot/data/plugins
git clone https://github.com/Neo-millunnium/astrbot_plugin_tool_router.git
```

### 依赖

- Python ≥ 3.10
- `numpy`（语义匹配需要）
- AstrBot 中已配置 Embedding Provider（可选，无则自动回退关键词匹配）

---

## 技术细节

- **拦截点**: `@filter.on_llm_request()` —— 在 LLM 调用前修改 `ProviderRequest.func_tool`
- **Embedding 获取**: 调用 `context.get_all_embedding_providers()` 获取可用 Provider
- **安全降级**: 任何异常自动回退到关键词匹配，**不影响正常功能**
- **查询预处理**: 去除 XML/HTML 标签、超长截断（500 字）
- **插件启停**: 由 AstrBot 前端开关直接控制，无需修改配置文件

---

## 更新日志

### v0.3.0 — 2025-06-08

- ✨ **白名单可配置**：新增 `whitelist_tools` 配置项，用户可在后台自由编辑白名单工具列表
- ✨ **Embedding Provider 选择**：新增 `embedding_provider_id` 和 `embedding_model_name` 配置项，支持指定 Provider 和模型
- 🧹 **精简配置**：移除 `enable` 配置项，插件启停由 AstrBot 前端开关统一管理

### v0.2.0 — 2025-06-xx

- ✨ 支持 Embedding Provider 配置
- ✨ 关键词匹配回退机制
- ✨ 日志输出保留/移除统计

### v0.1.0 — 初始版本

- 🎉 基于语义匹配的动态工具路由
- ✨ 10 个基础工具白名单保护
- ✨ Top-K + 阈值裁剪过滤
- ✨ 查询预处理（标签去除、截断）

---

## License

MIT
