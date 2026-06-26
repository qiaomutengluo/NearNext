# Campus Event Workflow

定时扫描 McGill / Concordia 活动页面，导出 JSON，并通过 [Agnes 2.0 Flash](https://agnes-ai.com/doc/agnes-20-flash) API 分析。

**在线展示：** https://qiaomutengluo.github.io/NearNext/

## 数据源

| 学校 | 活动页面 | 实现 |
|------|----------|------|
| McGill | [McGill Events](https://www.mcgill.ca/channels/section/all/channel_event) | `event_workflow/sources/mcgill.py` |
| Concordia | [Concordia Events](https://www.concordia.ca/events.html) | `event_workflow/sources/concordia.py` |

默认爬取窗口为**含当日共 7 天**（可用 `--horizon-days` 调整）。跨度超过 14 天的长期提醒类条目会在爬取/过滤时自动剔除。新增学校时实现 `EventSource` 并在 `pipeline.py` 中注册即可。

## 快速开始

```bash
cd NearNext
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # 填入 AGNES_API_KEY
```

## 爬取窗口与数据清洗

| 设置 | 说明 |
|------|------|
| `--horizon-days` | 含**今天**在内的连续天数，默认 `7`（一周） |
| 长期提醒过滤 | `start_at`–`end_at` 跨度 **> 14 天** 的条目自动忽略（多为申请截止提醒，而非单场活动） |

`scrape`、`run`、`filter`、`schedule` 均支持 `--horizon-days`；其中 `filter` 用它计算统计窗口，不改变已爬取的 `events.json`。

## 命令

```bash
# 爬取并导出 data/events.json（默认含今日共 7 天）
python -m event_workflow.cli scrape

# 自定义窗口，例如含今日共 14 天
python -m event_workflow.cli scrape --horizon-days 14

# 对已导出活动调用 LLM 分析
python -m event_workflow.cli analyze

# 爬取 + 分析（同样支持 --horizon-days）
python -m event_workflow.cli run --horizon-days 10

# 每天定时执行（默认 08:00）
python -m event_workflow.cli schedule --daily-at 08:00
```

## 兴趣过滤

规则配置文件：`config/filter_rules.json`（可随时修改 exclude / interests 关键词）

```bash
# 对已导出的 events.json 做兴趣过滤 + 统计（统计窗口默认同为 7 天）
python -m event_workflow.cli filter
python -m event_workflow.cli filter --horizon-days 14

# 过滤后同时更新 GitHub Pages 静态页
python -m event_workflow.cli filter --publish-site

# 单独发布前端（需已有 data/events_filtered.json）
python -m event_workflow.cli publish-site

# 输出:
#   data/events_filtered.json  — 筛选后活动（含 matched_interests 标签）
#   data/filter_stats.json       — 每日/来源/兴趣统计数据
#   docs/                        — GitHub Pages 静态站点

# 对筛选后的活动做 LLM 深度分析
python -m event_workflow.cli analyze --filtered
```

过滤逻辑：**先排除** 跨度超过 14 天的长期提醒、PhD答辩、校园参观、注册事务、考试、奖学金等 → **再保留** 匹配 AI / 求职 / 音乐 / 社交 关键词的活动。

LLM 分析在规则过滤**之后**运行，用于生成摘要、推荐和去重，不负责硬性剔除。

## 前端展示（GitHub Pages）

当前采用**单次快照**模式：每次运行 `filter --publish-site`（或 `publish-site`）会用最新的筛选结果**整体替换** `docs/events.json`，页面展示这一轮爬取窗口内的活动。

推荐更新流程：

```bash
python -m event_workflow.cli scrape
python -m event_workflow.cli filter --publish-site
git add docs/
git commit -m "chore: update event site snapshot"
git push
```

### 首次启用 GitHub Pages

1. 打开仓库 **Settings → Pages**
2. **Build and deployment → Source** 选择 **Deploy from a branch**
3. Branch 选 `main`，文件夹选 **`/docs`**
4. 保存后等待 1–2 分钟，访问 https://qiaomutengluo.github.io/NearNext/

页面功能：按日期分组、学校/兴趣筛选、标题搜索、活动详情链接。

### 未来可扩展（暂未实现）

- **历史列表模式**：保留每次运行的快照，页面按日期切换查看
- **定时自动更新**：GitHub Actions 每日 `scrape` + `filter` + `publish-site` + push

## 扩展数据源

实现 `event_workflow.sources.base.EventSource`，在 `PipelineConfig.sources` 中注册即可。

```bash
pytest
```

## Agnes API

- Base URL: `https://apihub.agnes-ai.com/v1`
- Model: `agnes-2.0-flash`
- Endpoint: `POST /chat/completions`（OpenAI 兼容）
- Key: https://platform.agnes-ai.com/settings/apiKeys

## TODO

- [x] **前端展示**：将 `data/events_filtered.json` 渲染为可浏览的 Web 页面（GitHub Pages）
- [ ] **历史快照**：储存多次运行结果，支持按批次浏览
- [ ] **通知推送**：筛选出高相关活动后，通过邮件 / Telegram / Slack 发送每日摘要
- [ ] **更多数据源**：接入 UdeM、Polytechnique 等蒙特利尔高校活动页
- [ ] **详情页补全**：对部分活动抓取「More info」详情页，补充完整描述与报名链接
- [ ] **部署定时任务**：用 GitHub Actions 每日自动 `scrape` + `filter` + `publish-site`
