---
name: weread-reading-buddy
description: 微信读书小书童 — 基于 WEREAD_API_KEY 生成个人阅读报告与每本书的独立读书档案 HTML（进度快照对比、热门划线/点评、好友在读、阅读统计、笔记互动、读后感编辑）。当用户要求生成阅读报告、读书档案、查看阅读进度变化、导出阅读笔记或整理在读书目时使用。
version: 0.2.0
---

# 微信读书小书童

仅凭 `WEREAD_API_KEY` 调用微信读书 Gateway，生成两类可直接打开的视觉化页面：

1. **个人阅读报告**：账号级阅读统计、笔记互动、好友在读、最近想法 + 在读书架切换 + 随书联动的进度轨迹、阅读信息、本书动态、热门划线 TOP10（每条附最热评论 3 条）。
2. **读书档案**：每本书一份独立 HTML，含阅读信息（开始阅读时间 / 累计时长）、读后感 Markdown 弹窗编辑器（自动保存 + 导入导出）、笔记明细、热门点评 TOP10、本书动态。

页面为单文件 HTML，无外部依赖；长列表默认折叠，读后感编辑器为 80vw × 80vh 浮层弹窗。

## 前置条件

- Python 3.8+
- 环境变量 `WEREAD_API_KEY`（格式 `wrk-...`）。未设置时脚本会明确报错，不会输出密钥。
- 可选：环境变量 `WEREAD_SELF_NAME`，用于从公开点评中识别本人的点评；不设置则互动明细留空（不伪造数据）。

## 快速使用

```bash
# 1) 采集数据（同时把本次进度/笔记数写入快照，供下次对比）
python scripts/collect.py --out data/bundle.json

# 2) 渲染报告 + 每本书的独立档案
python scripts/render.py all data/bundle.json "输出目录"

# 输出：
#   输出目录/个人阅读报告.html
#   输出目录/读书档案/<书名>_读书档案.html
```

单独渲染：

```bash
python scripts/render.py report  data/samples/report.json            报告.html
python scripts/render.py archive data/samples/archives/31131759.json 档案.html
```

`data/samples/` 内为可运行的样例数据，便于在没有密钥时预览模板效果。

## 数据流

```
Gateway API → collect.py → bundle.json + snapshots/last_call.json
                              ↓
                         render.py + templates/
                              ↓
                    个人阅读报告.html / 读书档案/*.html
```

- **进度变化**：`collect.py` 读取 `data/snapshots/last_call.json` 中的上次进度，写入 `previousProgress / previousChapterIdx / previousChapterTitle`，渲染为“进度变化轨迹”。首次运行没有快照时，前后相同，差值为 0。
- **笔记互动变化**：同样基于快照对比笔记数与点评赞评数。
- **读后感**：只存在用户浏览器 localStorage，键名 `weread_reflection_<bookId>`；档案页提供导出 / 导入 JSON，不上传服务器。
- **本书动态**：Gateway 无网络资讯接口。`collect.py` 会读取 `data/news/<bookId>.json`（数组，元素含 `date/cat/title/summary/source/url`）；没有文件就显示“暂无”，不会编造。

## 目录说明

| 路径 | 用途 |
|------|------|
| `templates/report.html` | 阅读报告模板，数据占位符 `__WEREAD_DATA__` |
| `templates/archive.html` | 读书档案模板，数据占位符 `__WEREAD_DATA__` |
| `scripts/collect.py` | 调 Gateway 采集数据、维护快照、产出 bundle |
| `scripts/render.py` | 模板渲染（report / archive / all） |
| `scripts/prepare_assets.py` | 从既有成品 HTML 抽取样例数据与模板（开发用） |
| `references/API_CAPABILITIES.md` | Gateway 18 个接口的能力与坑 |
| `data/samples/` | 可运行样例数据 |
| `tests/test_render.py` | 渲染冒烟测试 |

## 已知边界（不要向用户承诺）

- 接口只有**当前进度快照**，没有“某日从 X 页读到 Y 页”的历史轨迹，也不支持任意起止时间查询。
- `/book/bestbookmarks` 固定返回全书 Top20，章节过滤只在这 20 条内生效。
- `/readdata/detail` 的 `readLongest` 有 5 分钟阈值且最多 10 条，不能当作稳定的“本周读过哪些书”。
- 好友接口无阅读时长、无友好度，只能按最近互动时间与动态条数排序。
- 个人想法接口 `/review/list/mine`、`/review/single` 均不返回"想法的点赞数"，只有 `isLike`（本人是否点赞过）标记；公开点评 `/review/list` 才有 `likesCount`。因此报告"最近想法"不展示点赞数，只展示书名、章节、正文（80 字截断）与时间。
- Gateway 的 `skill_version` 是 `1.0.5`，与本技能版本 `0.2.0` 无关。

## 隐私

- API Key 只从环境变量读取，不写文件、不打印、不进入生成页面。
- 生成的 HTML 含个人阅读数据，分享前请自行检查。
