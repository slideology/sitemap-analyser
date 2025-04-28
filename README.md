# Sitemap Analyser

这是一个用于分析网站Sitemap变化的工具。它可以定期获取指定网站的Sitemap，并与本地存储的版本进行对比，找出新增的URL。

## 功能特点

- 支持多个网站的Sitemap监控
- 每日定时自动检查更新
- 保存新增URL到按日期组织的目录中
- 自动更新本地Sitemap存储
- 详细的日志记录

## 安装

1. 克隆项目到本地
2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 配置

在`config.json`中配置需要监控的Sitemap：

```json
{
    "sitemaps": [
        {
            "url": "https://example.com/sitemap.xml",
            "name": "example.com"
        }
    ]
}
```

- `url`: Sitemap的URL地址
- `name`: 网站的标识名称（用于生成本地文件名）

## 使用方法

直接运行主程序：

```bash
python sitemap_analyser.py
```

程序会：
1. 首次运行时立即执行一次分析
2. 之后每天凌晨2点自动运行分析

## 输出说明

- Sitemap文件保存在 `./sitemaps/` 目录
- 新增URL保存在 `./diff/YYYYMMDD/` 目录下
- 日志会实时输出到控制台

## 目录结构

```
.
├── config.json           # 配置文件
├── requirements.txt      # 项目依赖
├── sitemap_analyser.py  # 主程序
├── sitemaps/            # 本地Sitemap存储目录
└── diff/                # 差异URL存储目录
    └── YYYYMMDD/        # 按日期组织的差异文件
```
