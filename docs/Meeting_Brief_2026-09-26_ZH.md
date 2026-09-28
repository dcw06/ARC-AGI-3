# ARC-AGI-3 项目会议材料

## 代码、真实模型回放、完整结果与 GPU 状态

整理日期：2026 年 9 月 26 日（America/Los_Angeles）。

本材料核对的远端代码版本为 `0b0e453eebc9e032bd08799bd123637fcb5b18ef`。本文依据该版本的报告、冻结配置、真实运行归档及独立回放，不把项目计划或 CPU 脚本模拟当成真实模型结果。本次未登录 Kaggle 查询实时额度或排行榜，也未启动模型、预留算力或提交比赛。

## 一、会议开场摘要

**一句话结论：项目已经建立较完整的可复现执行与研究基础设施，但尚未证明有效的游戏解题能力；下一步是在小规模诊断中确认模型是否能正确读取自己的控制和动作效果证据。**

可以确认的主要事实：

- 最大规模、已报告通过的真实模型开发生命周期运行是 v13：110 个客户端、7,582 次真实模型请求和确认动作，完成关卡数为 0。
- 最近完成的动作效果历史对照研究运行了 3 个开发游戏、2 个顺序反转区组、12 个 episode，共 144 次模型决策和动作；两组均未完成任何关卡。
- 该研究在技术层面完整，行为结论为“不确定”，解题结论为“未证明改善”。它有完整归档和可离线浏览的双臂回放。
- README 记录 E0 历史公开分数为 0.08。它是流程基线，不是最新模型成绩，也不能解释为“零关卡必然等于 0.08”。
- 最新 evidence-comprehension 问卷包已实现 CPU 演练，但仍有独立审查发现待修复；当前不具备 GPU 发射批准。
- 最近归档中的 GPU 账户余额可算出历史值，但不是今天实时可用额度，更不是项目已经获准使用的预算。

## 二、能运行的确切版本、启动方式和配置

### 2.1 必须区分三个版本概念

| 对象 | 确切版本或标识 | 可以证明什么 |
|---|---|---|
| 最新开发代码 | `0b0e453eebc9e032bd08799bd123637fcb5b18ef` | 包含最新理解问卷 runner、GPU-disabled review package 和本次会议所用报告 |
| 最近真实游戏研究的归档快照 | `13ad6e0`，归档提交 `3e54968` | 真实模型动作历史实验的结果、完整 archive 和 HTML 回放 |
| 当时真实运行的冻结源代码 | action-effect-history review r3，锁 `0f870a1a…e386` | 绑定当时实际执行的源码；不能用当前工作目录冒充当时运行代码 |

最新理解问卷 review r1 的完整锁为：

`866bffdb1359dfe71639b8de7ed9970a35c065f3e9cdca6571b79bb2bd05354e`

其目录是 `notebooks/evidence-comprehension-v1-review-r1/`，包含 1,081 个运行源码绑定。GPU 和互联网均关闭；锁验证通过不代表获准发射。

注意：本次检查时，当前本地工作树仍停在较早提交 `fa5f524`，并有未跟踪文档。远端已更新并不意味着当前目录已切换到最新代码。审查使用隔离快照，没有覆盖现有工作。

### 2.2 建议的会议复现入口

在现有仓库中创建独立工作树，不改动当前目录的未提交内容：

```bash
git fetch origin
git worktree add --detach ../AGI-meeting-20260926 0b0e453eebc9e032bd08799bd123637fcb5b18ef
cd ../AGI-meeting-20260926
```

以上命令假设目标目录尚不存在。Windows 建议在已配置的 WSL/Linux 开发环境中执行；进程组、文件锁及 supervisor 演练不应当作原生 Windows 已获验证。

使用已经装好项目依赖的 Python 3.12 开发环境。以下 `python` 指该环境的解释器，不是任意系统 Python。仓库 README 的 `make setup` 是一般开发入口，但不等于冻结 GPU 推理环境的安装验收。

会议最安全、最容易稳定演示的两个命令是：

```bash
python -m scripts.archive_action_effect_history_v1 replay
python -m scripts.build_action_effect_history_v1_replay --check
```

第一条验证 archive 的哈希、55 个成员文件，并重新执行独立 evaluator；第二条检查 HTML 能否从 archive 字节一致地重建。两者不调用模型、不花 GPU、不触发比赛提交。本次整理已重新执行，两条均通过。

