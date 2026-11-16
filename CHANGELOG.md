# Changelog

## 未发布修复 — 2026-11-16

- 样例数据好友脱敏：`data/samples/report.json` 的 `friends[].name` 与档案点评作者中的真实姓名统一替换为 `好友-1`～`好友-5`。`scripts/prepare_assets.py` 新增 `build_friend_aliases/apply_aliases`，重跑抽取时自动脱敏，真名不再回流。
- `prepare_assets.py` 固化 `day()` 字符串日期兼容修复，重生成模板不再回退 Invalid Date 问题。
- 修复 `templates/report.html` 与 `templates/archive.html` 的 `day()`：`archive.span.first/last` 为 `YYYY-MM-DD` 字符串，此前被当作时间戳解析导致"阅读活跃跨度"显示 Invalid Date；现兼容字符串与时间戳两种格式。

## V0.1.0 — 2026-11-16

首个版本，从阅读报告试跑页面固化为可复用技能。

- 新增 `templates/report.html` 与 `templates/archive.html`，与数据解耦，使用 `__WEREAD_DATA__` 占位符。
- 新增 `scripts/collect.py`：Gateway 采集、本地快照对比、产出 bundle。
- 新增 `scripts/render.py`：支持 `report` / `archive` / `all` 三种渲染模式。
- 新增 `scripts/prepare_assets.py`：从既有 HTML 抽取样例数据与模板（开发用）。
- 页面内容精简：移除接口说明、数据说明、口径说明与“账号全局/随书切换”等元信息横幅。
- 长列表默认折叠并支持展开；读后感改为约 80vw × 80vh 浮层 Markdown 编辑器，自动保存。
- 新增 `data/samples/` 样例数据与 `tests/test_render.py` 冒烟测试。
- 建立 Git 版本管理，初始标签 `v0.1.0`。
