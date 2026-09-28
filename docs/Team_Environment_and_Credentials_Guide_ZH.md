# ARC-AGI-3 团队环境配置与认证指南

日期：2026-09-26。代码基准：`0b0e453eebc9e032bd08799bd123637fcb5b18ef`。

适用对象：需要阅读代码、复现结果、参与本地测试和查看有权限的 Kaggle 运行的队友。本文不授予 GPU 运行、上传 notebook 或计分提交权限。

本文检查了仓库配置和官方认证说明，没有读取或分享真实 `.env`、Kaggle token 或其他密钥，也没有替任何人配置账户。以下命令是操作指南，不代表已经在每位队友的电脑上完成安装验证。

## 1. 先选择你的工作范围

| 工作 | 本地 GPU | Kaggle token | ARC_API_KEY |
|---|---|---|---|
| 阅读代码、打开已有 HTML 回放 | 不需要 | 不需要 | 不需要 |
| 归档重放、问卷 fixtures/unit tests | 不需要 | 不需要 | 一般不需要；不得额外触发在线游戏请求 |
| CPU 假服务连接演练 | 不需要 | 不需要 | 使用离线证据，不以在线认证作为前提 |
| 查看/下载私有 Kaggle notebook | 不需要 | 需要本人有效认证及对应资源权限 | 通常不需要 |
| 在线 ARC 游戏开发 | 取决于模型方案 | 非必需 | 按平台和任务要求配置 |
| 在 Kaggle 上运行冻结真实模型 | 目标 GPU 必须可用 | 需要；另需项目明确授权 | 由冻结运行协议决定，不可随意改网关配置 |

建议新成员先完成“能重放历史结果”，再配置平台访问，最后才参与 GPU 运行准备。没有 token 不妨碍先做大部分离线研究工作。

## 2. 三种认证不要混淆

| 名称 | 来源 | 用途 | 本项目建议位置 |
|---|---|---|---|
| `ARC_API_KEY` | ARC Prize 平台账户 | ARC 游戏平台访问 | 仓库根目录 `.env` |
| `KAGGLE_API_TOKEN` | 本人 Kaggle 账户 API 设置 | Kaggle API / CLI 认证 | 仓库根目录 `.kaggle/access_token`，文件中仅保存 token 本身 |
| GitHub 认证 | 本人 GitHub 账户 | 私有仓库访问、push 等 | Git 凭据管理器或本人 SSH 配置，不放入上述 token 文件 |

**`ARC_API_KEY` 不是 Kaggle token。** 一个平台的密钥不能填写到另一个平台的字段。

