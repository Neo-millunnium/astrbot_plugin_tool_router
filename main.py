from __future__ import annotations

import re
from typing import Any

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.core.agent.tool import FunctionTool, ToolSet
from astrbot.core.star import Context, Star

# 无论如何都会保留的基础工具（白名单）
ESSENTIAL_TOOLS = {
    "astrbot_execute_shell",
    "astrbot_execute_python",
    "astrbot_file_read_tool",
    "astrbot_file_write_tool",
    "astrbot_file_edit_tool",
    "astrbot_grep_tool",
    "send_message_to_user",
    "future_task_tool",
    "astrbot_web_search",
    "astrbot_fetch_webpage",
}


class ToolRouterPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context, config)
        self._context = context
        self._cfg = config
        self._embedding_provider = None
        self._initialized = False

    async def _ensure_initialized(self):
        if self._initialized:
            return
        try:
            providers = self._context.get_all_embedding_providers()
            if providers:
                # 根据 embedding_provider_id 配置选择指定的 provider
                configured_id = self._cfg.get("embedding_provider_id", "") if self._cfg else ""

                if configured_id:
                    # 按 id 查找匹配的 provider
                    matched = [p for p in providers if getattr(p, 'provider_config', {}).get("id", "") == configured_id]
                    if matched:
                        self._embedding_provider = matched[0]
                        logger.info(f"工具路由插件: 已选择 Embedding Provider [{configured_id}]")
                    else:
                        # 未匹配到指定 id，回退到第一个并给出警告
                        available_ids = [p.provider_config.get("id", "unknown") for p in providers]
                        logger.warning(
                            f"工具路由插件: 未找到配置的 Embedding Provider ID [{configured_id}]，"
                            f"当前可用的 provider id: {available_ids}，将使用第一个可用 provider"
                        )
                        self._embedding_provider = providers[0]
                else:
                    # 未配置 provider_id，使用第一个
                    self._embedding_provider = providers[0]
                    logger.info("工具路由插件: 已加载第一个可用的 Embedding Provider")

                # 如果配置了 model_name，覆盖 provider 的模型
                configured_model = self._cfg.get("embedding_model_name", "") if self._cfg else ""
                if configured_model and self._embedding_provider:
                    current_model = self._embedding_provider.get_model()
                    if current_model != configured_model:
                        self._embedding_provider.set_model(configured_model)
                        logger.info(
                            f"工具路由插件: 已覆盖 Embedding 模型 "
                            f"[{current_model or '默认'} -> {configured_model}]"
                        )
            else:
                logger.warning("工具路由插件: 未找到 Embedding Provider，使用关键词匹配")
            self._initialized = True
        except Exception as e:
            logger.error(f"工具路由插件初始化失败: {e}")

    def _get_top_k(self) -> int:
        return self._cfg.get("top_k", 10) if self._cfg else 10

    def _get_min_similarity(self) -> float:
        return self._cfg.get("min_similarity", 0.3) if self._cfg else 0.3

    def _is_enabled(self) -> bool:
        return self._cfg.get("enable", True) if self._cfg else True

    def _extract_query(self, event: AstrMessageEvent, req: ProviderRequest) -> str:
        query = req.prompt or event.message_str or ""
        query = re.sub(r"<[^>]+>", " ", query)
        query = re.sub(r"\[[^\]]+\]", " ", query)
        query = re.sub(r"\s+", " ", query).strip()
        return query[:500]

    def _keyword_match(self, query: str, tool: FunctionTool) -> float:
        query_lower = query.lower()
        name_lower = tool.name.lower()
        desc_lower = (tool.description or "").lower()
        score = 0.0
        if name_lower in query_lower:
            score += 0.8
        name_words = set(re.findall(r'\w+', name_lower))
        query_words = set(re.findall(r'\w+', query_lower))
        common = name_words & query_words
        if common:
            score += 0.3 * len(common) / max(len(name_words), 1)
        desc_words = set(re.findall(r'\w+', desc_lower))
        desc_common = query_words & desc_words
        if desc_common:
            score += 0.15 * len(desc_common) / max(len(desc_words), 1)
        return min(score, 1.0)

    async def _semantic_match(self, query: str, tool: FunctionTool) -> float:
        if not self._embedding_provider:
            return self._keyword_match(query, tool)
        try:
            tool_text = f"{tool.name}: {tool.description or ''}"
            texts = [query, tool_text]
            embeddings = await self._embedding_provider.get_embeddings_batch(texts)
            if not embeddings or len(embeddings) < 2:
                return self._keyword_match(query, tool)
            import numpy as np
            query_vec = np.array(embeddings[0], dtype=np.float32)
            tool_vec = np.array(embeddings[1], dtype=np.float32)
            dot = np.dot(query_vec, tool_vec)
            norm = np.linalg.norm(query_vec) * np.linalg.norm(tool_vec)
            if norm == 0:
                return 0.0
            return float(dot / norm)
        except Exception as e:
            logger.debug(f"语义匹配失败，回退到关键词: {e}")
            return self._keyword_match(query, tool)

    @filter.on_llm_request()
    async def filter_tools(self, event: AstrMessageEvent, req: ProviderRequest) -> None:
        if not self._is_enabled():
            return
        if not req.func_tool or req.func_tool.empty():
            return

        await self._ensure_initialized()

        query = self._extract_query(event, req)
        if not query:
            return

        top_k = self._get_top_k()
        min_sim = self._get_min_similarity()
        all_tools = req.func_tool.tools

        if len(all_tools) <= top_k:
            return

        # 分离基础工具和普通工具
        essential = []
        others = []
        for tool in all_tools:
            if not tool.active:
                continue
            if tool.name in ESSENTIAL_TOOLS:
                essential.append(tool)
            else:
                others.append(tool)

        # 对普通工具做语义匹配排序
        scored_tools = []
        for tool in others:
            score = await self._semantic_match(query, tool)
            scored_tools.append((score, tool))

        scored_tools.sort(key=lambda x: x[0], reverse=True)

        # 保留基础工具 + 分数最高的 top_k 个普通工具
        kept_tools = list(essential)
        kept_names = {t.name for t in essential}

        for score, tool in scored_tools:
            if len(kept_tools) >= top_k + len(essential):
                break
            if score >= min_sim and tool.name not in kept_names:
                kept_tools.append(tool)
                kept_names.add(tool.name)

        # 如果还不够，补一些分数高的
        if len(kept_tools) < min(5, len(all_tools)):
            for score, tool in scored_tools:
                if tool.name not in kept_names and len(kept_tools) < top_k + len(essential):
                    kept_tools.append(tool)
                    kept_names.add(tool.name)

        if kept_tools:
            removed = len(all_tools) - len(kept_tools)
            logger.info(
                f"工具路由: 保留 {len(kept_tools)}/{len(all_tools)} 个 "
                f"(基础={len(essential)}, 语义={len(kept_tools)-len(essential)}, 移除={removed})"
            )
            req.func_tool = ToolSet(tools=kept_tools)