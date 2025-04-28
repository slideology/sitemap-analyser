#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class WebhookSender:
    def __init__(self, webhook_url: str):
        """初始化 Webhook 发送器"""
        self.webhook_url = webhook_url

    def send_summary(self, title: str, summary: Dict[str, Any]) -> bool:
        """发送汇总消息
        
        Args:
            title: 卡片标题
            summary: 统计摘要信息
        """
        try:
            card = {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**总计网站数：**\n{summary.get('total_sites', 0)}"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**新增URL数：**\n{summary.get('total_new_urls', 0)}"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "以下将分别显社每个网站的详细信息..."
                        }
                    }
                ]
            }

            payload = {
                "msg_type": "interactive",
                "card": card
            }

            return self._send_payload(payload)

        except Exception as e:
            logger.error(f"发送汇总消息异常: {str(e)}")
            return False

            return self._send_payload(payload)

    def send_site_details(self, site_name: str, urls: List[str]) -> bool:
        """发送单个网站的详细信息
        
        Args:
            site_name: 网站名称
            urls: URL列表
        """
        try:
            # 将URL列表分成每组100个
            url_groups = [urls[i:i + 100] for i in range(0, len(urls), 100)]
            
            for i, group in enumerate(url_groups, 1):
                card = {
                    "config": {
                        "wide_screen_mode": True
                    },
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"{site_name} - 新增URL列表 ({i}/{len(url_groups)})"
                        },
                        "template": "green"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**{site_name}**\n本组显示 {len(group)} 个URL："
                            }
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": "\n".join([f"• {url}" for url in group])
                            }
                        }
                    ]
                }

                payload = {
                    "msg_type": "interactive",
                    "card": card
                }

                if not self._send_payload(payload):
                    return False
                
                # 添加短暂延迟，避免消息发送太快
                time.sleep(0.5)

            return True

        except Exception as e:
            logger.error(f"发送网站详情异常: {str(e)}")
            return False

    def _send_payload(self, payload: Dict) -> bool:
        """发送消息到Webhook
        
        Args:
            payload: 消息内容
        """
        try:
            logger.info(f"准备发送消息到 Webhook: {self.webhook_url}")
            logger.info(f"发送的消息内容: {json.dumps(payload, ensure_ascii=False)}")

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            logger.info(f"Webhook响应状态码: {response.status_code}")
            logger.info(f"Webhook响应内容: {response.text}")

            response.raise_for_status()
            result = response.json()

            if result.get("StatusCode") == 0 or result.get("code") == 0:
                logger.info("消息发送成功")
                return True
            else:
                logger.error(f"消息发送失败: {result}")
                return False

        except Exception as e:
            logger.error(f"发送消息异常: {str(e)}")
            return False

            
            logger.info(f"Webhook响应状态码: {response.status_code}")
            logger.info(f"Webhook响应内容: {response.text}")
            
            response.raise_for_status()
            
            if response.status_code == 200:
                result = response.json()
                if result.get("StatusCode") == 0:
                    logger.info("消息发送成功")
                    return True
                else:
                    logger.error(f"消息发送失败: {result}")
                    return False
            else:
                logger.error(f"请求失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"发送消息异常: {str(e)}")
            return False


def create_webhook_sender(config_path: str = "config.json") -> WebhookSender:
    """创建 Webhook 发送器实例"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        webhook_config = config.get('webhook', {})
        if not webhook_config.get('url'):
            logger.error("Webhook URL 未配置")
            return None
            
        return WebhookSender(webhook_config['url'])
    except Exception as e:
        logger.error(f"创建 Webhook 发送器失败: {str(e)}")
        return None
