# Campus Event Workflow

定时扫描 McGill / Concordia 活动页面，导出 JSON，并通过 [Agnes 2.0 Flash](https://agnes-ai.com/doc/agnes-20-flash) API 分析。

## 数据源

| 学校 | 活动页面 | 实现 |
|------|----------|------|
| McGill | [McGill Events](https://www.mcgill.ca/channels/section/all/channel_event) | `event_workflow/sources/mcgill.py` |
| Concordia | [Concordia Events](https://www.concordia.ca/events.html) | `event_workflow/sources/concordia.py` |

默认爬取窗口为**当日 + 未来 3 日**。新增学校时实现 `EventSource` 并在 `pipeline.py` 中注册即可。

## 快速开始

```bash
cd NearNext
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # 填入 AGNES_API_KEY
```

## 命令

```bash
# 仅爬取并导出 data/events.json（当日 + 未来 3 日）
python -m event_workflow.cli scrape

# 对已导出活动调用 LLM 分析
python -m event_workflow.cli analyze

# 爬取 + 分析
python -m event_workflow.cli run

# 每天定时执行（默认 08:00）
python -m event_workflow.cli schedule --daily-at 08:00
```

## 扩展数据源

实现 `event_workflow.sources.base.EventSource`，在 `PipelineConfig.sources` 中注册即可。

## 兴趣过滤

规则配置文件：`config/filter_rules.json`（可随时修改 exclude / interests 关键词）

```bash
# 对已导出的 events.json 做兴趣过滤 + 统计
python -m event_workflow.cli filter

# 输出:
#   data/events_filtered.json  — 筛选后活动（含 matched_interests 标签）
#   data/filter_stats.json       — 每日/来源/兴趣统计数据

# 对筛选后的活动做 LLM 深度分析
python -m event_workflow.cli analyze --filtered
```

过滤逻辑：**先排除** PhD答辩、校园参观、注册事务、考试、奖学金等 → **再保留** 匹配 AI / 求职 / 音乐 / 社交 关键词的活动。

LLM 分析在规则过滤**之后**运行，用于生成摘要、推荐和去重，不负责硬性剔除。

```bash
pytest
```

## Agnes API

- Base URL: `https://apihub.agnes-ai.com/v1`
- Model: `agnes-2.0-flash`
- Endpoint: `POST /chat/completions`（OpenAI 兼容）
- Key: https://platform.agnes-ai.com/settings/apiKeys

## TODO

- [ ] **前端展示**：将 `data/events_filtered.json` 渲染为可浏览的 Web 页面（按日期、兴趣标签、学校筛选）
- [ ] **通知推送**：筛选出高相关活动后，通过邮件 / Telegram / Slack 发送每日摘要
- [ ] **更多数据源**：接入 UdeM、Polytechnique 等蒙特利尔高校活动页
- [ ] **详情页补全**：对部分活动抓取「More info」详情页，补充完整描述与报名链接
- [ ] **部署定时任务**：用 GitHub Actions 或服务器 cron 每日自动 `scrape` + `filter`
