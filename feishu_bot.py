#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import requests
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class FeishuBot:
    def __init__(self, app_id: str, app_secret: str, chat_id: str):
        """初始化飞书机器人"""
        self.app_id = app_id
        self.app_secret = app_secret
        self.chat_id = chat_id
        self.base_url = "https://open.feishu.cn/open-apis"
        self.access_token = None
        self.token_expires_time = 0

    def _get_tenant_access_token(self) -> str:
        """获取 tenant_access_token"""
        if self.access_token and time.time() < self.token_expires_time:
            return self.access_token

        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                self.access_token = data.get("tenant_access_token")
                self.token_expires_time = time.time() + data.get("expire") - 60  # 提前60秒更新
                return self.access_token
            else:
                logger.error(f"获取 tenant_access_token 失败: {data}")
                raise Exception(f"获取 tenant_access_token 失败: {data.get('msg')}")
        except Exception as e:
            logger.error(f"获取 tenant_access_token 异常: {str(e)}")
            raise

    def send_message(self, title: str, content: List[Dict[str, Any]], summary: Dict[str, Any] = None) -> bool:
        """发送消息卡片
        
        Args:
            title: 卡片标题
            content: 卡片内容列表
            summary: 统计摘要信息
        """
        try:
            access_token = self._get_tenant_access_token()
            url = f"{self.base_url}/im/v1/messages?receive_id_type=chat_id"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            elements = []
            
            # 添加统计摘要
            if summary:
                elements.append({
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
                })
                elements.append({"tag": "hr"})

            # 添加内容
            for item in content:
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{item['site']}**\n发现 {len(item['urls'])} 个新增URL："
                    }
                })
                
                # 添加URL列表
                url_content = "\n".join([f"• {url}" for url in item['urls'][:10]])
                if len(item['urls']) > 10:
                    url_content += f"\n...等共 {len(item['urls'])} 个URL"
                
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": url_content
                    }
                })
                elements.append({"tag": "hr"})

            message = {
                "receive_id": self.chat_id,
                "msg_type": "interactive",
                "content": json.dumps({
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
                    "elements": elements
                })
            }

            response = requests.post(url, headers=headers, json=message)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                logger.info("消息发送成功")
                return True
            else:
                logger.error(f"消息发送失败: {data}")
                return False

        except Exception as e:
            logger.error(f"发送消息异常: {str(e)}")
            return False

def create_feishu_bot(config_path: str = "config.json") -> FeishuBot:
    """创建飞书机器人实例"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        feishu_config = config.get('feishu', {})
        if not all([feishu_config.get('app_id'), feishu_config.get('app_secret'), feishu_config.get('chat_id')]):
            logger.error("飞书配置不完整")
            return None
            
        return FeishuBot(
            app_id=feishu_config['app_id'],
            app_secret=feishu_config['app_secret'],
            chat_id=feishu_config['chat_id']
        )
    except Exception as e:
        logger.error(f"创建飞书机器人失败: {str(e)}")
        return None