问卷数据和本地测试入口：

```bash
python -m scripts.build_evidence_comprehension_v1 --check
python -m unittest tests.test_evidence_comprehension_v1 tests.test_evidence_comprehension_v1_schedule tests.test_evidence_comprehension_v1_transport tests.test_evidence_comprehension_v1_snapshot -q
```

连接路径的 CPU 演练入口：

```bash
python -m scripts.rehearse_evidence_comprehension_v1 --fault none --seconds 480
```

演练会启动本地进程、写入演练输出并进行清理，答案来自脚本假模型。它不是新的真实模型实验。不要把 `package`、`reserve` 或 `launch` 命令作为会议演示命令。

### 2.3 最近真实游戏研究的配置

| 配置项 | 动作效果历史研究 |
|---|---|
| 模型 | `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8` |
| 服务 | vLLM 0.19.0 |
| 目标 GPU | 单张 NVIDIA RTX Pro 6000 |
| 输入 | 文本编码的网格和观察字段；本实验不是图像输入对照 |
| 解码 | temperature 0、request seed 0、thinking disabled |
| 输出上限 | 128 completion tokens |
| 游戏种子 | 0 |
| 游戏 | ar25-0c556536、s5i5-18d95033、wa30-ee6fef47 |
| 对照 | 修正后的共同 baseline，对比仅增加 action_effect_history 字段的 history arm |
| 历史 | 当前 segment 内最近 4 条自身已观察到的动作效果记录 |
| 规模 | 2 个顺序反转区组，12 个 episode，每个最多 12 次动作 |
| 停止规则 | 胜利、game over、动作上限、无效输出或失败/未知派发；不自动重试、不主动重启 |
| 时间 | 3,600 秒单次授权；3,300 秒内部上限 |

这是新共同 baseline，不是原封不动的 E1S-R。区组反转不是独立随机种子采样。全部游戏都属于已暴露的开发案例，不支持隐藏集泛化结论。

### 2.4 GPU 目标环境和离线附件

Kaggle notebook metadata 中保留的附件标识：

- Wheelhouse：`driessmit1/arc3-vllm-h100-wheelhouse-v3`。
- 模型：`qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1`。
- 游戏附件：`arc-prize-2026-arc-agi-3`。
- 历史真实 notebook：`notebooks/action-effect-history-v1-run/profile.ipynb`。

Wheelhouse 名称包含 H100，并不表示该次实际运行 GPU 是 H100；运行记录是 RTX Pro 6000。最新 host 检查 vLLM 0.19.0、Torch 2.10.0、Transformers 4.57.6、Tokenizers 0.22.2、Jinja2 3.1.6。实际依赖、模型目录和安装验证应以冻结 notebook/source lock 为准，不能用随意安装的最新版替代。

普通 Mac 或没有 NVIDIA runtime 的 WSL 可做回放和 CPU 演练；不能据此声称能够本地运行同一 GPU 模型服务。本文不提供或展示任何 token、`.env` 或认证文件。

## 三、一份真实模型游戏回放

### 3.1 推荐展示材料

真实运行：`aeh1-4c75150a156640fcad105a770ce81119`。

