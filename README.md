# 微信读书助手（wechat-reading-assistant）

把微信读书账号数据变成两份可读、可分享的视觉化页面：**个人阅读报告** 与 **每本书的独立读书档案**。

当前版本：**V0.1.0** · 目标：迭代后发布为公开技能供他人调用。

## 它能做什么

- 读取书架与阅读进度，用本地快照对比出“上次 → 本次”的变化，而不是假装接口能给出历史轨迹。
- 展示账号级阅读统计、笔记互动、好友在读、最近想法。
- 切换书架卡片时，书封面、进度、读书档案入口、进度轨迹、阅读信息、本书动态、热门划线全部联动。
- 热门划线 TOP10，每条附按点赞数排序的最热评论 3 条；全书热门点评 TOP10。
- 每本书一份独立读书档案：开始阅读时间、累计阅读时长、读后感 Markdown 弹窗编辑器（自动保存 / 导出 / 导入）、划线与想法明细。
- 长列表默认折叠，点击展开，保证首屏和谐。

## 30 秒体验（无需密钥）

```bash
python scripts/render.py all data/bundle_sample.json demo/
```

打开 `demo/个人阅读报告.html`，点击书架卡片切换书目，点击“打开完整档案 →”。

## 真实数据运行

```bash
export WEREAD_API_KEY="wrk-你的密钥"     # Windows PowerShell: $env:WEREAD_API_KEY="wrk-..."
python scripts/collect.py --out data/bundle.json
python scripts/render.py all data/bundle.json output/
```

可选：`--books 3 --highlights 10 --reviews 10 --friends 5` 控制数量。

`data/news/<bookId>.json` 可放该书近期动态数组；没有就留空，页面如实显示“暂无”。

## 测试

```bash
python -m unittest discover -s tests -v
```

## 发布前检查清单

- [ ] 用真实 API Key 跑通 `collect.py` + `render.py all`。
- [ ] 检查生成页不包含密钥、不含他人隐私数据。
- [ ] 确认 README 与 SKILL.md 的示例路径在全新环境可用。
- [ ] 更新 CHANGELOG 与 VERSION，打 Git tag。
- [ ] 若随技能分发样例数据，确认已脱敏。

## 设计取舍

见 `SKILL.md` 的“已知边界”。简言之：接口给的是快照和聚合值，本技能用**本地快照差值**还原“最近一次调用以来的变化”，不伪造逐次阅读轨迹。
