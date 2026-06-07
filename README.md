# astrbot_plugin_tool_router 🧠

**动态工具路由插件** — 基于语义匹配，每次只注入与当前对话最相关的工具到 LLM。

---

## 解决的问题

AstrBot 挂载大量 Skill 后，LLM 每次请求会携带 **200+ 个工具**，导致：

- ❌ Token 浪费严重（工具描述占大量 context）
- ❌ 工具太多，LLM 选择困难，常选错工具
- ❌ 每次请求成本高、响应慢

**工具路由** 在 LLM 请求前拦截，从海量工具中**只保留最相关的一小部分**，大幅降本增效。

---

## 工作原理

```
用户消息
    │
    ▼
语义匹配 ──┬── Embedding Provider 可用 → 余弦相似度排序
           │
           └── 不可用 / 出错 → 关键词匹配回退
    │
    ▼
白名单保留（10 个基础工具）
    │
    ▼
取 Top-K 个最相关工具注入 LLM
```

### 三步过滤

| 阶段 | 说明 |
|------|------|
| **1. 白名单保护** | Shell/Python/文件读写等 10 个基础工具永远保留 |
| **2. 语义排序** | 对 230+ 个普通工具做 Embedding 余弦相似度评分 |
| **3. 阈值裁剪** | 只保留分数 ≥ `min_similarity` 且排名 Top-K 的工具 |

### 双引擎匹配

| 引擎 | 条件 | 特征 |
|------|------|------|
| **语义匹配** ✅ | Embedding Provider 已加载 | 理解意图，不依赖关键词 |
| **关键词回退** 🔄 | 无 Embedding / 请求失败 | 基于工具名+描述词频打分 |

---

## 配置

通过 `_conf_schema.json` 配置：

```json
{
    "enable": {
        "description": "启用动态工具路由插件",
        "type": "bool",
        "default": true
    },
    "top_k": {
        "description": "每次保留的最多工具数量（越小越省 token）",
        "type": "int",
        "default": 10
    },
    "min_similarity": {
        "description": "最小语义相似度阈值 (0-1)，越高过滤越严格",
        "type": "float",
        "default": 0.3
    }
}
```

> 💡 **建议**：Embedding 效果好时可设 `min_similarity: 0.35`，关键词场景建议 `0.2-0.25`。

---

## 效果实测

日志输出示例：

```
# 未启用路由（235 个工具全量注入）
工具路由: 保留 235/235 个 (基础=0, 语义=0, 移除=0)

# 启用后（用户问"画图"）
工具路由: 保留 15/235 个 (基础=5, 语义=10, 移除=220)
```

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 注入工具数 | 235 | **~15** |
| Token 节约 | 基准 | **~94%** |
| LLM 选择难度 | 极高 | 极低 |

---

## 安装

### 通过 Git 安装

```bash
cd /path/to/astrbot/data/plugins
git clone https://github.com/Neo-millunnium/astrbot_plugin_tool_router.git
```

### 依赖

- Python ≥ 3.10
- `numpy`（语义匹配场景需要）
- AstrBot 中已配置 Embedding Provider（可选，无则自动回退关键词匹配）

---

## 白名单

以下 10 个工具**始终保留**，确保 Agent 基础能力不受影响：

| 工具 | 用途 |
|------|------|
| `astrbot_execute_shell` | 执行 Shell 命令 |
| `astrbot_execute_python` | 执行 Python 代码 |
| `astrbot_file_read_tool` | 读文件 |
| `astrbot_file_write_tool` | 写文件 |
| `astrbot_file_edit_tool` | 编辑文件 |
| `astrbot_grep_tool` | 文件搜索 |
| `send_message_to_user` | 发送消息 |
| `future_task_tool` | 定时任务 |
| `astrbot_web_search` | 联网搜索 |
| `astrbot_fetch_webpage` | 抓取网页 |

---

## 技术细节

- **拦截点**: `@filter.on_llm_request()` — 在 LLM 调用前修改 `ProviderRequest.func_tool`
- **Embedding 获取**: 调用 `context.get_all_embedding_providers()`，取第一个可用 Provider
- **安全降级**: 任何异常（Embedding 请求失败、Provider 未就绪等）自动回退到关键词匹配，**不影响正常功能**
- **查询预处理**: 去除 XML/HTML 标签、超长截断（500 字）

---

## License

MIT