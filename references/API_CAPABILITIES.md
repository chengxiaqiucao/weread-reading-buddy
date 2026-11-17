# 微信读书 Gateway 接口能力清单

> 适用前提：新 skill 不依赖原微信读书 Skill，仅凭 `WEREAD_API_KEY` 直接调用 gateway。  
> 资料来源：`/_list` 接口返回的完整定义（18 个接口）+ 真实调用抽查（2026-11-16）。  
> 本清单只描述"接口能提供什么数据"，不含任何二次开发实现。

---

## 一、调用约定

**统一入口**

```
POST https://i.weread.qq.com/api/agent/gateway
Authorization: Bearer $WEREAD_API_KEY
Content-Type: application/json
```

**请求体格式**：`api_name` 指定接口，业务参数与 `skill_version` **平铺在同一层**。

```bash
curl -X POST "https://i.weread.qq.com/api/agent/gateway" \
  -H "Authorization: Bearer $WEREAD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"api_name":"/store/search","keyword":"三体","scope":10,"count":3,"skill_version":"1.0.6"}'
```

- **禁止**把业务参数包在 `params`/`data` 内，否则参数不会被转发，表现为分页失效。
- `skill_version` 每次必带；若回包出现 `upgrade_info`，须按其 `message` 升级后再重试。
- `need_login=true` 的接口由 API Key 自动注入用户身份（vid），无需手动传 vid。
- 响应为 JSON，成功时通常不返回 `errcode` 字段；失败时 `errcode` 非 0。

**分页三种模式**

| 接口                                 | 分页参数                                                     |
| ---------------------------------- | -------------------------------------------------------- |
| `/user/notebooks`                  | `count` + `lastSort`（游标，取上页最后一项 `sort`），不支持 offset/limit |
| `/review/list`、`/review/list/mine` | `count` + `maxIdx`/`synckey`                             |
| `/book/readreviews`                | `reviews[]` 数组内每项带 `range`/`count`/`maxIdx`/`synckey`    |
| `/store/search`                    | `maxIdx` + `count`（默认 15）                                |

---

## 二、接口总览（18 个）

| 端点                         | 功能                      | 需登录 |
| -------------------------- | ----------------------- | :-: |
| `/store/search`            | 搜索书籍/作者/书单/听书/公众号/文章/全文 |  是  |
| `/book/info`               | 书籍基本信息                  |  否  |
| `/book/chapterinfo`        | 章节目录                    |  否  |
| `/book/getprogress`        | 单本书当前阅读进度               |  是  |
| `/shelf/sync`              | 书架列表（含听书/讲书）            |  是  |
| `/user/notebooks`          | 有笔记的书籍概览                |  是  |
| `/book/bookmarklist`       | 单本书的个人划线（不含书签内容）        |  是  |
| `/review/list/mine`        | 单本书的个人想法/笔记             |  是  |
| `/book/bestbookmarks`      | 全书/章节热门划线（含原文+人数，Top20） |  是  |
| `/book/underlines`         | 章节划线热度统计（人数/得分，无文本）     |  是  |
| `/book/readreviews`        | 指定划线范围下的想法/评论           |  是  |
| `/review/list`             | 书籍公开点评                  |  是  |
| `/review/single`           | 单条想法/评论详情（含评论/点赞）       |  是  |
| `/readdata/detail`         | 阅读统计（周/月/年/总）           |  是  |
| `/book/recommend`          | 个性化推荐书籍                 |  是  |
| `/book/similar`            | 相似书籍推荐                  |  是  |
| `/discover/interact/type3` | 发现页好友在读动态               |  是  |
| `/page/submit`             | 上传自定义 HTML 页面           |  是  |

---

## 三、接口详情

### A. 搜索与发现

#### `/store/search` — 搜索

