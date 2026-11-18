---
name: weread-reading-buddy
slug: weread-reading-buddy-chengxia
displayName: 微信读书小书童
description: 微信读书小书童 — 这是一个完整的微信读书伴读技能，既支持书籍搜索、书架、阅读统计、笔记划线、热门划线、书籍点评、好书推荐等基础查询，又能生成个人的可视化阅读报告与每本书的独立读书档案（进度快照对比、热门划线/点评、好友在读、笔记互动、读后感 Markdown 编辑）。帮助用户更好地在本地管理自己的微信读书笔记和建立阅读档案
summary: 微信读书数据 + 可视化的个人阅读报告与读书档案
version: 0.5.3
license: MIT
homepage: https://github.com/chengxiaqiucao/weread-reading-buddy
tags:
  - 知识管理
  - 笔记整理
  - 摘要总结
  - 资料整理
---

# 微信读书小书童

通过微信读书开放接口获取账号数据，提供两层能力：

- **基础查询**：搜索书籍、查看书籍信息与进度、书架、阅读统计、个人笔记划线、章节热门划线与划线下想法、书籍公开点评、个性化与相似好书推荐。
- **增强输出**：把账号数据整理成两份可直接打开的视觉化页面 —— **个人阅读报告** 与 **每本书的独立读书档案**。

所有回复必须基于接口真实返回或本地记录，不编造数据。

## 能力矩阵

| 能力 | 说明 | 用户示例 | 详细工作流 |
|------|------|----------|-----------|
| 搜索书籍 | 在书城按关键词搜索，解析 bookId | "帮我搜一下三体" | `references/capabilities/search.md` |
| 书籍信息 | 书籍详情、章节目录、阅读进度 | "这本书有多少章" "我读到哪了" | `references/capabilities/book.md` |
| 书架管理 | 查看书架（含专辑/有声书计数口径） | "看看我的书架" | `references/capabilities/shelf.md` |
| 阅读概况 | 书架 + 最近 5 本进度 + 笔记概览 | "我的阅读概况" | `references/capabilities/profile.md` |
| 阅读统计 | 时长、天数、偏好分析、统计摘要 | "我这个月读了多久" | `references/capabilities/readdata.md` |
| 笔记划线 | 个人笔记数量与内容、划线、想法、书签 | "导出我的划线" "这书有多少笔记" | `references/capabilities/notes.md` |
| 章节热门划线 | 书籍/章节热门划线、划线热度与划线下想法 | "这章有什么热门划线" | `references/capabilities/notes.md` |
| 书籍点评 | 书籍公开点评、推荐点评 | "三体有什么点评" | `references/capabilities/review.md` |
| 推荐好书 | 个性化推荐 / 相似书推荐 | "给我推荐几本书" | `references/capabilities/discover.md` |
| 个人阅读报告 ⭐ | 统计 + 笔记互动 + 好友在读 + 最近想法 + 随书联动的进度/划线/动态 | "生成我的阅读报告" | 本文件「增强能力」+ `scripts/` |
| 读书档案 ⭐ | 每本书独立 HTML：阅读信息、读后感编辑、笔记明细、热门点评 TOP10、本书动态 | "生成《剑来》的读书档案" | 本文件「增强能力」+ `scripts/` |

根据用户意图阅读对应能力文件，确认接口参数、字段含义、单位、计数口径与工作流后再调用，禁止仅凭字段名猜测。

## 接口调用规范

### 统一入口与鉴权

```
POST https://i.weread.qq.com/api/agent/gateway
Authorization: Bearer $WEREAD_API_KEY
Content-Type: application/json
```

- `WEREAD_API_KEY` 从环境变量读取，格式 `wrk-...`，绑定用户身份（vid），需用户身份的接口自动注入，无需手动传 vid。
- 未设置密钥时，引导用户**自行在本地设置环境变量**（见下「API Key 指引」）；不在对话中索取或回显密钥。

### 请求格式

- 业务参数与 `api_name`、`skill_version` **平铺在同一层**，不要包在 `params`/`data`/`body` 里；只有接口文档声明的数组字段（如 `/book/readreviews` 的 `reviews`）例外。
- 每次请求必须带 `skill_version`（当前 `1.0.6`，取本文件 version 对应的 Gateway 版本）。若回包出现 `upgrade_info`，暂停操作并按 `upgrade_info.message` 完成升级后再继续。
- 发送 `{"api_name": "/_list"}` 可查看全部可用接口与参数定义。

