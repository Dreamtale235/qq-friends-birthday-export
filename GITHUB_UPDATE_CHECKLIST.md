# GitHub 更新前检查清单

## 本次建议上传的内容

将 `上传GitHub/` 目录内的内容作为 GitHub 仓库根目录上传。

建议包含：

- `*.py` 源码文件
- `README.md`
- `requirements.txt`
- `.gitignore`
- `.gitattributes`
- `LICENSE`
- `CHANGELOG.md`
- `QQ好友生日导出.spec`
- `QQ好友生日导出工具_使用说明.md`
- `tests/`

不要上传：

- `sessions/`
- `data/`
- `logs/`
- `__pycache__/`
- `.pytest_cache/`
- `build/`
- `dist/`
- `browsers/`
- `.env` 或任何账号、Cookie、会话文件

## 上传前自检

```bash
python -m py_compile *.py
python -m unittest discover -s tests
```

## 推荐提交信息

```text
chore: prepare qq birthday exporter for GitHub update
```

## GitHub 仓库描述建议

```text
基于 Playwright 的 QQ 邮箱好友生日导出工具，支持扫码登录、12 个月自动爬取、CSV 导出和 GUI/CLI 双模式。
```

## Release Notes 建议

```text
v0.3.0

- 优化浏览器资源关闭和会话检测流程
- 修复 2 月 29 日生日在非闰年的日期计算问题
- 同一天多次导出时自动避让同名 CSV
- 新增本地自检测试
- 完善 GitHub 忽略规则、更新日志和使用说明
```
