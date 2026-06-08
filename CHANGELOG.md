# 更新日志

## v1.0.0 — 2025-06-08

- ✨ **白名单可配置**：新增 `whitelist_tools` 配置项，用户可在后台自由编辑白名单工具列表
- ✨ **Embedding Provider 选择**：新增 `embedding_provider_id` 和 `embedding_model_name` 配置项，支持指定 Provider 和模型
- ✨ **关键词匹配回退机制**：无 Embedding 或请求异常时自动降级
- 🧹 **精简配置**：移除 `enable` 配置项，插件启停由 AstrBot 前端开关统一管理
- 📊 **日志优化**：每次路由输出保留/移除统计，方便调参
- 🎉 基于语义匹配的动态工具路由
- ✨ 10 个基础工具白名单保护
- ✨ Top-K + 阈值裁剪过滤
- ✨ 查询预处理（标签去除、截断）
