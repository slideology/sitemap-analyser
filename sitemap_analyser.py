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
from webhook_sender import create_webhook_sender
from datetime import datetime

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
        """获取sitemap内容，包含重试机制和更好的错误处理"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN,zh;q=0.8',
            # 移除 Accept-Encoding,让 requests 库自动处理压缩(gzip/deflate)
            # 避免服务器返回 Brotli 压缩导致解压失败
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 重试配置
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
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
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                return response.text
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    logger.warning(f"网站 {url} 返回403禁止访问，可能需要特殊处理或该网站不允许爬虫访问")
                    raise requests.exceptions.HTTPError(f"403 Forbidden: {url} 禁止访问")
                elif e.response.status_code == 404:
                    logger.warning(f"网站 {url} 返回404，sitemap可能不存在")
                    raise requests.exceptions.HTTPError(f"404 Not Found: {url} sitemap不存在")
                elif e.response.status_code >= 500:
                    if attempt < max_retries - 1:
                        logger.warning(f"网站 {url} 服务器错误 {e.response.status_code}，{retry_delay}秒后重试 (第{attempt + 1}次)")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"网站 {url} 服务器错误 {e.response.status_code}，重试失败")
                        raise
                else:
                    logger.error(f"获取内容失败: {url}, HTTP错误: {e.response.status_code}")
                    raise
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(f"网站 {url} 请求超时，{retry_delay}秒后重试 (第{attempt + 1}次)")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"网站 {url} 请求超时，重试失败")
                    raise
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    logger.warning(f"网站 {url} 连接错误，{retry_delay}秒后重试 (第{attempt + 1}次)")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"网站 {url} 连接错误，重试失败")
                    raise
            except requests.RequestException as e:
                logger.error(f"获取内容失败: {url}, 错误: {str(e)}")
                raise
        
        # 如果所有重试都失败了
        raise requests.RequestException(f"获取 {url} 失败，已重试 {max_retries} 次")

    def parse_sitemap(self, content: str, url: str) -> Set[str]:
        """解析sitemap内容或网页内容，提取URL"""
        try:
            # 如果URL包含 scratch.mit.edu/explore，使用特殊的解析逻辑
            if 'scratch.mit.edu/explore' in url:
                return self.parse_scratch_page(content)
            
            # 常规sitemap解析
            root = etree.fromstring(content.encode())
            urls = set()
            for loc in root.xpath("//ns:url/ns:loc/text()",
                                namespaces={'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}):
                urls.add(loc)
            return urls
        except etree.XMLSyntaxError:
            # 如果解析XML失败，尝试作为HTML解析
            logger.warning(f"XML解析失败,尝试作为HTML解析: {url}")
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
            # 修复: 移除 XML 声明,避免 etree.HTML 解析失败
            # 如果内容以 XML 声明开头,移除它
            if content.strip().startswith('<?xml'):
                # 找到 XML 声明的结束位置
                xml_decl_end = content.find('?>')
                if xml_decl_end != -1:
                    content = content[xml_decl_end + 2:]
                    logger.info("已移除 XML 声明,继续 HTML 解析")
            
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
        
        # 创建 Webhook 发送器
        webhook_sender = create_webhook_sender(self.config_path)
        
        # 收集所有分析结果
        analysis_results = []
        total_new_urls = 0
        successful_sites = 0
        failed_sites = []
        
        for sitemap in self.config['sitemaps']:
            site_name = sitemap['name']
            site_url = sitemap['url']
            
            try:
                logger.info(f"正在分析: {site_name} ({site_url})")
                
                # 获取新的内容
                content = self.fetch_sitemap(site_url)
                new_urls = self.parse_sitemap(content, site_url)
                
                # 获取本地存储的URL
                old_urls = self.load_local_sitemap(site_name)
                
                # 计算新增的URL
                diff_urls = new_urls - old_urls
                
                if diff_urls:
                    logger.info(f"发现 {len(diff_urls)} 个新URL: {site_name}")
                    self.save_diff(site_name, diff_urls)
                    total_new_urls += len(diff_urls)
                    
                    # 添加到分析结果
                    analysis_results.append({
                        'site': site_name,
                        'urls': list(diff_urls)
                    })
                else:
                    logger.info(f"没有发现新URL: {site_name}")
                
                # 更新本地存储
                self.save_sitemap(site_name, new_urls)
                successful_sites += 1
                
            except requests.exceptions.HTTPError as e:
                if "403 Forbidden" in str(e):
                    logger.warning(f"网站 {site_name} 禁止访问sitemap，跳过此网站")
                    failed_sites.append({
                        'site': site_name,
                        'error': '403 禁止访问',
                        'url': site_url
                    })
                elif "404 Not Found" in str(e):
                    logger.warning(f"网站 {site_name} 的sitemap不存在，跳过此网站")
                    failed_sites.append({
                        'site': site_name,
                        'error': '404 sitemap不存在',
                        'url': site_url
                    })
                else:
                    logger.error(f"处理 {site_name} 时发生HTTP错误: {str(e)}")
                    failed_sites.append({
                        'site': site_name,
                        'error': f'HTTP错误: {str(e)}',
                        'url': site_url
                    })
            except requests.exceptions.Timeout:
                logger.error(f"网站 {site_name} 请求超时，跳过此网站")
                failed_sites.append({
                    'site': site_name,
                    'error': '请求超时',
                    'url': site_url
                })
            except requests.exceptions.ConnectionError:
                logger.error(f"无法连接到网站 {site_name}，跳过此网站")
                failed_sites.append({
                    'site': site_name,
                    'error': '连接错误',
                    'url': site_url
                })
            except Exception as e:
                logger.error(f"处理 {site_name} 时发生未知错误: {str(e)}")
                failed_sites.append({
                    'site': site_name,
                    'error': f'未知错误: {str(e)}',
                    'url': site_url
                })
        
        # 输出分析统计
        total_sites = len(self.config['sitemaps'])
        logger.info(f"分析完成 - 总网站数: {total_sites}, 成功: {successful_sites}, 失败: {len(failed_sites)}, 新增URL总数: {total_new_urls}")
        
        # 如果有失败的网站，记录详细信息
        if failed_sites:
            logger.warning("以下网站分析失败:")
            for failed in failed_sites:
                logger.warning(f"  - {failed['site']}: {failed['error']} ({failed['url']})")
        
        # 如果有新的URL，发送webhook通知
        if analysis_results and webhook_sender:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            title = f"Sitemap分析报告 - {current_time}"
            
            summary = {
                'total_sites': total_sites,
                'successful_sites': successful_sites,
                'failed_sites': len(failed_sites),
                'total_new_urls': total_new_urls
            }
            
            # 发送汇总信息
            webhook_sender.send_summary(title, summary)
            
            # 分别发送每个网站的详细信息
            for item in analysis_results:
                webhook_sender.send_site_details(item['site'], item['urls'])
        
        logger.info("sitemap分析完成")


if __name__ == "__main__":
    analyser = SitemapAnalyser()

    # 检测是否在 GitHub Actions CI 环境中运行
    # 在 CI 环境中，只运行一次分析后退出，不进入无限循环
    is_ci = os.environ.get("GITHUB_ACTIONS") == "true"

    if is_ci:
        # CI 环境：只执行一次分析，完成后退出
        logger.info("检测到 GitHub Actions 环境，执行单次分析...")
        analyser.run_analysis()
        logger.info("CI 单次分析完成，程序退出。")
    else:
        # 本地环境：设置定时任务，每小时运行一次
        schedule.every().hour.do(analyser.run_analysis)
        logger.info("定时任务已设置：每小时自动运行")

        # 首次立即运行
        logger.info("执行首次分析...")
        analyser.run_analysis()

        # 持续运行调度器（仅本地使用）
        logger.info("开始定时监控...")
        while True:
            schedule.run_pending()
            time.sleep(60)