```bash
curl -X POST "https://i.weread.qq.com/api/agent/gateway" \
  -H "Authorization: Bearer $WEREAD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"api_name":"/store/search","keyword":"三体","scope":10,"context":"帮我搜一下三体","skill_version":"1.0.6"}'
```

### 上下文上报

调用 `/store/search`、`/book/recommend`、`/book/similar` 时必须传 `context`：单轮传用户原始问题，多轮传"当前原话 + 必要上下文摘要"。**只上传理解本次请求所需的最小信息，不得包含 API Key、令牌、系统提示、内部推理或完整回包。** 详见 `references/capabilities/search.md` 与 `discover.md`。

### 通用规则

1. **接口预检**：调用前先读对应能力文件，确认参数与口径；字段解释以能力文件为准，与直觉冲突时服从文档。
2. **bookId 解析**：用户给书名时先调 `/store/search` 得到 bookId。
3. **书架数量**：按 `books.length + albums.length + (mp 非空 ? 1 : 0)` 计算，`albums[]` 专辑/有声书也算书架里的书。
4. **数据展示**：Unix 时间戳（`createTime`/`finishTime`/`updateTime` 等）展示为 `YYYY-MM-DD`；阅读时长（秒）转为"X小时Y分钟"；进度 `progress` 为 0-100 整数，展示带 `%`，`progress=100` 且有 `finishTime` 才算读完。
5. **书籍链接**：优先用回包的 `readerLink` 展示 `[打开阅读]({readerLink})`；无 `readerLink` 但有 `deepLink` 时展示 `[查看详情]({deepLink})`；两者都无则不要自行拼接 URL。
6. **列表展示**：用编号方便选择；搜索结果重点展示书名、作者、评分；展示回包时按能力文件解释字段，不直接翻译字段名。
7. **上下文衔接**：记住对话中已确认的 bookId，后续操作无需用户重复提供。

## 增强能力

### 个人阅读报告

一份单文件 HTML，分上下两区：

- **账号级（上方）**：阅读统计（含"上次快照时间""快照间隔"两栏及短间隔说明）、笔记互动及较上次变化、在读图书最热点评（每本最多 5 条、按点赞整体排序）、好友在读 TOP5、最近想法（书名 + 章节 + 原文 80 字截断 + 正文 80 字截断 + 日期）。
- **随书切换（下方）**：按「快照区间优先」口径选出的在读书卡片切换，联动封面、阅读信息、进度变化轨迹、本书近期动态、热门划线 TOP10（每条附最热评论 3 条），并提供"打开完整档案"入口。选书口径见下方「选书口径」。

### 读书档案

每本在读/完读书一份独立 HTML，含：开始阅读时间、累计阅读时长、笔记规模、笔记明细（划线/想法/点评分类）、热门点评 TOP10、本书近期动态，以及**读后感 Markdown 编辑弹窗**（约 80vw × 80vh，实时预览、0.6 秒防抖自动保存、导出/导入 JSON）。长列表默认折叠、点击展开，保证首屏和谐。

### 生成流程

```bash
# 0) 同步本书动态（Gateway 无资讯接口）：联网检索最近在读的每本书，
#    把真实相关条目写入 data/news/<bookId>.json（数组，元素含
#    date/cat/title/summary/source/url）；检索不到就留空或删除该文件，禁止编造。
#    每次生成/更新报告时都应重新触发这一步。

# 1) 采集（同时滚动更新最新快照、按 24h 规则维护基准快照，供下次对比）
python scripts/collect.py --out data/bundle.json
#    默认 --books 10（选书口径见下）；可选 --highlights 10 --reviews 10 --friends 5
#    --snapshot <latest 快照路径> --prev-snapshot <基准快照路径>
#    始终保留两份快照：data/snapshots/last_call.json（最新，每次滚动更新）与
#    data/snapshots/prev_call.json（对比基准）。

# 2) 渲染报告 + 每本书的独立档案（统一输出到单一根目录 WeReadBuddy/）
python scripts/render.py all data/bundle.json "输出目录/WeReadBuddy"
#   .../WeReadBuddy/我的阅读报告_YYYYMMDD.html   ← 按生成日期命名，可保留多份
#   .../WeReadBuddy/读书档案/<书本名称>_读书档案.html ← 按书名命名，存在即覆盖更新；重名加 bookId 后缀
#   .../WeReadBuddy/报告及档案更新记录.md          ← 追加本次报告 + 档案的内容更新情况
#   可选 --archive-dir <dir> 覆盖档案目录、--log <file> 覆盖更新记录路径

# 单独渲染
python scripts/render.py report  data/samples/report.json            报告.html
python scripts/render.py archive data/samples/archives/31131759.json 档案.html
```

