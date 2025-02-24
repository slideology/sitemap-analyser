#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import schedule
import time
from datetime import datetime
from lxml import etree
from typing import List, Dict, Set
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SitemapAnalyser:
    def __init__(self, config_path: str = "config.json"):
        """初始化Sitemap分析器"""
        self.config_path = config_path
        self.sitemaps_dir = "sitemaps"
        self.diff_dir = "diff"
        self.load_config()
        self.ensure_directories()

    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            logger.error(f"配置文件 {self.config_path} 不存在")
            raise
        except json.JSONDecodeError:
            logger.error(f"配置文件 {self.config_path} 格式错误")
            raise

    def ensure_directories(self):
        """确保必要的目录存在"""
        os.makedirs(self.sitemaps_dir, exist_ok=True)
        os.makedirs(self.diff_dir, exist_ok=True)

    def fetch_sitemap(self, url: str) -> str:
        """获取sitemap内容"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"获取sitemap失败: {url}, 错误: {str(e)}")
            raise

    def parse_sitemap(self, content: str) -> Set[str]:
        """解析sitemap内容，提取URL"""
        try:
            root = etree.fromstring(content.encode())
            urls = set()
            for url in root.xpath("//ns:url/ns:loc/text()", 
                                namespaces={'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}):
                urls.add(url)
            return urls
        except Exception as e:
            logger.error(f"解析sitemap失败: {str(e)}")
            raise

    def save_sitemap(self, name: str, urls: Set[str]):
        """保存sitemap到本地"""
        filepath = os.path.join(self.sitemaps_dir, f"{name}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(list(urls), f, indent=2, ensure_ascii=False)

    def load_local_sitemap(self, name: str) -> Set[str]:
        """加载本地sitemap"""
        filepath = os.path.join(self.sitemaps_dir, f"{name}.json")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except FileNotFoundError:
            return set()

    def save_diff(self, name: str, diff_urls: Set[str]):
        """保存差异URL到指定目录"""
        today = datetime.now().strftime("%Y%m%d")
        diff_dir = os.path.join(self.diff_dir, today)
        os.makedirs(diff_dir, exist_ok=True)
        
        filepath = os.path.join(diff_dir, f"{name}.urls.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(list(diff_urls), f, indent=2, ensure_ascii=False)

    def analyse_sitemap(self, sitemap_config: Dict):
        """分析单个sitemap"""
        name = sitemap_config['name']
        url = sitemap_config['url']
        
        try:
            # 获取并解析新的sitemap
            content = self.fetch_sitemap(url)
            new_urls = self.parse_sitemap(content)
            
            # 加载本地sitemap
            local_urls = self.load_local_sitemap(name)
            
            # 如果本地没有存储，直接保存并返回
            if not local_urls:
                logger.info(f"首次获取 {name} 的sitemap")
                self.save_sitemap(name, new_urls)
                return
            
            # 计算新增的URL
            diff_urls = new_urls - local_urls
            
            if diff_urls:
                logger.info(f"发现 {name} 有 {len(diff_urls)} 个新增URL")
                self.save_diff(name, diff_urls)
            else:
                logger.info(f"{name} 没有新增URL")
            
            # 更新本地sitemap
            self.save_sitemap(name, new_urls)
            
        except Exception as e:
            logger.error(f"处理 {name} 的sitemap时发生错误: {str(e)}")

    def run_analysis(self):
        """运行所有sitemap分析"""
        logger.info("开始分析sitemaps...")
        for sitemap in self.config['sitemaps']:
            self.analyse_sitemap(sitemap)
        logger.info("sitemap分析完成")

def main():
    analyser = SitemapAnalyser()
    
    # 设置每天运行的时间（例如每天凌晨2点）
    schedule.every().day.at("02:00").do(analyser.run_analysis)
    
    # 首次运行
    analyser.run_analysis()
    
    # 持续运行调度器
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main() 