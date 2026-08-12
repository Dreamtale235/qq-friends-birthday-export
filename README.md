# QQ 好友生日导出工具

> **维护模式：** v0.4.0 是最后一个功能版本。后续仅考虑关键安全修复和 QQ 邮箱页面兼容性修复，不再扩展新功能。

这是一个本地运行的个人数据迁移工具：通过 Playwright 打开 QQ 邮箱好友生日日历，将可见的好友生日同时导出为 CSV 和可导入日历应用的 ICS。

本项目不是腾讯官方产品，也未获得腾讯授权。自动化访问可能受到腾讯服务条款、账号风控和页面改版影响；请仅处理你有权访问的数据，并自行判断使用风险。本工具不提供验证码绕过、风控规避或批量账号能力。

## 功能

- 扫码登录 QQ 邮箱，遍历 1–12 月好友生日日历
- 同时导出 UTF-8 with BOM CSV 和标准 iCalendar（ICS）
- ICS 创建每年重复的全天事件，默认提前 7 天和 1 天提醒
- GUI 与 CLI 两种模式
- 登录状态默认不保存；用户明确选择后才写入本机
- 同名文件自动避让，任何月份失败时不生成不完整备份

## 兼容性

- Python 3.10+
- Windows 10/11 已验证
- macOS 和 Linux 为尽力支持，未进行完整桌面环境测试

本工具依赖 QQ 邮箱当前网页结构。页面结构变化可能导致日历入口、月份切换或生日解析失效。

## 安装

```bash
pip install -r requirements.txt
playwright install chromium
```

Playwright Chromium 约 150 MB，需要稳定网络。

## 使用

### GUI

```bash
python main.py
```

点击“开始导出”后使用手机 QQ 扫码。默认仅在本次浏览器会话中登录；只有主动勾选“记住登录状态”时，程序才会把登录状态保存到 `sessions/state.json`。

### CLI

```bash
# 默认不保存登录状态
python main.py --cli

# 明确允许保存并复用登录状态
python main.py --cli --remember-session

# 删除本工具保存的登录状态，不需要启动浏览器
python main.py --clear-session
```

## 导出文件

成功后会在 `data/` 生成一对同名文件：

```text
qq_friends_birthdays_YYYY-MM-DD.csv
qq_friends_birthdays_YYYY-MM-DD.ics
```

重复导出会增加 `_2`、`_3` 等序号，不覆盖已有文件。

- CSV 适合核对、整理和二次处理。
- ICS 可导入 Apple 日历、Google 日历、Outlook 等支持 iCalendar 的应用。
- 由于 QQ 邮箱不提供出生年份，ICS 使用下一次生日作为首次事件并每年重复。
- `02-29` 在 ICS 中固定于每年 2 月 28 日提醒，事件说明保留原始日期。
- 不同日历客户端可能调整或忽略导入事件自带的提醒，请在导入后抽查。

## 隐私与安全

- `sessions/state.json` 可能包含可恢复 QQ 邮箱登录状态的 Cookie 或令牌，敏感程度接近已登录浏览器。
- `data/` 包含好友昵称、生日等个人信息；`logs/` 可能包含本机路径和错误上下文。
- `.gitignore` 已排除会话、数据、日志、缓存和构建产物，但这不等于磁盘加密。
- 不要上传或分享 `sessions/`、`data/`、`logs/` 的内容；提交 issue 前先清理敏感信息。
- 共用电脑使用完毕后，通过 GUI 的“清除登录状态”或 `python main.py --clear-session` 删除会话文件。
- 如安全软件告警，请核对源码、下载来源和隔离记录；不要为了运行本工具关闭系统防护。

## 数据完整性

只有 QQ 邮箱实际显示、好友已经公开的生日才能被导出。以下情况可能造成缺失或差异：

- 未在 QQ 邮箱日历中启用“好友生日”分类
- QQ 邮箱限制显示数量或好友没有公开生日
- 同一天事件堆叠、月末和月初填充格变化
- 农历与公历混合显示；本工具按页面显示的公历月日处理
- QQ 邮箱页面结构或 CSS 类名发生变化

程序会在检测到日历未加载或某个月份处理异常时停止写出文件，以避免把部分结果误认为完整备份。即使导出成功，也建议抽查几个已知生日。

## 故障排查

- **扫码超时或账号验证：** 在手机 QQ 完成腾讯显示的验证后重试，避免频繁登录。
- **未找到日历：** 确认 QQ 邮箱中能手动打开好友生日日历；页面可能已经改版。
- **需要调试页面：** 将 `config.py` 中 `DEBUG` 临时设为 `True`，运行后检查 `data/month_*.html` 和截图；完成后恢复为 `False` 并保护其中的个人数据。
- **CSV 乱码：** 在 Excel 中使用“数据 → 从文本/CSV”并选择 UTF-8，或使用支持 UTF-8 BOM 的软件。

## 自检

```bash
python -m compileall -q .
python -m unittest discover -s tests -v
```

自动测试覆盖日期计算、CSV/ICS、会话策略和流水线失败路径，不会登录或访问 QQ 邮箱。核心 DOM 选择器仍需要使用者在自己的账号环境中验证。

## 打包说明

仓库保留 PyInstaller 配置，但 v0.4.0 只发布源码，不提供未经签名和真实账号验证的 EXE。自行打包：

```bash
pip install pyinstaller
pyinstaller QQ好友生日导出.spec
```

打包结果仍可能需要单独安装 Playwright Chromium，并可能被安全软件额外检查。

## License

MIT，详见 [LICENSE](LICENSE)。
