# 更新日志

## v1.0.0 — 2025-06-08

- ✨ **白名单可配置**：新增 `whitelist_tools` 配置项，用户可在后台自由编辑白名单工具列表
- ✨ **Embedding Provider 选择**：新增 `embedding_provider_id` 和 `embedding_model_name` 配置项，支持指定 Provider 和模型
- ✨ **关键词匹配回退**：无 Embedding 或请求异常时自动降级，保证可用
- 🎉 基于语义匹配的动态工具路由，每次仅注入最相关的 Top-K 个工具
- 🛡️ 10 个基础工具白名单保护，核心能力不受影响
- ⚡ Top-K + 阈值裁剪双重过滤，大幅降低 Token 消耗
