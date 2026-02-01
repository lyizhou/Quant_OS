"""AI Agent Service - Autonomous analyst powered by GLM-4.

This service provides an intelligent agent that can:
1. Understand natural language queries
2. Automatically route to appropriate tools/functions
3. Perform multi-step analysis
4. Generate insights and recommendations
"""

import json
import os
from typing import Any, Callable

import httpx
from loguru import logger


class AIAgentService:
    """AI Agent service using GLM-4 for autonomous analysis."""

    def __init__(self, api_key: str = None):
        """Initialize AI agent service.

        Args:
            api_key: ZhipuAI API key (defaults to ZHIPU_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        if not self.api_key:
            raise ValueError("ZHIPU_API_KEY not found in environment")

        self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        self.model = "glm-4"  # Use GLM-4
        self.tools = {}  # Tool registry
        self.conversation_history = []

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: dict,
        function: Callable,
    ):
        """Register a tool that the agent can call.

        Args:
            name: Tool name
            description: What the tool does
            parameters: JSON schema for parameters
            function: The actual function to call
        """
        self.tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
            "callable": function,
        }
        logger.info(f"✓ Registered tool: {name}")

    def _get_tool_definitions(self) -> list[dict]:
        """Get tool definitions for API call (without callable)."""
        return [
            {
                "type": tool["type"],
                "function": tool["function"],
            }
            for tool in self.tools.values()
        ]

    async def chat(
        self,
        user_message: str,
        context: dict = None,
        max_iterations: int = 5,
    ) -> dict:
        """Chat with the AI agent.

        The agent will:
        1. Understand the user's intent
        2. Decide which tools to call
        3. Execute tool calls
        4. Synthesize results
        5. Return a comprehensive response

        Args:
            user_message: User's natural language query
            context: Additional context (user_id, portfolio data, etc.)
            max_iterations: Max tool call iterations to prevent loops

        Returns:
            {
                "response": str,  # Final response text
                "tool_calls": list,  # Tools that were called
                "results": dict,  # Results from tool calls
            }
        """
        try:
            # Add user message to history
            self.conversation_history.append(
                {
                    "role": "user",
                    "content": user_message,
                }
            )

            # Add context if provided
            if context:
                context_msg = f"\n\n[Context: {json.dumps(context, ensure_ascii=False)}]"
                self.conversation_history[-1]["content"] += context_msg

            tool_calls_made = []
            tool_results = {}
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Prepare request
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": self.model,
                    "messages": self.conversation_history,
                }

                # Add tools if available
                if self.tools:
                    payload["tools"] = self._get_tool_definitions()
                    payload["tool_choice"] = "auto"

                # Call GLM-4 API
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    result = response.json()

                if "choices" not in result or not result["choices"]:
                    raise ValueError(f"Invalid API response: {result}")

                assistant_message = result["choices"][0]["message"]

                # Check if agent wants to call tools
                if assistant_message.get("tool_calls"):
                    # Add assistant message to history
                    self.conversation_history.append(assistant_message)

                    # Execute tool calls
                    for tool_call in assistant_message["tool_calls"]:
                        tool_name = tool_call["function"]["name"]
                        tool_args = json.loads(tool_call["function"]["arguments"])

                        logger.info(f"🤖 Agent calling tool: {tool_name} with args: {tool_args}")

                        # Execute the tool
                        if tool_name in self.tools:
                            try:
                                tool_func = self.tools[tool_name]["callable"]
                                result = await tool_func(**tool_args)
                                tool_results[tool_name] = result

                                # Add tool result to history
                                self.conversation_history.append(
                                    {
                                        "role": "tool",
                                        "content": json.dumps(result, ensure_ascii=False),
                                        "tool_call_id": tool_call["id"],
                                    }
                                )

                                tool_calls_made.append(
                                    {
                                        "tool": tool_name,
                                        "args": tool_args,
                                        "result": result,
                                    }
                                )

                            except Exception as e:
                                error_msg = f"Tool execution failed: {str(e)}"
                                logger.error(f"✗ {error_msg}", exc_info=True)

                                self.conversation_history.append(
                                    {
                                        "role": "tool",
                                        "content": json.dumps({"error": error_msg}, ensure_ascii=False),
                                        "tool_call_id": tool_call["id"],
                                    }
                                )
                        else:
                            logger.warning(f"⚠ Tool not found: {tool_name}")

                    # Continue loop to get next response
                    continue

                else:
                    # No more tool calls, agent has final response
                    final_response = assistant_message.get("content", "")

                    # Add to history
                    self.conversation_history.append(
                        {
                            "role": "assistant",
                            "content": final_response,
                        }
                    )

                    return {
                        "response": final_response,
                        "tool_calls": tool_calls_made,
                        "results": tool_results,
                    }

            # Max iterations reached
            logger.warning(f"⚠ Max iterations ({max_iterations}) reached")
            return {
                "response": "抱歉，分析过程超时。请简化您的问题或稍后重试。",
                "tool_calls": tool_calls_made,
                "results": tool_results,
            }

        except Exception as e:
            logger.error(f"AI agent error: {e}", exc_info=True)
            return {
                "response": f"AI分析失败: {str(e)}",
                "tool_calls": [],
                "results": {},
            }

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("✓ Conversation history cleared")

    def get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """你是 Quant_OS 的智能投资助手，专注于A股市场分析。

你的能力：
1. 持仓分析 - 分析用户持仓，提供盈亏分析和风险评估
2. 板块分析 - 分析板块强度，找出热门题材和龙头股
3. 个股研究 - 查询个股行情、技术指标、新闻动态
4. 市场监控 - 监控市场热点，生成每日市场总结

你的工作流程：
1. 理解用户意图
2. 选择合适的工具获取数据
3. 分析数据并生成洞察
4. 提供可操作的建议

注意事项：
- 始终使用中文回复
- 提供具体的数据支持
- 给出明确的操作建议
- 标注风险和不确定性
- 不做绝对的预测

可用工具：
- get_portfolio: 获取用户持仓
- get_sector_strength: 获取板块强度排名
- get_stock_quote: 获取个股实时行情
- search_stock: 搜索股票
- get_hot_sectors: 获取热门板块
- get_market_summary: 获取市场概况
- search_news: 搜索股票新闻

请根据用户的问题，智能选择工具并提供专业的分析。"""

    def set_system_prompt(self):
        """Set system prompt at the beginning of conversation."""
        if not self.conversation_history or self.conversation_history[0]["role"] != "system":
            self.conversation_history.insert(
                0,
                {
                    "role": "system",
                    "content": self.get_system_prompt(),
                },
            )


# Global instance
_agent_instance: AIAgentService | None = None


def get_ai_agent(api_key: str = None) -> AIAgentService:
    """Get or create global AI agent instance.

    Args:
        api_key: ZhipuAI API key

    Returns:
        AI agent instance
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AIAgentService(api_key)
        _agent_instance.set_system_prompt()
    return _agent_instance