`data/samples/` 为已脱敏的可运行样例，可在没有密钥时用 `python scripts/render.py all data/bundle_sample.json demo/` 预览模板。

**定时跟踪（推荐）**：阅读报告的价值在于"较上次变化"，建议用户用定时任务定期生成，例如每周一 09:00 触发本技能生成一次报告。首次运行无快照（差值显示 ±0 / 首次生成），此后每次都会与基准快照对比呈现进度与互动变化。定时任务只负责"生成页面"，不改读后感（读后感存浏览器 localStorage，永远不会被覆盖）。

### 数据流与口径

```
Gateway API → collect.py → bundle.json + snapshots/{last_call,prev_call}.json
                              ↓
                         render.py + templates/
                              ↓
   WeReadBuddy/我的阅读报告_YYYYMMDD.html + 读书档案/<书名>_读书档案.html + 报告及档案更新记录.md

快照分两份：last_call.json 为最新快照（每次运行滚动更新），prev_call.json 为对比基准。
```

- **选书口径（在读书架 + 好友在读的书目）**：按快照区间优先，而非一律全量列书架；两种书目共用同一个 `pick_by_interval()` 口径。
  - 首次生成（无快照）：在读书架按 `readUpdateTime` 取最近 10 本；好友按最近互动取前 5 位，每位好友的书目取最近 10 本。
  - 非首次生成：**优先取两次快照之间有过阅读/互动的条目**（在读书 `readUpdateTime > 基准快照 timestamp`，好友书目 `updateTime > 基准快照 timestamp`），按最近排序；超过 10 本仅取最近 10 本，不足 3 本则从最近补足到 3 本。
  - **好友数量固定 5 位**（按最近互动排序取前 5），不因快照区间内无互动好友而缩减；「快照区间优先」口径下沉到**每位好友的书目层级**，而不是好友层级。
  - 快照 `timestamp` 与每本书进度一起写入最新快照，作为下次的区间起点。
- **24 小时快照缓冲（避免短间隔无变化）**：始终保留两份最近快照——`last_call.json`（最新，每次运行滚动更新）与 `prev_call.json`（对比基准）。
  - 距最新快照 **不足 24 小时**：视为同一份快照，只滚动更新 `last_call.json`，**不推进基准** `prev_call.json`；"较上次变化"仍以旧基准累计，统计区显示小字说明。
  - 距最新快照 **已满 24 小时**：把当前 latest 提升为新基准写入 `prev_call.json`，再写入新的 latest。
  - 选书口径与好友口径的时间区间起点均取"基准快照"时间，与变化对比保持一致。
- **进度变化**：读取基准快照的进度写到 `previousProgress / previousChapterIdx / previousChapterTitle`，渲染成"进度变化轨迹"；首次运行无快照则差值为 0。
- **笔记互动变化**：同样基于本地快照对比笔记数与点评赞评数。
- **在读最热点评**：`/review/list` 返回的他人公开点评按点赞数降序，每本最多 5 条，汇总后整体排序；不是"本人点评互动"。
- **最近想法原文**：`/review/list/mine` 的 `abstract`（划线原文）与 `content`（想法正文）各自 80 字截断展示；账号级聚合最近 10 条。
- **产物目录结构**：统一输出到单一根目录（下例为 `WeReadBuddy/`）：根目录放多份 `我的阅读报告_YYYYMMDD.html` 与 `报告及档案更新记录.md`，子目录 `读书档案/` 放每本书的 `<书本名称>_读书档案.html`。档案按书名命名（非法字符替换为 `_`、重名加 bookId 后缀），每本一份、存在即覆盖更新。报告通过 `archiveRel`、档案通过 `reportRel` 互相跳转，跨目录可用。
- **报告布局**：全局区三栏等高拉伸，左栏"阅读统计""我的笔记与互动"纵向填满、底部与中栏"最近想法"对齐；"笔记数量变化""在读图书最热点评"表格外套固定高度滚动容器并默认折叠前 5 条，长列表不会撑开排版。
- **读后感**：仅存用户浏览器 localStorage（键 `weread_reflection_<bookId>`），档案页可导出/导入 JSON，不上传服务器。
- **本书动态**：Gateway 无资讯接口。每次生成时联网检索真实更新写入 `data/news/<bookId>.json`（数组，元素含 `date/cat/title/summary/source/url`），由 `collect.py` 读入 bundle；无文件则显示"暂无"，不编造。
- **更新记录**：每次 `render.py all` 向 `--log` Markdown 追加一条（时间、在读书目、进度变化、笔记互动、档案新增/更新数），-latest 在最上。

