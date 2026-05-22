# QQ 好友生日导出工具

基于 Playwright 的 QQ 邮箱好友生日自动爬取工具，支持 GUI 和命令行两种模式，一键导出 CSV。

## 功能

- **扫码登录**：通过 QQ 手机版扫描二维码登录 QQ 邮箱，会话自动保存，一次登录多次使用
- **自动爬取**：遍历 QQ 邮箱日历 1-12 月，提取所有好友生日信息
- **CSV 导出**：按日期排序导出 UTF-8 with BOM 编码的 CSV（含星座、距今天数）
- **双模式**：Tkinter GUI（进度条 + 日志窗口）和 CLI 命令行
- **可打包**：支持 PyInstaller 打包为独立 .exe

## 快速开始

### 环境要求

- Python 3.10+（安装时勾选 tcl/tk）
- Windows / macOS / Linux

### 安装

```bash
pip install -r requirements.txt
playwright install chromium
```

### 运行

```bash
# GUI 模式（图形界面）
python main.py

# CLI 模式（命令行）
python main.py --cli
```

首次运行会打开浏览器窗口，用**手机 QQ 扫描二维码**登录。登录成功后会话自动保存，下次无需重复扫码。

### 打包为 EXE

```bash
pip install pyinstaller
pyinstaller QQ好友生日导出.spec
```

## 项目结构

```
├── main.py              # 入口（Chromium 检测 + 模式路由）
├── pipeline.py           # 工作流编排（登录 → 爬取 → 导出）
├── auth.py               # QQ 邮箱登录 & 会话管理
├── crawler.py            # 日历 DOM 解析 & 数据提取
├── exporter.py           # CSV 导出
├── gui.py                # Tkinter GUI
├── run_cli.py            # CLI 命令行
├── config.py             # 全局配置
├── logger.py             # 日志系统
├── utils.py              # 工具函数（星座、日期计算）
├── requirements.txt      # Python 依赖
├── QQ好友生日导出.spec    # PyInstaller 打包配置
├── data/                 # 输出目录（CSV、调试 HTML/截图）
├── sessions/             # 浏览器会话（自动保存，已 gitignore）
└── logs/                 # 运行日志
```

## 常见问题

### 登录相关
- **扫码超时**：默认等待 3 分钟，超时后重试即可
- **会话过期**：通常有效期几天，过期后需重新扫码
- **账号风控**：频繁登录可能触发验证，需在手机上确认

### 数据源
- **日历为空**：需在 QQ 邮箱「日历 → 日历分类」中勾选「好友生日」
- **好友未公开生日**：仅已填写生日且设为可见的好友会显示
- **好友数量上限**：QQ 邮箱生日日历有显示数量限制

### 页面结构变化
- 本工具依赖 QQ 邮箱日历的 CSS 选择器定位数据。若 QQ 邮箱前端改版，需修改 `crawler.py` 中的选择器
- 调试方法：设置 `config.py` 中 `DEBUG = True`，运行后查看 `data/month_*.html` 定位实际 DOM 结构

### 数据准确性
- 同一天多个生日时，因日历堆叠可能漏掉个别条目
- 农历/公历混合显示，本工具统一按公历处理
- CSV 中 `birth_year` 字段为空（QQ 邮箱不提供出生年份）

### CSV 乱码
- Excel 直接打开可能中文乱码 → 使用「数据 → 从文本/CSV → UTF-8」导入
- 推荐使用 WPS 或 VS Code 打开

## 技术栈

- [Playwright](https://playwright.dev/python/) — 浏览器自动化
- Tkinter — GUI 框架
- PyInstaller — 打包为独立可执行文件

## License

MIT