Kaggle 官方还支持旧式 `kaggle.json`、环境变量及其他认证方式。项目的只读辅助脚本有自己的加载逻辑，不等于它自动支持官方 CLI 的所有认证入口。参考：[Kaggle 官方认证说明](https://github.com/Kaggle/kaggle-cli/blob/main/docs/README.md#authentication)。

## 3. Windows：推荐 WSL2，而不是直接运行 Linux supervisor

### 3.1 安装与检查 WSL

在管理员 PowerShell 中，如果还没有 WSL：

```powershell
wsl --install
```

按提示重启、创建 Linux 用户。已有 WSL 的同事不要重复安装，先检查：

```powershell
wsl --list --verbose
wsl --list --online
```

建议使用 WSL2 的 Ubuntu 24.04 开发环境。如需指定发行版，使用在线列表给出的实际名称。安装方法与适用系统要求见 [Microsoft WSL 文档](https://learn.microsoft.com/en-us/windows/wsl/install)。

后文的 Bash 命令在 Ubuntu/WSL 终端执行，不是 PowerShell。Windows 与 WSL 是不同环境，Python、虚拟环境和用户目录下的认证文件不能假定共用。

### 3.2 安装开发工具

在 Ubuntu 中：

```bash
sudo apt update
sudo apt install -y git make python3-venv pipx
pipx install uv
pipx ensurepath
```

重新打开 Ubuntu 终端，再检查：

```bash
git --version
make --version
uv --version
```

uv 的其他官方安装方式见 [uv 安装文档](https://docs.astral.sh/uv/getting-started/installation/)。不要为了装本项目向系统 Python 强行使用 `--break-system-packages`。

### 3.3 获取固定代码

建议仓库放在 WSL 的 Linux 文件系统，例如 `/home/你的Linux用户名/projects/`，而非直接在 `/mnt/c/` 上运行大量小文件写入的演练。

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/dcw06/ARC-AGI-3.git AGI-team
cd AGI-team
git checkout --detach 0b0e453eebc9e032bd08799bd123637fcb5b18ef
git rev-parse HEAD
```

这套命令仅用于新的 `AGI-team` 目录。已有工作目录如含未提交内容，应先检查 `git status`，不要覆盖或强制切换。

detached HEAD 适合固定版本复现。需要开发时从此版本建立自己的分支，例如 `git switch -c research/你的任务名`，不要直接修改冻结 notebook 和 source lock。

### 3.4 创建 Python 环境

新 checkout 可使用仓库现有入口：

```bash
make setup
source .venv/bin/activate
python --version
python -c "import sys; print(sys.executable)"
```

本项目目标开发 Python 是 3.12。`make setup` 会联网安装固定基础依赖、取得并处理指定 revision 的 vendor framework；这不是 GPU 发射，不消耗 Kaggle GPU，但也不是只读操作。已有虚拟环境的成员先核对解释器和依赖，不要无条件重跑 setup。

基础直接版本来自 Makefile / `config/dependency_manifest.lock`，包括 arc-agi 0.9.9、arcengine 0.9.3、kaggle 2.2.4、python-dotenv 1.2.3 等。若固定版本安装失败，保留错误并反馈维护者，不要悄悄换成最新版来宣称复现成功。

**本次发现的开发依赖缺口：**最新问卷 scorer 导入 `jsonschema`，但基础安装清单未显式列出它。独立审查环境使用 4.26.0；在开发虚拟环境中可补装：

```bash
uv pip install --python .venv/bin/python "jsonschema==4.26.0"
uv pip check --python .venv/bin/python
python -c "import arc_agi, arcengine, jsonschema; print('development imports OK')"
```

这是本地开发补充，不代表冻结目标依赖已完成相同修订。若需要修改目标安装清单，应由维护者更新并重新冻结审查包。

`scripts/setup_wsl.sh` 是另一个现有入口，但要求 `python3.12` 命令及已经恢复的 vendor framework；它不是缺少 vendor 的新 checkout 的无条件替代方案。

### 3.5 编辑器与路径

VS Code 中使用 WSL 连接打开同一个 Linux 仓库，并选择该仓库的 `.venv/bin/python`。不要同时编辑 Windows 桌面的另一份 clone，并假设 WSL 文件会同步。

不要照抄历史记录中的 `/home/jingjing/...`、`C:/Users/jjzzw/...` 或其他队员的绝对路径。这些仅是旧机器的记录。用 `pwd` 和 `sys.executable` 确认自己的真实路径。

## 4. macOS 与原生 Windows 的范围

macOS 可以安装 Git、make、uv 后，使用同样的固定 checkout 和 `make setup`。已有 Homebrew 的机器可用 `brew install uv`；仍需按项目要求使用 Python 3.12 虚拟环境。

原生 Windows 可以阅读文档、浏览 HTML、进行部分 API 查询，但本项目监督进程涉及 POSIX 文件锁与进程组，不把它视为已验证的原生 Windows 运行路径。CPU supervisor 建议放在 WSL，真实模型运行放在已批准的 Kaggle 目标环境。

不要从 Mac 复制 `.venv` 到 Windows/WSL 后继续使用。虚拟环境及二进制依赖应在目标平台重建。

## 5. 配置 Kaggle token：推荐项目内文件方式

### 5.1 获取本人 token

登录本人 Kaggle 账户，打开 [API 设置页面](https://www.kaggle.com/settings/api)，按页面提供的生成 token 操作取得凭据。官方文档列出了 API token 文件和旧式凭据文件两种不同方式；不要把整个 `kaggle.json` 粘到 `access_token` 里。

每位同事应使用自己的账户和凭据。访问项目私有 notebook 需要所有者授予相应权限；有 token 不代表自动有权访问所有资源，更不代表可以使用项目负责人的 GPU 预算。

### 5.2 在实际执行脚本的仓库中保存

在 WSL/Linux/macOS 的项目根目录执行：

```bash
mkdir -p .kaggle
chmod 700 .kaggle
nano .kaggle/access_token
```

在编辑器中粘贴 token 本身，保存为单行。不要加 `KAGGLE_API_TOKEN=`，不要加 JSON、引号或 Markdown 标记。然后：

```bash
chmod 600 .kaggle/access_token
git check-ignore .kaggle/access_token
```

应输出被忽略的文件路径。不要运行 `cat .kaggle/access_token` 来截图“证明配置好了”，也不要把真实 token 放进 `echo TOKEN...` 命令，避免进入 shell history。配置时关闭会议共享；编辑器中的文件依然是明文，不是密码库。

### 5.3 项目脚本怎样读它

`scripts/phase4_install_kaggle.py` 会从进程环境、仓库 `.env` 和仓库 `.kaggle/access_token` 查找 Kaggle 凭据，再传给同虚拟环境的 CLI。它还有历史用户路径 fallback；新成员应在自己的当前仓库配置，不要依赖该 fallback。

项目内 `.kaggle/access_token` 与官方默认用户目录中的 `~/.kaggle/access_token` 不是同一个位置。使用项目只读辅助脚本可以避免依赖默认目录。

若直接运行 `kaggle ...`，不要假定它自动读取项目内 token。环境变量中已有旧 token 时，也可能优先使用旧值。排查时只确认是否设置，不打印密钥值。

### 5.4 旧式 kaggle.json 与替代配置

如果账户提供旧式凭据，`kaggle.json` 通常包含 `username` 与 `key`，不是单个现代 token。官方默认路径和相关说明见 [认证文档](https://github.com/Kaggle/kaggle-cli/blob/main/docs/README.md#authentication)。

本项目辅助脚本也接受 `.env` 中的 `KAGGLE_USERNAME` 与 `KAGGLE_KEY` 配对。可以通过本地编辑器填写，但不要同时配置多组来源不明的新旧凭据。只为完成教程的新成员，优先统一使用项目 token 文件。

**不要将 `.env` 当作 shell 脚本 `source`。** 此处由 Python dotenv 读取；也不要将真实密钥复制到教程或代码示例中。

## 6. 配置 ARC_API_KEY

只有需要相关 ARC 平台功能时才配置。通过 [ARC Prize 平台](https://arcprize.org/platform) 获取本人的 key，并遵循平台当前授权要求。

若项目尚无 `.env`，从 `.env.example` 复制一份；已有文件不要覆盖。在编辑器填写：

```dotenv
ARC_API_KEY=<只在你本地替换为真实ARC密钥>
ARC_BASE_URL=https://arcprize.org
ENVIRONMENTS_DIR=environment_files
RECORDINGS_DIR=recordings
```

这里的占位符不是可用 key。示例 endpoint 来自本仓库模板，不用于擅自替换 Kaggle 竞赛网关配置。

保存后：

```bash
chmod 600 .env
git check-ignore .env
```

认证信息有效、游戏接口可用和模型推理可用，是三个独立检查，不能互相代替。

## 7. 不暴露密钥的验证顺序

### A. 先做纯离线验证

在已经激活的项目虚拟环境中：

```bash
python -m scripts.archive_action_effect_history_v1 replay
python -m scripts.build_action_effect_history_v1_replay --check
python -m scripts.build_evidence_comprehension_v1 --check
```

通过表示归档/回放/问题集可复现，不表示模型能通关。直接打开 `reports/action_effect_history_v1_replay/index.html` 可查看真实历史模型回放，无需 Kaggle token。

### B. 检查 token 文件格式

```bash
python scripts/check_kaggle_config.py
```

该命令检查文件、权限及基础 notebook metadata，不发起身份认证。即使显示 `KAGGLE_CONFIG_VALID`，也不能证明服务器接受该 token；它也不是所有冻结研究 notebook 的完整检查器。

### C. 发起已获访问权限的只读请求

```bash
python scripts/phase4_install_kaggle.py kernels status daichongwei06/arc3-action-effect-history-v1
```

该辅助脚本限制为查询/下载类操作，并对已知密钥做输出替换。但仍需人工检查日志再分享，不能把它视为万能脱敏工具。

私有 notebook 返回 403/404 时，先检查访问授权和资源名称，不要立即认定 token 错误。队友可能能够认证，却无权读取负责人名下的私有 notebook。

### D. 可选 CPU 连接演练

```bash
python -m scripts.rehearse_evidence_comprehension_v1 --fault none --seconds 480
```

这会运行本地进程及假服务，产生文件并执行清理。脚本答案不是模型答案，也不会变成有效研究结论。不要用耗时全套演练代替第一次简单环境检查。

## 8. Kaggle 目标 GPU 环境不是本地开发环境

已保留的目标附件：

- Wheelhouse：`driessmit1/arc3-vllm-h100-wheelhouse-v3`。
- 模型：`qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1`。
- 目标加速器：历史真实研究使用 NVIDIA RTX Pro 6000。

Wheelhouse 名称中的 H100 不代表实际使用 H100。冻结目标包含 vLLM、Torch/CUDA 和模型依赖的独立安装、版本及文件哈希检查，不能用本地 `pip install vllm` 替代。

没有 NVIDIA runtime 的 WSL 无法因此变成目标推理机器。队员也不需要为了看回放下载约数十 GB 的模型。依赖附件的再分发权限另行检查，不应将整个 wheelhouse、用户配置或模型目录随意打包群发。

## 9. 哪些操作必须停下来请求批准

以下不属于“配环境”：

- 上传或重新运行 GPU notebook，包括为确认环境而开启交互 GPU session。
- 执行任何 reservation、launch、push、`make submit` 或 Submit to Competition 操作。
- 使用 H1/H2 holdout、改动已冻结协议、自动重试消耗完的 attempt。
- 修改 notebook owner、附件或参数后继续使用旧批准文件。

截至本指南基准版本，最新 evidence-comprehension review r1 **尚有独立审查问题，不具备发射批准**。环境安装成功或 token 认证成功不能解除这些限制。

## 10. 常见故障排查

| 现象 | 优先检查 |
|---|---|
| `No module named ...` | `sys.executable` 是否指向正确 venv；新问卷是否补装 jsonschema；不要全局乱装 |
| `No module named research` | 从仓库根目录执行支持的 `python -m scripts...` 入口 |
| `Kaggle credentials missing` | token 是否位于当前执行仓库 `.kaggle/access_token`；Windows 与 WSL 是否用了不同 clone |
| `token_permissions` | WSL Linux 文件系统内用 chmod；Windows 挂载盘权限语义可能不同 |
| 401 / 未认证 | 检查 token 是否撤销、复制错误或被旧环境变量覆盖；不贴 token 排障 |
| 403 / 404 | 私有资源权限、规则接受状态、资源 ID；不能单凭状态码断言根因 |
| 固定依赖版本安装失败 | 记录 OS、架构、Python、包索引及错误；请维护者核对，不改冻结版本凑通过 |
| vendor framework 缺失 | 新 checkout 使用 make setup，或按批准的恢复流程恢复；setup_wsl.sh 不自动补齐它 |
| GPU 检查失败 | 区分 CPU 开发与目标 CUDA 环境；不要绕过 GPU binding |
| 锁或 archive hash 不匹配 | 检查 commit 和文件变更；不要改 hash 让验证通过 |

## 11. 密钥安全与团队交接

- 只共享代码、报告、脱敏日志和准许分发的证据。不要共享本人 token 来解决团队资源权限问题。
- `.gitignore` 只防止普通新增，不会清除已经进入 Git 历史的密钥。
- 检查意外跟踪：`git ls-files .env .kaggle`。如出现实际认证文件，暂停 push 并联系维护者。
- 不把含密钥的项目目录整个 ZIP 到桌面、云盘、邮件或会议群。打包采用明确 allowlist。
- 如泄露，立即在对应平台撤销/轮换，再更新本地配置；仅删除聊天消息或 Git 当前文件不够。
- 不在分享屏幕、终端历史、issue、README、notebook 单元格或错误报告中展示密钥。

给项目负责人回报环境验收时，提交以下非敏感信息即可：

```text
操作系统 / WSL 发行版：
代码 commit：
Python 版本与解释器路径：
依赖一致性检查：通过 / 失败
历史 archive replay：通过 / 失败
HTML 重建检查：通过 / 失败
问题集检查：通过 / 失败
Kaggle 只读访问：通过 / 未配置 / 权限待授予
ARC key：已在本地配置 / 不需要 / 未配置（不要填写实际值）
是否启动 GPU：否
是否上传或计分提交：否
脱敏错误摘要：
```

## 12. 依据与适用范围

项目级细节来自基准提交中的 Makefile、`.env.example`、`config/dependency_manifest.lock`、`scripts/setup_wsl.sh`、`scripts/check_kaggle_config.py`、`scripts/phase4_install_kaggle.py` 和最新问卷 review 文档。

官方资料在整理时核对：

- [Kaggle CLI 认证](https://github.com/Kaggle/kaggle-cli/blob/main/docs/README.md#authentication)。
- [Microsoft WSL 安装](https://learn.microsoft.com/en-us/windows/wsl/install)。
- [uv 安装](https://docs.astral.sh/uv/getting-started/installation/)。

官方 CLI 的新功能不自动适用于本项目固定的 kaggle 2.2.4；本指南优先使用项目已实现的 token 加载方式。成功执行本指南意味着开发/访问环境具备相应条件，不等于实验批准、模型能力验证或比赛提交完成。