- Kaggle notebook：[arc3-action-effect-history-v1](https://www.kaggle.com/code/daichongwei06/arc3-action-effect-history-v1)，provider version 1，私有运行。
- 本地页面：`reports/action_effect_history_v1_replay/index.html`，可用浏览器直接打开。
- 私有分享页：[双臂回放](https://claude.ai/artifact/GrQDg7vBXy7MxXm3UxCtR4)。此链接由项目提供，未在本次核对其访问权限；会前应确认同事已被授权，离线 HTML 更适合备用。
- 证据：`evidence/action-effect-history-v1-complete.zip`。
- archive SHA-256：`a67b69557d835f8076e3b80674c29c0032b95ec2dbd9a70f032ed85af54654cb`。

HTML 是真实模型调用及环境返回的可视化，不是 CPU 演练答案。它展示真实观测帧，不补画帧间动画，因此不等于连续视频，也不能用播放速度解释真实推理速度。

### 3.2 建议的五分钟演示顺序

1. 先展示 archive replay 的通过结果，说明回放来源可核验。
2. 打开 ar25 第一区组，逐步查看 baseline 和 history 的动作、坐标、前后帧和效果记录。
3. 指出 history arm 在 ACTION6 与 ACTION7 之间切换，但未带来帧变化或关卡完成。动作类型变化不等于进步。
4. 切换到 s5i5，展示 history arm 连续 12 次点击同一坐标，同时变化仅集中在底行。
5. 最后展示完整结果表，而不是只展示某一次看似合理的动作。

底行“可能是计数器”的解释是事后假设。回放颜色属于标注，不是当时输入给模型的知识，也不是冻结成功指标。离线探针观察到 ar25 某些箭头动作会改变画面，不等于已经证明这些动作能解题。

## 四、目前最佳完整结果：包含零分与失败

### 4.1 怎样定义“最佳”

目前没有证据支持一个统一的“最佳解题模型”称号。本会议建议分别报告：

- **工程规模最强的已报告完整运行**：v13 开发生命周期 pilot。
- **最近、最容易独立核验的对照研究**：动作效果历史实验。
- **历史比赛基线**：README 所记 E0 公开分数 0.08。

三者的工作负载、评价口径和用途不同，不应合并成一个成绩。

### 4.2 v13：完整规模与零关卡同时成立

| 指标 | 结果 |
|---|---:|
| 客户端 | 110 |
| 真实模型请求 / 确认动作 | 7,582 / 7,582 |
| 通过坐标验证的 ACTION6 | 5,262 |
| 策略失败、parser repair、推理队列失败、transport failure | 均为 0 |
| 完成关卡 | 0 |
| Notebook 生命周期 | 4,500.288 秒，约 75 分钟 |
| 监控样本 | 16,133 |

这是 15 个开发游戏在 110 个客户端中重复运行，并非 110 个不同正式游戏共用一个 scorecard 的生产认证。生命周期通过，不代表 Phase 4 全部退出条件通过，也不代表解题质量合格。

来源：`reports/phase4_v13_pilot_status.md`、`reports/phase4_v13_pilot_evaluation.json`。归档为 `evidence/phase4-v13-pilot-passed-v1.zip`。本次查阅了报告，未重新执行该大型归档的独立验证。

### 4.3 最近动作效果历史对照：完整结果

| 指标 | Baseline | History |
|---|---:|---:|
| Episode 数 | 6 | 6 |
| 决策及确认动作 | 72 | 72 |
| 完成关卡 | 0 | 0 |
| 无效输出、派发失败、中断、关闭失败 | 均为 0 | 均为 0 |
| 即时精确重复 / 机会数 | 7/23 | 6/24 |

逐对结果：

| 区组与游戏 | Baseline | History | 冻结分类 |
|---|---:|---:|---|
| b1 ar25 | 3/11 | 3/11 | 未减少 |
| b1 s5i5 | 0/0 | 0/0 | 不具备比较资格 |
| b1 wa30 | 0/0 | 0/1 | 不具备比较资格 |
| b2 wa30 | 1/1 | 0/1 | 减少，但只有一次机会 |
| b2 s5i5 | 0/0 | 0/0 | 不具备比较资格 |
| b2 ar25 | 3/11 | 3/11 | 未减少 |

0/0 的比率未定义，不是 0%。只有 3 对具备比较资格。总体行为结果是 **inconclusive**，不能把 0.304 → 0.250 宣称为可靠改善。解题结果是 **no_demonstrated_solving_improvement**。

### 4.4 感知负结果及失败记录

| 记录 | 必须保留的结论 |
|---|---|
| Paired perception R2 | 在冻结 IoU ≥ 1/2 阈值下，文本和图像均为 0/11 参考对象检出；这是对象检测结果，不是 11 个关卡的通关率 |
| R2 控制参数问答 | 两种表示都只有 1/7 动作坐标参数分类正确；未执行游戏动作 |
| v11 pilot 上传 | HTTP 400，后续状态 HTTP 404，未确认有运行中的 GPU session；不能写成模型推理失败或确定零花费 |
| v12 pilot | 完成 110 客户端和 7,582 请求，但旧 evaluator 用八 token canary 上限拒绝了有效的 29-token 输出；原始 notebook 结论仍保留失败 |
| 最新理解问卷 | CPU stand-in 的成功不算模型结果；真实模型问卷尚未运行 |

这不是全部历史 attempt 的穷尽清单，而是本次会议相关的主要已核对记录。若需要“项目累计全部失败及花费”，需逐条核对所有 ledger 和 provider session inventory，不能由本表推算。

## 五、GPU 时数、调用速度与提交状态

### 5.1 GPU 额度：四种数字不能混用

1. 平台账户当前剩余额度。
2. 项目授权给某个实验的预算。
3. 本地为 attempt 保留、尚未释放的 reservation。
4. 平台明确提供的单次 billed GPU time。

历史账户快照时间：**2026-09-25 22:02:18 UTC，即洛杉矶 2026-09-25 15:02:18 PDT**。

| 字段 | 归档值 |
|---|---:|
| total_time_allowed | 108,000 秒 = 30 小时 |
| time_used | 14,294.995 秒 ≈ 3.9708 小时 |
| time_reserved | 0 秒 |
| 单纯算术差额 | 93,705.005 秒 ≈ 26.0292 小时 |

**26.0292 小时只是该快照字段的历史算术差额，不是今天已确认可用时数。** 本次没有读取实时账户状态、额度周期或完整交互 session 历史。它也不是已批准给下一实验的预算。

动作历史实验账户计数器从 13,547.424 增至 14,294.995 秒，差额 747.571 秒。该差额是账户级观察值，不是独立确认的单次账单。该 attempt 已消耗，不可自动重试。

最新理解问卷包：**授权时数为 0，无 reservation，无 launch**。拟议上限不等于批准。

### 5.2 尚未解决的历史记账

V2 fixture prescreen：内部计时 1,074.161 秒；Kaggle 截图显示 1,083.8 秒。两者都不能自动替代精确 billed GPU time。历史 28,800 秒（8 小时）本地预留仍保留，释放 0 秒，不转给下一实验。

Owner 的表述记录为“no additional sessions recalled”，不是已核验的“没有其他 session”。v13 报告也保留原 28,800 秒 reservation，精确单次账单待核对。本地保守 reservation 和平台 `time_reserved=0` 可以同时存在，不应混为一谈，也不能直接从当前账户余额减去跨时期的全部旧 reservation。

会前若必须确定当天可使用 GPU 时数，应新增带 UTC 时间戳的只读 quota/session 导出，再由负责人另行明确实验授权；不要修改旧观察记录。

### 5.3 实际调用速度

以下由真实动作历史研究 144 次调用的 `latency_seconds` 重新汇总，未包含 startup，也不是去缓存新问卷的性能保证：

| 统计 | 秒 / 调用 |
|---|---:|
| 均值 | 1.3047 |
| 中位数 | 1.4113 |
| P95（nearest-rank） | 1.6839 |
| 最快 | 0.1997 |
| 最慢 | 1.7370 |
| 总调用延迟 | 187.8721 秒 |

该研究模型 startup 约 403 秒，supervisor 约 735 秒，first-cell 约 737 秒。这些是嵌套时间，不应相加。144/737 ≈ 0.195 次动作/秒是包含启动等成本的整体摊销值，不是稳态推理速度。

v13 的整体摊销吞吐为 7,582/4,500.288 ≈ 1.685 次动作/秒。该值跨 110 个客户端，不能解读为每个游戏每秒 1.685 帧，更不能与单个请求延迟直接比较。

新问卷要求关闭 prefix caching，采用不同问题长度和输出上限。其真实 GPU 速度尚未测量；历史 110 completion tokens/s、8,929 prompt tokens/s 是规划参考，不是保证下限。

### 5.4 当前提交状态

| 类型 | 已知状态 |
|---|---|
| GitHub | 最新核对的 origin/main 为 `0b0e453` |
| 最近真实研究 notebook | action-effect-history v1，version 1，归档 provider 状态 COMPLETE，私有、非计分研究 |
| v13 notebook | 报告为开发 pilot 完成，不是正式生产认证 |
| 最新问卷 GPU run | 未授权、未预留、未上传、未启动 |
| 比赛排行榜 | README 记录历史 E0 0.08；本次未核验实时排行榜或全部提交列表 |
| 论文 | 已有本地草稿及 Word 导出；未发现本次已完成论文提交的确认，本文不作已提交声明 |

“Save Version / notebook 完成”和“Submit to Competition / 计分提交”不是同一个事件。会议不要把私有研究成功运行写成比赛成绩更新。

## 六、当前代码审查状态与下一步

最新 package 的源码锁已核对。本轮独立审查运行了 52 个 unit/transport/snapshot 测试及 1 个连接路径正常运行测试，均通过；未重跑全部耗时连接故障测试。团队报告的全部演练通过应与独立重跑范围分开陈述。

仍有三个独立审查问题，不能以已有测试通过代替修复：

1. **调用证据验证不足。** evaluator 接受负 token 数、缺失 completion metadata、未校验的 finish reason 和越过截止时间的调用时间戳。
2. **metrics 检查缺少总截止保护。** 15 秒 idle 检查可在 20 秒后返回成功；逐次 socket timeout 不能保证整个检查在预算内结束。
3. **缓存验证信任结论标志。** 即使保留的 cache queries/hits 为非零，`prefix_caching_disabled_verified=true` 仍可通过独立验证。

下一里程碑应为：保留当前 review r1，修复这些问题，增加异常证据和慢 metrics 回归，冻结 review r2，再进行独立 review。之后才是明确源码批准、独立 compute authorization 和单次 reservation。

研究问题保持不变：**模型能否根据给出的控制规则和自身动作效果证据，正确回答事实性问题？** 当前 revision 4 有 654 道不同请求的问题，其中 454 道用于主要 gate；两遍合计 1,308 次问卷调用，另有 startup canary。没有真实模型答案，不能提前报告 comprehension accuracy。

## 七、会议可直接使用的讲述稿

“我们现在最确定的进展在执行可靠性和证据可复现性，而不是解题分数。真实模型已经在 110 个开发客户端中完成过 7,582 次动作，但没有完成关卡。最近的小规模对照也没有证明动作历史能改善解题，我们保留了全部零结果，可以现场逐步回放。

下一步不是再盲目跑一次，而是先验证模型是否能读懂控制和动作反馈。问卷及本地 runner 已准备，但独立审查还发现 evaluator 和截止保护问题，修复前不会申请 GPU 发射。账户历史快照约有 26 小时算术余额，不过这不是实时确认，也不是下一实验授权。今天希望讨论的是研究范围、修复负责人、审查标准及后续单次预算，而不是宣布系统已能解题。”

## 八、分享清单与证据索引

建议发给同事：本说明、精确 commit 链接、HTML 回放、archive 与 lock、结果 JSON/Markdown、下一实验 protocol/review。不要分享 `.env`、API token、整个虚拟环境或用户认证目录。

固定源码入口：[GitHub 0b0e453](https://github.com/dcw06/ARC-AGI-3/tree/0b0e453eebc9e032bd08799bd123637fcb5b18ef)。以下路径均相对此版本：

| 材料 | 路径 |
|---|---|
| 最近真实研究结果 | `reports/action_effect_history_v1_results.md` |
| 机器可读完整评价 | `reports/action_effect_history_v1_live_evaluation.json` |
| 归档锁 | `reports/action_effect_history_v1_archive.json` |
| 真实模型回放 | `reports/action_effect_history_v1_replay/index.html` |
| v13 完整运行报告 | `reports/phase4_v13_pilot_status.md` |
| 对象检测负结果 | `reports/phase4_perception_v1_r2_disposition.md` |
| v11 / v12 失败记录 | `reports/phase4_v11_pilot_status.md`、`reports/phase4_v12_pilot_status.md` |
| 历史记账限制 | `reports/phase4_accounting_v2_disposition.md`、`reports/phase4_accounting_v2_screenshot.json`、`reports/phase4_accounting_owner_recollection.json` |
| 问卷协议与审查包 | `reports/evidence_comprehension_v1_protocol.md`、`reports/evidence_comprehension_v1_review.md` |
| 问卷 token 审计 | `reports/evidence_comprehension_v1_token_audit.json` |

`phase4_status.md` 和 README 包含历史准备状态，部分段落已被后续结果取代。会议引用应优先使用具体 attempt 的最终结果、归档和时间戳，而不是孤立引用“尚未启动”或“已经通过”的旧段落。

本文属于会议资料，不授予任何 GPU、holdout、上传或比赛提交权限。