- **参数**：`keyword`*`string`；`scope` `int`（0全部/10电子书/16网文/14听书/6作者/12全文/13书单/2公众号/4文章，默认10）；`maxIdx` `int`；`count` `int`
- **返回**：`sid`、`hasMore`、`results[]`
- **真实结构**：`results[].books[].bookInfo.{bookId,title,author,cover,newRating,newRatingCount,readerLink,deepLink}`
- **示例**：搜书并取 bookId
  ```bash
  -d '{"api_name":"/store/search","keyword":"三体","scope":10,"count":3,"skill_version":"1.0.6"}'
  ```
  实测"三体"返回 `results[0].books[0].bookInfo.bookId = "695233"`（三体全集）
- **场景**：所有需要"书名 → bookId"转换的流程入口。
- **注意**：bookId 既可能是数字串（如 `695233`），也可能是 `CB_xxx` 形式（外文书），都作为 string 传递。

#### `/book/recommend` — 为你推荐

- **参数**：`count`（默认12）、`maxIdx`（默认0）
- **返回**：`books[]`
- **示例**：
  ```bash
  -d '{"api_name":"/book/recommend","count":12,"skill_version":"1.0.6"}'
  ```

#### `/book/similar` — 相似书推荐

- **参数**：`bookId`*、`count`（默认12）、`maxIdx`、`sessionId`（首次不传，翻页用回包值）
- **返回**：`booksimilar[]`
- **示例**：
  ```bash
  -d '{"api_name":"/book/similar","bookId":"31131759","count":12,"skill_version":"1.0.6"}'
  ```

#### `/discover/interact/type3` — 好友在读动态

- **参数**：`count`（默认20）、`maxIdx`（传上页 `nextMaxIdx`）、`synckey`（刷新时传）
- **返回**：`synckey`、`count`、`hasMore`、`nextMaxIdx`、`items[]`
- **场景**：社交化推荐、"朋友在读什么"。

---

### B. 书籍信息与进度

#### `/book/info` — 书籍详情

- **参数**：`bookId`*
- **返回**：`title`、`author`、`translator`、`cover`、`intro`、`category`、`publisher`、`publishTime`、`isbn`、`wordCount`、`newRating`、`newRatingCount`、`newRatingDetail`、`readerLink`、`deepLink`
- **示例**：


  ```bash
  -d '{"api_name":"/book/info","bookId":"31131759","skill_version":"1.0.6"}'
  ```
- **注意**：`newRating` 为百分制（如 930 = 9.3 分）。

#### `/book/chapterinfo` — 章节目录

- **参数**：`bookId`*
- **返回**：`chapterUpdateTime`、`chapters[].{chapterUid,chapterIdx,title,wordCount,level,paid,isMPChapter,anchors}`
- **示例**：
  ```bash
  -d '{"api_name":"/book/chapterinfo","bookId":"31131759","skill_version":"1.0.6"}'
  ```
  实测《剑来》共 643 章，`chapterUid=1592` 对应 idx=598。
- **场景**：把 chapterUid 映射为章节序号/标题，是所有章节级接口的定位基础。

#### `/book/getprogress` — 当前阅读进度

- **参数**：`bookId`*
- **返回**：`book.{chapterUid,chapterOffset,progress,updateTime,recordReadingTime,finishTime,isStartReading}`、`timestamp`
- **示例**：
  ```bash
  -d '{"api_name":"/book/getprogress","bookId":"31131759","skill_version":"1.0.6"}'
  ```
  实测《剑来》：`chapterUid=1592, chapterOffset=25179, progress=94, updateTime=1794763127`
- **关键注意**：
  - `progress` 是 **0-100 整数**（1 表示 1%，不是 100%）；100 才代表读完。
  - 这是**当前快照**，不是历史轨迹。接口不提供"某日从哪页读到哪页"的逐次记录。
  - `recordReadingTime` 实测返回 0，可能不稳定，不宜作为主口径。

---

### C. 书架与个人笔记

#### `/shelf/sync` — 书架

