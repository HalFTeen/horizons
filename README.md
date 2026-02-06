# Horizons

自动化关注者洞察工具，目标能力：

- 维护关注者列表（初始：`minimax`）。
- 聚合最近一周来自 RSS / 网页的最新内容。
- 去重 + 存档条目，为后续音视频转写、观点提炼做准备。
- 计划每两天 06:00（北京时间）运行一次，结果通过 QQ 邮箱发送。

## 当前进度

- [x] 仓库初始化
- [x] 项目骨架与依赖管理（`pyproject.toml`）
- [x] 配置模块（读取 `config/followees.json` 与 `config/secrets.json`）
- [x] SQLite 数据层（`sources` / `items` / `runs` 表设计）
- [x] RSS/网页采集模块（`collector/rss.py`, `collector/webpage.py`）
- [x] 测试基础设施（pytest + pytest-cov）
- [x] GLM 观点提炼（`summarizer/glm.py` + CLI `summarize` 命令）
- [x] 邮件推送（`mailer/qq.py` + CLI `email-snippet` 命令）
- [x] CLI 命令：`init-db`, `ingest-rss`, `ingest-url`, `email-snippet`, `summarize`
- [ ] 音视频转写模块
- [ ] 主流程 `run` 命令（整合采集→转写→摘要→邮件）
- [ ] 调度脚本

## 目录结构（草案）

```
.
├── config/              # 运行配置、关注者列表、密钥（本地维护）
├── data/                # SQLite 数据库、缓存
├── docs/                # 设计文档、流程说明
├── logs/                # 运行日志
├── scripts/             # 调度或辅助脚本
├── src/
│   └── horizons/
│       ├── collector/   # RSS/网页采集
│       ├── transcriber/ # 音视频转写
│       ├── summarizer/  # 调用 GLM4.7
│       ├── mailer/      # 邮件发送
│       └── cli.py       # 命令行入口
└── tests/               # 单元 / 集成测试
```

## 本地开发说明

1. Python 版本：3.11+
2. 创建虚拟环境并安装依赖：
   ```bash
   conda create -n horizons python=3.11 -y
   conda activate horizons
   pip install -e ".[dev]"
   ```
3. 填写配置：
   - `config/followees.json`：关注者及其数据源
   - `config/secrets.json`：邮箱、GLM API Key、GitHub 凭证等
4. 初始化数据库：
   ```bash
   horizons init-db
   ```
5. 运行测试：
   ```bash
   pytest
   ```
6. CLI 命令：
   ```bash
   horizons ingest-rss              # 采集 RSS 源
   horizons ingest-url <URL>        # 采集单个网页
   horizons summarize <ITEM_ID>     # GLM 摘要生成
   horizons email-snippet --to <EMAIL>  # 发送摘要邮件
   ```

---

> NOTE: 项目处于早期阶段，功能将按小颗粒迭代并及时验证与推送。