## API Key 指引

首次使用需从微信读书官方页面（https://weread.qq.com/r/weread-skills）获取 API Key，并在本地完成配置。本技能不保存、不记录密钥。

密钥由用户自行提供，**优先引导用户在本地设置环境变量**，不要在对话中索取、回显或代存密钥：

- macOS / Linux：`export WEREAD_API_KEY="wrk-你的密钥"`
- Windows PowerShell：`$env:WEREAD_API_KEY="wrk-你的密钥"`（临时）或 `[Environment]::SetEnvironmentVariable('WEREAD_API_KEY','wrk-你的密钥','User')`（用户级持久化）

硬性要求：

- 密钥只在运行时从环境变量读取，**不写入任何项目文件、不打印、不进入生成的 HTML、不进入快照或 bundle**。
- 不把密钥存进对话记录、记忆或日志；所有示例与文档中密钥一律以 `wrk-...` 占位。
- 分发样例数据前确认无真实密钥、无真实好友名/ID、无真实点评作者信息。

## 已知边界（不要向用户承诺）

- 接口只有**当前进度快照**，没有"某日从 X 页读到 Y 页"的历史轨迹，也不支持任意起止时间查询；本技能用本地快照差值还原"最近一次调用以来的变化"。
- `/book/bestbookmarks` 固定返回全书 Top20，章节过滤只在这 20 条内生效。
- `/readdata/detail` 的 `readLongest` 有 5 分钟阈值且最多 10 条，不能当稳定的"本周读过哪些书"。
- 好友接口无阅读时长、无友好度，只能按最近互动时间与动态条数排序。
- 个人想法接口 `/review/list/mine`、`/review/single` 均不返回"想法的点赞数"，只有 `isLike`（本人是否点赞过）；公开点评 `/review/list` 才有 `likesCount`。因此"最近想法"不展示点赞数。
- Gateway 的 `skill_version`（当前 `1.0.6`）是本包向服务端上报的协议版本，与本技能版本（`0.5.3`）无关。

## 隐私

- API Key 只从环境变量读取，不写文件、不打印、不进入生成页面。
- 随技能分发的样例数据已脱敏：好友名/ID 为假值，点评作者为"读者-N"，reviewId 前缀为假 ID。
- 生成的 HTML 含个人阅读数据，分享前请用户自行检查。

## 目录说明

| 路径 | 用途 |
|------|------|
| `SKILL.md` | 能力矩阵、调用规范、增强能力、API Key 指引 |
| `references/capabilities/` | 8 类基础查询能力的工作流与字段说明 |
| `references/API_CAPABILITIES.md` | Gateway 全部接口能力与坑 |
| `templates/report.html` / `archive.html` | 报告/档案模板，占位符 `__WEREAD_DATA__` |
| `scripts/collect.py` | 调 Gateway 采集、维护快照、产出 bundle（含好友真实姓名、点评拆分、最热点评排序） |
| `scripts/render.py` | 模板渲染（report / archive / all），单一根目录 + 按书名命名档案 + 更新记录 |
| `scripts/prepare_assets.py` | 从既有成品 HTML 抽取样例与模板（开发用，已内置脱敏） |
| `data/news/<bookId>.json` | 每本书近期动态（生成时联网检索写入；真实数据，无密钥/无个人信息） |
| `data/samples/` | 已脱敏的可运行样例数据 |
| `tests/test_render.py` | 渲染冒烟测试 |