- **参数**：无
- **返回**：`books[]`、`albums[]`（有声书/专辑）、`archive`、`mp`
- **真实结构**：`books[].{bookId,title,author,cover,readUpdateTime,updateTime,finishReading,readerLink,deepLink}`
- **示例**：
  ```bash
  -d '{"api_name":"/shelf/sync","skill_version":"1.0.6"}'
  ```
  实测书架 141 本；书架书数按 `books.length + albums.length + (mp非空?1:0)` 计算。
- **场景**："我有哪些书"、筛选最近阅读的书（`readUpdateTime`）。
- **注意**：`readUpdateTime` 只是**最后阅读时间**，无法还原"某周期读了哪几本"。

#### `/user/notebooks` — 笔记本概览

- **参数**：`count`（默认20）、`lastSort`（游标）
- **返回**：`totalBookCount`、`totalNoteCount`、`books[].{bookId,book,reviewCount,noteCount,bookmarkCount,readingProgress,markedStatus,sort}`、`hasMore`
- **示例**：
  ```bash
  -d '{"api_name":"/user/notebooks","count":20,"skill_version":"1.0.6"}'
  -d '{"api_name":"/user/notebooks","count":20,"lastSort":1793847318,"skill_version":"1.0.6"}'
  ```
- **关键口径**：
  - 单本书笔记数 = `reviewCount + noteCount + bookmarkCount`
  - `noteCount` 是**划线数**（不是总笔记数）；`reviewCount` 已含个人点评，勿重复相加。
  - 书签只有数量，接口不导出书签内容。
  - 分页只认 `count`+`lastSort`，用 `offset/limit` 会失效。

#### `/book/bookmarklist` — 个人划线

- **参数**：`bookId`*
- **返回**：`updated[].{bookmarkId,chapterUid,markText,range,createTime,colorStyle}`、`chapters[]`、`book`、`removed`、`synckey`
- **示例**：
  ```bash
  -d '{"api_name":"/book/bookmarklist","bookId":"31131759","skill_version":"1.0.6"}'
  ```
- **场景**：导出"我的划线"、按章节分组。
- **注意**：只返回划线（type=1），已过滤书签；`range` 是字符位置范围（如 `"393-401"`），不是页码。

#### `/review/list/mine` — 个人想法/笔记

- **参数**：`bookid`*（注意是小写 d）、`count`（默认20）、`synckey`
- **返回**：`reviews[].review.{reviewId,content,abstract,range,chapterUid,chapterIdx,createTime,star,chapterName,isFinish}`、`totalCount`、`hasMore`
- **示例**：
  ```bash
  -d '{"api_name":"/review/list/mine","bookid":"31131759","count":20,"skill_version":"1.0.6"}'
  ```
- **注意**：`abstract`+`range` 仅"针对原文发表的想法"才有；整本书评可能为空。

---

### D. 划线、评论与点评

#### `/book/bestbookmarks` — 热门划线（含原文）

- **参数**：`bookId`*、`chapterUid`（默认0=全书）、`synckey`
- **返回**：`totalCount`（实测《剑来》959）、`items[].{chapterUid,range,markText,totalCount,bookmarkId}`、`chapters[]`
- **示例**：
  ```bash
  -d '{"api_name":"/book/bestbookmarks","bookId":"31131759","chapterUid":0,"skill_version":"1.0.6"}'
  ```
  实测 Top1："她向前走了两步，一把抱住了那个大骊少年……"（4140 人划线，range `21502-21592`）
- **关键机制（实测确认）**：
  - 服务端固定返回全书 **Top20**（`count=20,maxIdx=0`），不支持分页。
  - `chapterUid` 过滤是**在 Top20 结果集内筛选**，并非查询该章节独立热度。实测：全书 Top20 仅覆盖 18 个章节；当前阅读章节 uid=1591/1592 落在 20 条之外，传该 chapterUid 返回 0 条；传 uid=1074 返回 7 条。
  - 因此"按任意章节取热门划线"仅在该章节恰好进入全书 Top20 时有数据。

