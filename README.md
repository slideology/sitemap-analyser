# Sitemap Analyser

这是一个用于分析网站Sitemap变化的工具。它可以定期获取指定网站的Sitemap或网页内容，并与本地存储的版本进行对比，找出新增的URL，并通过飞书机器人发送通知。

## 功能特点

- 支持多个网站的Sitemap监控
- 支持标准XML格式的Sitemap和普通HTML页面
- 支持特殊网站的自定义解析（如Scratch项目页面）
- 每日定时自动检查更新
- 保存新增URL到按日期组织的目录中
- 自动更新本地Sitemap存储
- 通过飞书机器人发送通知
- 详细的日志记录
- GitHub Actions自动化部署

## 安装

1. 克隆项目到本地

```bash
git clone https://github.com/yourusername/sitemap_analyser.git
cd sitemap_analyser
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

## 配置

在`config.json`中配置需要监控的Sitemap和飞书机器人Webhook：

```json
{
    "webhook": {
        "url": "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-token"
    },
    "sitemaps": [
        {
            "url": "https://example.com/sitemap.xml",
            "name": "example.com"
        }
    ]
}
```

### 配置说明

- `webhook.url`: 飞书机器人的Webhook地址
- `sitemaps`: 需要监控的网站列表
  - `url`: Sitemap的URL地址或网页地址
  - `name`: 网站的标识名称（用于生成本地文件名）

## 使用方法

### 本地运行

直接运行主程序：

```bash
python sitemap_analyser.py
```

程序会：
1. 首次运行时立即执行一次分析
2. 之后每天凌晨2点自动运行分析

### GitHub Actions自动运行

项目已配置GitHub Actions工作流，可以自动运行分析任务：

- 每天UTC 18:00（北京时间凌晨2:00）自动运行
- 支持手动触发运行
- 自动提交分析结果到仓库

## 输出说明

- Sitemap文件保存在 `./sitemaps/` 目录，以JSON格式存储
- 新增URL保存在 `./diff/YYYYMMDD/` 目录下，按日期和网站名组织
- 日志会实时输出到控制台
- 如果配置了飞书机器人，会发送通知消息

## 通知功能

当发现新增URL时，程序会通过飞书机器人发送通知：

1. 发送汇总信息，包括总网站数和新增URL数
2. 分别发送每个网站的详细URL列表（每组最多100个URL）

## 目录结构

```
.
├── .github/workflows/    # GitHub Actions工作流配置
│   └── sitemap_analysis.yml
├── config.json           # 配置文件
├── requirements.txt      # 项目依赖
├── sitemap_analyser.py   # 主程序
├── webhook_sender.py     # Webhook发送器
├── feishu_bot.py         # 飞书机器人API
├── sitemaps/             # 本地Sitemap存储目录
└── diff/                 # 差异URL存储目录
    └── YYYYMMDD/         # 按日期组织的差异文件
```

## 项目依赖

- requests: 用于HTTP请求
- schedule: 用于定时任务
- lxml: 用于XML和HTML解析

## 扩展支持

项目支持多种类型的网站：

1. 标准XML格式的Sitemap
2. 普通HTML页面（提取所有链接）
3. 特殊网站的自定义解析（如Scratch项目页面）

如需添加新的网站支持，可以在`sitemap_analyser.py`中扩展相应的解析逻辑。
