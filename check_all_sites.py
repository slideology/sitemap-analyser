#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
检查所有配置网站的压缩和解析情况
"""

import json
import requests
from lxml import etree
import time

# 读取配置
with open('config.json', 'r') as f:
    config = json.load(f)

print("="*80)
print("检查所有配置网站的压缩和解析情况")
print("="*80)

# 统计信息
total = len(config['sitemaps'])
success = 0
failed = []
brotli_issues = []
xml_parse_issues = []
other_issues = []

for idx, site in enumerate(config['sitemaps'], 1):
    name = site['name']
    url = site['url']
    
    print(f"\n[{idx}/{total}] 检查: {name}")
    print(f"  URL: {url}")
    
    try:
        # 测试1: 使用带 Brotli 的 headers
        headers_with_br = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        
        response1 = requests.get(url, headers=headers_with_br, timeout=15)
        content_encoding = response1.headers.get('Content-Encoding', 'none')
        
        print(f"  压缩方式: {content_encoding}")
        
        # 检查是否是 Brotli 压缩
        if content_encoding == 'br':
            # 检查内容是否是乱码
            text = response1.text
            if len(text) > 0:
                # 检查前100个字符是否包含大量不可打印字符
                printable_count = sum(1 for c in text[:100] if c.isprintable() or c in '\n\r\t')
                if printable_count < 50:  # 如果可打印字符少于50%
                    print(f"  ⚠️  警告: Brotli 压缩导致内容乱码!")
                    brotli_issues.append({
                        'name': name,
                        'url': url,
                        'issue': 'Brotli 压缩内容无法解压'
                    })
                    failed.append(name)
                    continue
        
        # 测试2: 使用不带 Accept-Encoding 的 headers (修复后的方式)
        headers_fixed = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }
        
        response2 = requests.get(url, headers=headers_fixed, timeout=15)
        content = response2.text
        
        print(f"  内容长度: {len(content)}")
        
        # 测试3: 尝试解析
        try:
            # 尝试 XML 解析
            root = etree.fromstring(content.encode())
            urls = root.xpath("//ns:url/ns:loc/text()",
                            namespaces={'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'})
            
            if urls:
                print(f"  ✓ XML 解析成功: {len(urls)} 个 URL")
                success += 1
            else:
                # 可能是 sitemap index
                sitemap_urls = root.xpath("//ns:sitemap/ns:loc/text()",
                                        namespaces={'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'})
                if sitemap_urls:
                    print(f"  ✓ Sitemap Index: {len(sitemap_urls)} 个子 sitemap")
                    success += 1
                else:
                    print(f"  ⚠️  XML 解析成功但未找到 URL")
                    xml_parse_issues.append({
                        'name': name,
                        'url': url,
                        'issue': 'XML 格式正确但未找到 URL'
                    })
                    success += 1  # 仍算成功,因为能解析
                    
        except etree.XMLSyntaxError as e:
            # XML 解析失败,尝试 HTML
            print(f"  ℹ️  XML 解析失败,尝试 HTML 解析")
            try:
                # 移除 XML 声明
                if content.strip().startswith('<?xml'):
                    xml_decl_end = content.find('?>')
                    if xml_decl_end != -1:
                        content = content[xml_decl_end + 2:]
                
                html = etree.HTML(content)
                links = html.xpath('//a/@href')
                print(f"  ✓ HTML 解析成功: {len(links)} 个链接")
                success += 1
            except Exception as e2:
                print(f"  ✗ HTML 解析也失败: {str(e2)[:50]}")
                xml_parse_issues.append({
                    'name': name,
                    'url': url,
                    'issue': f'XML 和 HTML 解析都失败: {str(e2)[:50]}'
                })
                failed.append(name)
                
    except requests.exceptions.Timeout:
        print(f"  ✗ 请求超时")
        other_issues.append({
            'name': name,
            'url': url,
            'issue': '请求超时'
        })
        failed.append(name)
    except requests.exceptions.HTTPError as e:
        print(f"  ✗ HTTP 错误: {e.response.status_code}")
        other_issues.append({
            'name': name,
            'url': url,
            'issue': f'HTTP {e.response.status_code}'
        })
        failed.append(name)
    except Exception as e:
        print(f"  ✗ 其他错误: {str(e)[:50]}")
        other_issues.append({
            'name': name,
            'url': url,
            'issue': str(e)[:50]
        })
        failed.append(name)
    
    # 避免请求过快
    time.sleep(0.5)

# 输出总结
print("\n" + "="*80)
print("检查完成 - 总结报告")
print("="*80)
print(f"总计: {total} 个网站")
print(f"成功: {success} 个")
print(f"失败: {len(set(failed))} 个")

if brotli_issues:
    print(f"\n⚠️  发现 {len(brotli_issues)} 个 Brotli 压缩问题:")
    for issue in brotli_issues:
        print(f"  - {issue['name']}: {issue['url']}")

if xml_parse_issues:
    print(f"\n⚠️  发现 {len(xml_parse_issues)} 个解析问题:")
    for issue in xml_parse_issues:
        print(f"  - {issue['name']}: {issue['issue']}")

if other_issues:
    print(f"\n⚠️  发现 {len(other_issues)} 个其他问题:")
    for issue in other_issues:
        print(f"  - {issue['name']}: {issue['issue']}")

if not brotli_issues and not xml_parse_issues and not other_issues:
    print("\n✓ 所有网站都正常!")