#### `/book/underlines` — 章节划线热度（无文本）

- **参数**：`bookId`*、`chapterUid`*、`synckey`
- **返回**：`underlines[].{range,count,score,type}`、`synckey`
- **示例**：
  ```bash
  -d '{"api_name":"/book/underlines","bookId":"31131759","chapterUid":1074,"skill_version":"1.0.6"}'
  ```
- **场景**：判断哪些段落"很多人划线"，用于定位热门位置。
- **注意**：**不含划线文本**；要文本需配合 `/book/bestbookmarks` 或 `/book/bookmarklist`。

#### `/book/readreviews` — 划线下的想法/评论

- **参数**：`bookId`*、`chapterUid`*、`reviews`* `array`（每项：`range`*、`count`、`maxIdx`、`synckey`）
- **返回**：`reviews[].{range,totalCount,hasMore,maxIdx,synckey,pageReviews[]}`；`pageReviews[].review.{content,abstract,range,author,createTime}`
- **示例**：
  ```bash
  -d '{"api_name":"/book/readreviews","bookId":"31131759","chapterUid":1074,"reviews":[{"range":"21502-21592","count":5,"maxIdx":0}],"skill_version":"1.0.6"}'
  ```
  实测该 range 返回 5 条评论，`totalCount=246`，可翻页。
- **注意**：每个划线最多 20 条；`reviews` 是**数组**，须按接口约定传对象数组，不要拆成顶层字段。

#### `/review/list` — 公开点评

- **参数**：`bookId`*、`reviewListType`（0全部/1推荐/2不行/3最新/4一般，默认0）、`count`（默认20）、`maxIdx`、`synckey`
- **返回**：`reviews[]`、`reviewsCnt`、`reviewsHasMore`、`friendCommentUsers[]`、`deepVRecommendInfo` 等
- **真实结构（双层 review 嵌套）**：  
  `reviews[].{idx, review:{ reviewId, likesCount, commentsCount, friendLikesCount, review:{ content, htmlContent, star, author:{name,avatar}, book:{bookId,title,author}, chapterName, createTime, isFinish }}}`
- **示例**：
  ```bash
  -d '{"api_name":"/review/list","bookId":"31131759","reviewListType":1,"count":2,"skill_version":"1.0.6"}'
  ```
  实测《剑来》推荐点评总数 1701，含点赞数（如 846）、评论数（如 21）。
- **注意**：内容字段在内层 `reviews[].review.review.content`，不要读错层级；`star` 为 20/40/60/80/100（1-5 星）。

#### `/review/single` — 单条想法详情

- **参数**：`reviewId`*、`commentsCount`（默认10）、`commentsDirection`（0倒序/1正序）、`likesCount`（默认10）、`likesDirection`、`synckey`
- **返回**：`reviewId`、`review`、`htmlContent`、`bookReviewCount`
- **示例**：
  ```bash
  -d '{"api_name":"/review/single","reviewId":"379542066_851KJo8xA","commentsCount":10,"likesCount":10,"skill_version":"1.0.6"}'
  ```
- **场景**：获取某条热门评论的点赞/回复列表。

---

### E. 阅读统计

#### `/readdata/detail` — 阅读统计

- **参数**：`mode`（weekly/monthly/annually/overall，默认 monthly）、`baseTime`（0=当前周期；历史时间戳=该时间戳所在周期）
- **返回（部分）**：`baseTime`、`readTimes`（分桶时长，key=时间戳 value=秒）、`dailyReadTimes`、`readDays`、`totalReadTime`（秒）、`dayAverageReadTime`、`compare`、`readLongest[]`、`readStat[]`、`preferCategory[]`、`preferTime[]`、`preferAuthor[]`、`preferPublisher[]`、`rank`、`medals`、`readRate`、`wrReadTime`、`wrListenTime`
- **示例**：
  ```bash
  -d '{"api_name":"/readdata/detail","mode":"weekly","skill_version":"1.0.6"}'
  ```
  实测当日：baseTime=2026-11-16（周一零点）、readDays=1、totalReadTime=94 秒、readLongest=0 条。
