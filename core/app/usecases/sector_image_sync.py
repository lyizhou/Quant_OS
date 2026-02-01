"""Sector Image Sync - 板块图片同步（使用AI视觉识别）."""

import base64
import io
import json
import os
from typing import Any

import httpx
from PIL import Image

from app.common.logging import logger
from app.data.repositories.sector_repo import SectorRepository
from app.drivers.cn_market_driver.stock_mapper import StockNameMapper


class SectorImageParser:
    """板块图片解析器 - 使用AI视觉模型识别板块截图."""

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
            self.model = "glm-4v-flash"
        elif provider == "openai":
            self.api_url = "https://api.openai.com/v1/chat/completions"
            self.model = "gpt-4o"
        elif provider == "claude":
            self.api_url = "https://api.anthropic.com/v1/messages"
            self.model = "claude-3-sonnet-20240229"
        else:
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

    def parse_sector_image(self, image_path: str) -> dict[str, Any]:
        """解析板块图片.

        Args:
            image_path: 图片路径

        Returns:
            解析结果字典，包含板块信息和股票列表
        """
        logger.info(f"Parsing sector image: {image_path}")

        try:
            # 编码图片
            image_base64, mime_type = self._encode_image(image_path)
            image_url = f"data:{mime_type};base64,{image_base64}"

            # 构建提示词
            system_prompt = """你是一个金融数据录入员。请分析这张图片（通常是产业链、概念股层级图）。

任务：提取所有分类和对应的股票/公司名称。

输出要求：
1. 仅输出标准的 JSON 格式，不要包含 Markdown 标记（如 ```json）。
2. JSON 结构如下：
{
    "title": "图片的主题/板块名称（如 '人形机器人产业链'）",
    "category": "板块分类（如 '产业链', '概念股', '行业'）",
    "description": "板块描述（可选）",
    "categories": [
        {
            "name": "子分类名称（如 '执行器', '减速器', '上游', '中游'）",
            "items": [
                {
                    "name": "股票/公司名称（如 '五洲新春', '贵州茅台'）",
                    "notes": "备注信息（可选，如 '龙头', '核心标的'）"
                }
            ]
        }
    ]
}

关键规则：
1. **准确提取股票名称**：这是最重要的字段，必须准确
2. **不要编造信息**：如果看不清楚，可以留空
3. **保持层级结构**：板块 -> 子分类 -> 股票
4. **提取备注信息**：如果有标注（如 "龙头"、"核心"），记录在 notes 中

注意：
1. 只输出JSON，不要任何解释
2. 股票名称必须准确，这是后续代码映射的关键
3. 如果图片中有多个层级，按照实际层级组织数据"""

            user_prompt = "请分析这张板块/产业链图片，提取所有板块信息和股票列表。"

            # 调用AI视觉API
            with httpx.Client(timeout=30) as client:
                if self.provider == "zhipu":
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
                            "max_tokens": 2000,
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
                            "max_tokens": 2000,
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
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            data = json.loads(result_text)
            logger.info(
                f"Parsed sector: {data.get('title')}, {len(data.get('categories', []))} categories"
            )

            return data

        except Exception as e:
            logger.error(f"Failed to parse sector image: {e}")
            return {"error": str(e)}


class SectorImageSyncUseCase:
    """板块图片同步UseCase - 从图片识别并更新板块数据."""

    def __init__(self, api_key: str, provider: str = "zhipu", tushare_token: str | None = None):
        """初始化同步UseCase.

        Args:
            api_key: AI API密钥
            provider: AI服务提供商 (zhipu/openai/claude)
            tushare_token: Tushare API token（用于股票名称到代码的映射）
        """
        self.parser = SectorImageParser(api_key, provider)
        self.sector_repo = SectorRepository()
        self.stock_mapper = StockNameMapper(tushare_token) if tushare_token else None

    def sync_from_image(self, image_path: str) -> dict[str, Any]:
        """从图片同步板块数据.

        Args:
            image_path: 图片路径

        Returns:
            同步结果字典
        """
        logger.info(f"Starting sector sync from image: {image_path}")

        # 1. 解析图片
        parsed_data = self.parser.parse_sector_image(image_path)

        if "error" in parsed_data:
            logger.error(f"Failed to parse image: {parsed_data['error']}")
            return {"success": False, "error": parsed_data["error"]}

        # 2. 创建或获取板块
        sector_name = parsed_data.get("title", "未命名板块")
        sector_category = parsed_data.get("category", "产业链")
        sector_description = parsed_data.get("description")

        existing_sector = self.sector_repo.get_sector_by_name(sector_name)
        if existing_sector:
            sector_id = existing_sector["id"]
            logger.info(f"Using existing sector: {sector_name} (ID: {sector_id})")
        else:
            sector_id = self.sector_repo.create_sector(
                sector_name, sector_category, sector_description
            )
            logger.info(f"Created new sector: {sector_name} (ID: {sector_id})")

        # 3. 处理子分类和股票
        added_stocks = 0
        added_categories = 0
        errors = []

        for i, cat_data in enumerate(parsed_data.get("categories", [])):
            try:
                # 创建子分类
                cat_name = cat_data.get("name", f"分类{i + 1}")
                category_id = self.sector_repo.create_category(
                    sector_id=sector_id, name=cat_name, description=None, sort_order=i
                )
                added_categories += 1
                logger.info(f"Created category: {cat_name} (ID: {category_id})")

                # 添加股票
                for item in cat_data.get("items", []):
                    try:
                        # 提取股票信息
                        if isinstance(item, str):
                            stock_name = item
                            notes = None
                        elif isinstance(item, dict):
                            stock_name = item.get("name", "")
                            notes = item.get("notes")
                        else:
                            continue

                        if not stock_name:
                            continue

                        # 使用 StockNameMapper 获取代码
                        if self.stock_mapper:
                            symbol = self.stock_mapper.get_code_by_name(stock_name)
                        else:
                            symbol = None

                        if not symbol:
                            error_msg = f"无法获取股票代码: {stock_name}"
                            logger.warning(error_msg)
                            errors.append(error_msg)
                            continue

                        # 添加到板块
                        self.sector_repo.add_stock_to_sector(
                            symbol=symbol,
                            stock_name=stock_name,
                            sector_id=sector_id,
                            category_id=category_id,
                            notes=notes,
                        )
                        added_stocks += 1
                        logger.info(f"Added stock: {stock_name} ({symbol}) to {cat_name}")

                    except Exception as e:
                        error_msg = f"Failed to add stock {stock_name}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)

            except Exception as e:
                error_msg = f"Failed to process category {cat_name}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # 4. 返回结果
        result = {
            "success": True,
            "sector_id": sector_id,
            "sector_name": sector_name,
            "added_categories": added_categories,
            "added_stocks": added_stocks,
            "errors": errors,
        }

        logger.info(
            f"Sector sync completed: {sector_name}, "
            f"{added_categories} categories, {added_stocks} stocks, {len(errors)} errors"
        )

        return result
