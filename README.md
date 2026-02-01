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
- [ ] RSS/网页采集模块
- [ ] 音视频转写模块
- [ ] GLM4.7 观点提炼
- [ ] 邮件推送
- [ ] CLI & 调度脚本

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

## 本地开发说明（初稿）

1. Python 版本：3.11+
2. 安装依赖：
   ```bash
   pip install -e .
   ```
3. 填写配置：
   - `config/followees.json`：关注者及其数据源
   - `config/secrets.json`：邮箱、GLM API Key、GitHub 凭证等
4. 初始化数据库：
   ```bash
   python -m horizons.cli init-db
   ```
5. 运行预定任务（尚在开发）：
   ```bash
   python -m horizons.cli run
   ```

---

> NOTE: 项目处于早期阶段，功能将按小颗粒迭代并及时验证与推送。
