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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        try:
            # 如果是Scratch网站，使用特殊的处理
            if 'scratch.mit.edu' in url:
                # 首先获取主页面
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                # 提取API端点
                base_url = "https://api.scratch.mit.edu"
                if "/explore/projects/all" in url:
                    api_url = f"{base_url}/explore/projects?mode=trending&q=*"
                    api_response = requests.get(api_url, headers=headers, timeout=30)
                    api_response.raise_for_status()
                    
                    # 将API响应转换为HTML格式
                    projects = api_response.json()
                    html_content = '<html><body>'
                    for project in projects:
                        project_url = f"/projects/{project['id']}"
                        html_content += f'<a href="{project_url}">{project.get("title", "Untitled")}</a>'
                    html_content += '</body></html>'
                    return html_content
                
                return response.text
            
            # 其他网站使用普通请求
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"获取内容失败: {url}, 错误: {str(e)}")
            raise

    def parse_sitemap(self, content: str, url: str) -> Set[str]:
        """解析sitemap内容或网页内容，提取URL"""
        try:
            # 如果URL包含 scratch.mit.edu/explore，使用特殊的解析逻辑
            if 'scratch.mit.edu/explore' in url:
                return self.parse_scratch_page(content)
            
            # 常规sitemap解析
            root = etree.fromstring(content.encode())
            urls = set()
            for url in root.xpath("//ns:url/ns:loc/text()",
                                namespaces={'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}):
                urls.add(url)
            return urls
        except etree.XMLSyntaxError:
            # 如果解析XML失败，尝试作为HTML解析
            return self.parse_html_page(content, url)
        except Exception as e:
            logger.error(f"解析内容失败: {str(e)}")
            raise

    def parse_scratch_page(self, content: str) -> Set[str]:
        """解析Scratch项目页面"""
        try:
            html = etree.HTML(content)
            urls = set()
            # 提取项目链接
            for href in html.xpath('//a[contains(@href, "/projects/")]/@href'):
                if '/projects/' in href and not href.endswith('/projects/'):
                    full_url = f"https://scratch.mit.edu{href}"
                    urls.add(full_url)
            return urls
        except Exception as e:
            logger.error(f"解析Scratch页面失败: {str(e)}")
            raise

    def parse_html_page(self, content: str, base_url: str) -> Set[str]:
        """解析普通HTML页面"""
        try:
            html = etree.HTML(content)
            urls = set()
            for href in html.xpath('//a/@href'):
                if href.startswith('http'):
                    urls.add(href)
                elif href.startswith('/'):
                    # 将相对路径转换为绝对路径
                    base = base_url.split('//')[1].split('/')[0]
                    urls.add(f"https://{base}{href}")
            return urls
        except Exception as e:
            logger.error(f"解析HTML页面失败: {str(e)}")
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
        """分析单个sitemap或网页"""
        name = sitemap_config['name']
        url = sitemap_config['url']

        try:
            # 获取新的内容
            content = self.fetch_sitemap(url)
            new_urls = self.parse_sitemap(content, url)
            
            # 获取本地存储的URL
            old_urls = self.load_local_sitemap(name)
            
            # 计算新增的URL
            diff_urls = new_urls - old_urls
            
            if diff_urls:
                logger.info(f"发现 {len(diff_urls)} 个新URL: {name}")
                self.save_diff(name, diff_urls)
            
            # 更新本地存储
            self.save_sitemap(name, new_urls)
            
        except Exception as e:
            logger.error(f"处理 {name} 失败: {str(e)}")

    def run_analysis(self):
        """运行所有sitemap分析"""
        logger.info("开始分析sitemaps...")
        for sitemap in self.config['sitemaps']:
            self.analyse_sitemap(sitemap)
        logger.info("sitemap分析完成")


if __name__ == "__main__":
    analyser = SitemapAnalyser()

    # 设置每天凌晨2点运行
    schedule.every().day.at("02:00").do(analyser.run_analysis)
    logger.info("定时任务已设置：每天凌晨2点自动运行")

    # 首次运行
    logger.info("执行首次分析...")
    analyser.run_analysis()

    # 持续运行调度器
    logger.info("开始定时监控...")
    while True:
        schedule.run_pending()
        time.sleep(60)