- **关键口径与坑**：
  - 所有时长字段单位是**秒**，展示时转"X小时Y分钟"。
  - `readLongest` **最多 10 条，且过滤阅读时长低于 5 分钟的条目** → 阅读量小时返回空数组，不可作为稳定书目清单。
  - 只支持固定自然周期（周/月/年/总），**不支持任意起止时间**；"上次调用至今"无法直接查。
  - `dayAverageReadTime` 分母是自然日数，不是阅读天数。
  - `readTimes` 是分桶明细，总量以 `totalReadTime` 为准。

---

### F. 其他

#### `/page/submit` — 上传自定义 HTML 页面

- **参数**：`scene`* `int`（1=2026 年度总结）、`html`* `string`（非空 HTML）
- **返回**：`id`、`object_path`、`created_at`
- **示例**：
  ```bash
  ```


  -d '{"api_name":"/page/submit","scene":1,"html":"<html><body>年度报告</body></html>","skill_version":"1.0.6"}'
  ```
- **场景**：把生成的 HTML 报告上传到平台并返回页面标识。

---

## 四、关键限制与实测发现（影响需求设计）

1. **个人阅读行为轨迹不在开放接口中**
   - 没有"某日读了哪本书、从哪页到哪页"的逐次阅读事件接口。
   - `/readdata/detail` 只有周期聚合时长；`/book/getprogress` 只有当前位置快照；`/shelf/sync` 只有最后阅读时间。
   - 结论：任何依赖"指定时间区间内的个人阅读明细"的需求，都无法仅凭这些接口实现。

2. **"区间"定位的最小粒度是章节（chapterUid），不是页码**
   - `range` 是字符位置偏移，电子书无纸质页码概念。
   - 热门划线只覆盖全书 Top20 涉及的章节（实测《剑来》643 章中仅 18 章有数据）。

3. **热门评论链的可用路径**
   - `/book/bestbookmarks`（取 range + 原文 + 人数）→ `/book/readreviews`（按 range 取评论）→ `/review/single`（单条详情）。
   - `/review/list` 提供全书级公开点评（含点赞数、推荐筛选），但不支持按章节/区间筛选。

4. **`@page/submit` 提供了报告落地通道**，可将最终 HTML 结果上传并返回页面 ID。

---

## 五、数据可得性速查

| 想要的数据 | 能否拿到 | 来源接口 |
|-----------|---------|---------|
| 书名→bookId | ✅ | `/store/search` |
| 书架全部书籍 | ✅ | `/shelf/sync` |
| 书籍详情/目录 | ✅ | `/book/info`、`/book/chapterinfo` |
| 当前读到第几章/百分比 | ✅（仅当前） | `/book/getprogress` |
| 某周期内阅读时长/天数 | ✅ | `/readdata/detail` |
| 某周期内读过哪些书 | ⚠️ 不可靠（5分钟阈值+最多10条） | `/readdata/detail` 的 `readLongest` |
| 任意区间内的阅读轨迹 | ❌ | 无接口 |
| 逐次阅读的页码区间 | ❌ | 无接口 |
| 我的划线/想法 | ✅ | `/book/bookmarklist`、`/review/list/mine` |
| 全书/章节热门划线 Top5 | ✅（章节需在 Top20 内） | `/book/bestbookmarks` |
| 划线下的热门评论 Top5 | ✅ | `/book/readreviews`、`/review/single` |
| 全书公开点评（含点赞） | ✅ | `/review/list` |
| 好友在读动态 | ✅ | `/discover/interact/type3` |
| 相似/个性化推荐 | ✅ | `/book/similar`、`/book/recommend` |
| 上传 HTML 报告 | ✅ | `/page/submit` |
