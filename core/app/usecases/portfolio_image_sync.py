"""Portfolio Image Sync - 持仓图片同步（使用AI视觉识别）."""

import base64
import io
import json
import os
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from app.common.logging import logger
from app.data.repositories.user_portfolio_repo import UserPortfolioRepository
from app.drivers.cn_market_driver.stock_mapper import StockNameMapper


class PortfolioImageParser:
    """持仓图片解析器 - 使用AI视觉模型识别持仓截图."""

    def __init__(self, api_key: str, provider: str = "zhipu"):
        """初始化解析器.

        Args:
            api_key: API密钥
            provider: AI服务提供商 (zhipu/openai/claude)
        """
        self.api_key = api_key
        self.provider = provider

        if provider == "zhipu":
            self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            self.model = "glm-4v-flash"  # 智谱AI视觉模型
        elif provider == "openai":
            self.api_url = "https://api.openai.com/v1/chat/completions"
            self.model = "gpt-4o"
        elif provider == "claude":
            self.api_url = "https://api.anthropic.com/v1/messages"
            self.model = "claude-3-sonnet-20240229"
        else:
            # 默认使用智谱AI
            logger.warning(f"Provider {provider} not supported, using zhipu")
            self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            self.model = "glm-4v-flash"
            self.provider = "zhipu"

    def _encode_image(self, image_path: str) -> tuple[str, str]:
        """将图片编码为base64.

        如果图片过大(>10MB)或分辨率过高(>4096)，会自动进行压缩。
        同时会将RGBA等格式转换为RGB，确保AI模型兼容性。

        Args:
            image_path: 图片路径

        Returns:
            (base64编码的图片, MIME类型)
        """
        # 限制参数
        MAX_SIZE = 10 * 1024 * 1024  # 10MB
        MAX_DIMENSION = 4096

        try:
            file_size = os.path.getsize(image_path)

            with Image.open(image_path) as img:
                # 获取原始格式
                orig_format = img.format
                width, height = img.size
                mode = img.mode

                # 检查是否需要处理
                needs_processing = False

                # 1. 检查大小限制
                if file_size > MAX_SIZE:
                    needs_processing = True
                if max(width, height) > MAX_DIMENSION:
                    needs_processing = True

                # 2. 检查颜色模式 (RGBA/P/LA 需要转 RGB)
                if mode in ("RGBA", "P", "LA"):
                    needs_processing = True

                # 3. 检查格式兼容性 (非 JPEG/PNG/WEBP 转 JPEG)
                if orig_format not in ["JPEG", "PNG", "WEBP"]:
                    needs_processing = True

                # 如果不需要处理，直接返回原图
                if not needs_processing:
                    mime_map = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
                    mime_type = mime_map.get(orig_format, "image/jpeg")

                    with open(image_path, "rb") as f:
                        return base64.b64encode(f.read()).decode("utf-8"), mime_type

                # 需要处理：转换为RGB并压缩为JPEG
                logger.info(
                    f"Image processing: size={file_size / 1024 / 1024:.2f}MB, dim={width}x{height}, fmt={orig_format}, mode={mode}"
                )

                # 转换RGB (去除alpha通道，兼容JPEG)
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    # 创建白底背景（避免透明变黑）
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # 调整尺寸
                if max(img.size) > MAX_DIMENSION:
                    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

                # 保存到内存
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                return base64.b64encode(buffer.getvalue()).decode("utf-8"), "image/jpeg"

        except Exception as e:
            logger.warning(f"Error optimizing image, falling back to raw read: {e}")
            # 降级处理：直接读取
            # 尝试根据扩展名推断MIME类型
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = "image/jpeg"  # 默认
            if ext == ".png":
                mime_type = "image/png"
            elif ext == ".webp":
                mime_type = "image/webp"

            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8"), mime_type

    def parse_portfolio_image(self, image_path: str) -> dict[str, Any]:
        """解析持仓图片.

        Args:
            image_path: 图片路径

        Returns:
            解析结果字典，包含positions列表
        """
        logger.info(f"Parsing portfolio image: {image_path}")

        try:
            # 编码图片
            image_base64, mime_type = self._encode_image(image_path)
            image_url = f"data:{mime_type};base64,{image_base64}"

            # 构建提示词
            system_prompt = """你是一个金融数据助理。请分析截图，提取持仓信息并输出为 JSON。

关键规则：
1. **不要编造股票代码**：截图中如果看不到 6 位数字代码（如 600xxx, 000xxx, 300xxx），code 字段请返回 null 或空字符串 ""。
2. **区分数值**：注意 "494649" 这样的大数字是市值（Market Value），不是股票代码！股票代码必须是6位数字且符合A股规则。
3. **提取名称**：准确提取中文股票名称（如 "五洲新春"）。这是最重要的字段！
4. **提取数量**：持仓数量通常在"数量/可用"列（如 6100）。
5. **提取成本价**：成本价通常在"现价/成本"列的右侧（如 77.8486）。
6. **提取市值**：持仓市值是较大的数字（如 494649.00）。
7. **计算当前价**：如果截图中有"现价"列，提取现价；否则用 市值 / 数量 计算。

常见A股代码格式（必须是6位数字）：
- 上海主板：600xxx、601xxx、603xxx、605xxx
- 深圳主板：000xxx、001xxx、002xxx
- 创业板：300xxx
- 科创板：688xxx

输出JSON格式：
{
    "total_assets": 498516.27,
    "positions": [
        {
            "name": "五洲新春",
            "code": null,
            "quantity": 6100,
            "avg_cost": 77.8486,
            "current_price": 81.0900,
            "market_value": 494649.00,
            "profit": 19772.48,
            "profit_pct": 4.16
        }
    ]
}

注意：
1. 只输出JSON，不要任何解释
2. **如果看不到股票代码，code 设为 null（绝对不要编造，不要用市值代替）**
3. **name 字段必须准确提取，这是最关键的字段**
4. 数字不要包含逗号
5. 如果没有现价，用 market_value / quantity 计算
6. 如果没有盈亏，用 (current_price - avg_cost) × quantity 计算"""

            user_prompt = "请分析这张持仓截图，提取所有持仓信息。"

            # 调用AI视觉API
            with httpx.Client(timeout=30) as client:
                if self.provider == "zhipu":
                    # 智谱AI GLM-4V
                    response = client.post(
                        self.api_url,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "model": self.model,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": f"{system_prompt}\n\n{user_prompt}",
                                        },
                                        {"type": "image_url", "image_url": {"url": image_url}},
                                    ],
                                }
                            ],
                            "temperature": 0.3,
                        },
                    )
                elif self.provider == "openai":
                    response = client.post(
                        self.api_url,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "model": self.model,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": f"{system_prompt}\n\n{user_prompt}",
                                        },
                                        {"type": "image_url", "image_url": {"url": image_url}},
                                    ],
                                }
                            ],
                            "max_tokens": 1000,
                            "temperature": 0.3,
                        },
                    )
                elif self.provider == "claude":
                    response = client.post(
                        self.api_url,
                        headers={
                            "x-api-key": self.api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "max_tokens": 1000,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": f"{system_prompt}\n\n{user_prompt}",
                                        },
                                        {
                                            "type": "image",
                                            "source": {
                                                "type": "base64",
                                                "media_type": "image/jpeg",
                                                "data": image_base64,
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                    )
                else:
                    return {"error": f"Unsupported provider: {self.provider}"}

                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"AI API error: {response.status_code}, detail: {error_detail}")
                    return {"error": f"API错误: {response.status_code}\n详情: {error_detail[:200]}"}

                # 解析响应
                if self.provider in ["zhipu", "openai"]:
                    result_text = response.json()["choices"][0]["message"]["content"].strip()
                elif self.provider == "claude":
                    result_text = response.json()["content"][0]["text"].strip()

            # 解析JSON
            # 提取JSON部分
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            data = json.loads(result_text)
            logger.info(f"Parsed {len(data.get('positions', []))} positions from image")

            return data

        except Exception as e:
            logger.error(f"Failed to parse portfolio image: {e}")
            return {"error": str(e)}

    def validate_parsed_data(self, data: dict) -> tuple[bool, str]:
        """验证解析的数据.

        Args:
            data: 解析结果

        Returns:
            (是否有效, 错误消息)
        """
        if "error" in data:
            return False, data["error"]

        if "positions" not in data or not data["positions"]:
            return False, "未识别到任何持仓数据"

        # 验证每个持仓
        for i, pos in enumerate(data["positions"], 1):
            # 股票名称是必须的
            name = pos.get("name", "").strip()
            if not name:
                return False, f"第{i}个持仓缺少股票名称"

            # 代码可以为空（后续通过名称反查）
            code = pos.get("code")

            # 如果提供了代码，验证格式
            if code:
                # 验证代码格式（必须是6位数字）
                if not str(code).isdigit() or len(str(code)) != 6:
                    logger.warning(f"第{i}个持仓代码格式可疑: {code}，将尝试通过名称'{name}'反查")
                    # 不直接返回错误，允许后续通过名称修正
                else:
                    # 验证代码范围
                    if not self._is_valid_stock_code(str(code)):
                        logger.warning(
                            f"第{i}个持仓代码不在有效范围: {code}，将尝试通过名称'{name}'反查"
                        )

            # 验证数量
            if not pos.get("quantity") or pos["quantity"] <= 0:
                return False, f"第{i}个持仓({name})数量无效"

            # 验证成本价
            if not pos.get("avg_cost") or pos["avg_cost"] <= 0:
                return False, f"第{i}个持仓({name})成本价无效"

        return True, "数据验证通过"

    def _is_valid_stock_code(self, symbol: str) -> bool:
        """验证股票代码是否在有效范围内.

        Args:
            symbol: 6位股票代码

        Returns:
            是否有效
        """
        if not symbol or len(symbol) != 6:
            return False

        # 上海主板：600xxx-605xxx
        if symbol.startswith(("600", "601", "603", "605")):
            return True

        # 深圳主板：000xxx-001xxx
        if symbol.startswith(("000", "001")):
            return True

        # 创业板：300xxx
        if symbol.startswith("300"):
            return True

        # 科创板：688xxx
        if symbol.startswith("688"):
            return True

        # 北交所：430xxx, 830xxx
        if symbol.startswith(("430", "830")):
            return True

        # 其他可能的代码段
        # 深圳中小板（已并入主板）：002xxx
        if symbol.startswith("002"):
            return True

        return False


class PortfolioImageSyncUseCase:
    """持仓图片同步UseCase - 从图片识别并更新持仓."""

    def __init__(
        self,
        user_id: str,
        api_key: str,
        provider: str = "zhipu",
        tushare_token: str | None = None,
    ):
        """初始化同步UseCase.

        Args:
            user_id: 用户ID
            api_key: AI API密钥
            provider: AI服务提供商 (zhipu/openai/claude)
            tushare_token: Tushare API token（用于股票名称到代码的映射）
        """
        self.user_id = user_id
        self.parser = PortfolioImageParser(api_key, provider)
        self.portfolio_repo = UserPortfolioRepository()
        self.stock_mapper = StockNameMapper(tushare_token) if tushare_token else None

    def sync_from_image(
        self, image_path: str, market: str = "CN", replace_all: bool = True
    ) -> dict[str, Any]:
        """从图片同步持仓数据.

        Args:
            image_path: 图片路径
            market: 市场（CN/US）
            replace_all: 是否替换所有持仓（True=清空后重建，False=增量更新）

        Returns:
            同步结果字典
        """
        logger.info(f"Starting portfolio sync from image: {image_path}")

        # 1. 解析图片
        parsed_data = self.parser.parse_portfolio_image(image_path)

        # 2. 验证数据
        is_valid, error_msg = self.parser.validate_parsed_data(parsed_data)
        if not is_valid:
            logger.error(f"Invalid parsed data: {error_msg}")
            return {"success": False, "error": error_msg}

        positions = parsed_data["positions"]
        logger.info(f"Parsed {len(positions)} positions from image")

        # 3. 如果是替换模式，先清空现有持仓
        if replace_all:
            existing_positions = self.portfolio_repo.list_positions_by_user(self.user_id)
            for pos in existing_positions:
                if pos["market"] == market:
                    self.portfolio_repo.delete_position(pos["id"])
            logger.info(f"Cleared {len(existing_positions)} existing positions")

        # 4. 批量添加新持仓
        added_count = 0
        updated_count = 0
        errors = []

        for pos in positions:
            try:
                # 提取原始数据
                raw_code = pos.get("code")
                stock_name = pos.get("name", "")
                quantity = pos["quantity"]
                avg_cost = pos["avg_cost"]
                market_value = pos.get("market_value")

                # 使用 StockNameMapper 修正代码
                if self.stock_mapper:
                    symbol = self.stock_mapper.validate_and_fix_code(
                        code=raw_code, name=stock_name, market_value=market_value
                    )
                else:
                    # 如果没有 mapper，使用原始代码
                    symbol = raw_code

                # 如果仍然没有有效代码，跳过
                if not symbol:
                    error_msg = f"无法获取股票代码: name='{stock_name}', raw_code='{raw_code}'"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue

                # 检查是否已存在
                existing = self.portfolio_repo.get_position_by_symbol(self.user_id, symbol, market)

                if existing:
                    # 已存在（可能是增量模式，或者是当前批次中的重复项），执行更新
                    self.portfolio_repo.update_position(
                        existing["id"], quantity=quantity, avg_cost=avg_cost
                    )
                    updated_count += 1
                    logger.info(f"Updated position: {symbol} ({stock_name})")
                else:
                    # 添加新持仓，保存股票名称到notes
                    notes = (
                        f"股票名称:{stock_name}"
                        if stock_name
                        else f"Synced from image at {Path(image_path).name}"
                    )
                    self.portfolio_repo.add_position(
                        user_id=self.user_id,
                        symbol=symbol,
                        market=market,
                        position_type="long",
                        quantity=quantity,
                        avg_cost=avg_cost,
                        notes=notes,
                    )
                    added_count += 1
                    logger.info(f"Added position: {symbol} ({stock_name})")

            except Exception as e:
                error_msg = f"Failed to sync {pos.get('name', 'unknown')}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # 5. 返回结果
        result = {
            "success": True,
            "added": added_count,
            "updated": updated_count,
            "total": len(positions),
            "errors": errors,
            "summary": parsed_data.get("total_market_value"),
        }

        logger.info(
            f"Portfolio sync completed: {added_count} added, {updated_count} updated, "
            f"{len(errors)} errors"
        )

        return result

    def get_sync_summary(self) -> dict[str, Any]:
        """获取同步后的持仓汇总.

        Returns:
            持仓汇总字典
        """
        positions = self.portfolio_repo.list_positions_by_user(self.user_id)

        if not positions:
            return {
                "total_positions": 0,
                "total_cost": 0,
                "positions": [],
            }

        total_cost = sum(p["quantity"] * p["avg_cost"] for p in positions)

        return {
            "total_positions": len(positions),
            "total_cost": total_cost,
            "positions": positions,
        }
