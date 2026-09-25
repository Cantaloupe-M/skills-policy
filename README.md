# Skill 自进化实验

本项目从 **带 verifier 结果的 agent 轨迹** 中提炼可复用的操作能力，并将其编译为可供后续任务使用的 Claude Code skill。成功轨迹提供新 capability 的解决证据；失败轨迹及其重试过程也可贡献已成功执行的子操作。完整实验按任务族（family）独立训练：训练任务按 batch 和 epoch 执行并演化 skill，随后冻结最终版本，以该版本评估 held-out 任务。

> **适用范围**：这是面向 SkillFlow 实验的代码，不是通用的在线学习服务。完整协议、设计动机和约束见 [workflow.md](workflow.md)。本文档优先描述当前脚本的实际行为。

## 核心流程

```text
all task attempts (successful + failed)
        │
        ├── successful trajectories → new-capability discovery
        └── failed/retried trajectories → reflection and reuse-failure evidence
        │
        ▼
semantic clustering and representation split
        │
        ├── recurring cross-task invariant → skill-local policy
        └── instance-specific residual → searchable memory store
        │
        ▼
next training batch uses the promoted skill version
        │
        ▼
freeze final version → held-out evaluation (no evolution)
```

- **发现**：所有执行 attempt 都会被收集。verifier 通过的轨迹先产生 `experimental` policy/implementation；后续任务显式采用并通过 verifier 后才转为 `active`，来源任务或其他任务均可。失败轨迹中有明确成功子操作的路径可产生待验证证据；没有成功子操作的失败路径只保留为私有诊断。
- **抽象**：检测跨 trial 的探索摩擦与解决路径，排除瞬时网络重试、单纯语法修正和实例专属常量。
- **聚类**：按问题意图、障碍和输入类型聚合相近能力，形成稳定 capability 标识。
- **编译**：将达到跨任务支持阈值的过程性不变量编译进 family skill。用于跨 batch 聚类的参数化 atomic/workflow 证据保存在 `policy_candidates` 私有区，不进入 Agent 的检索结果；具体失败反思保存在 `memories` 检索区。已编译反思仍保留上下文、理由和结果，但过程性 lesson 由 skill 负责，避免双份指导。
- **检索**：memory 默认不注入 prompt。后续 agent 只在需要类比经验时，通过只读 `experience_memory` MCP 的 `search_memories` / `get_memory` 按需读取；返回内容是待验证的上下文，不覆盖 skill 中的 procedure。
- **评估**：训练结束后冻结版本；held-out 阶段可以重试任务，但不会根据测试结果更新、提升或选择 skill。

## 稳定 bootstrap 与受控演化

默认初始化 family skill 会使用显式指定的训练任务合同生成 v000，不进行网络搜索；`--initialization scaffold` 则只创建固定通用 scaffold，不读取训练任务内容。每个 Batch 完成后，轨迹进入私有 policy candidate 池，具体反思进入可检索 memory，并共同参与跨任务聚类；只有达到 recurrence 阈值的共享不变量才生成或更新 Policy card 及相关局部 section，并仅在适合参数化且通过静态检查时生成 `scripts` helper。单个成功轨迹不会直接重写主 workflow。


- **私有证据**：绑定、capability state、诊断和 promotion provenance 写入版本根目录的 `.evolution/`，不进入挂载给 agent 的 `.claude/skills/` tree，也不影响 runtime skill hash。
- **分区状态**：`skill_versions/memory_store.json` 的 `memories` 仅保存可检索的具体反思经验，`policy_candidates` 保存不可检索的参数化聚类证据。每批审计视图写入 `experience_memories.json`，失败重试链仍单独写入 `reflection_memories.json`。Skill 发布后，相关 memory 转为 `memory_residual`，相关 candidate 转为 `skill_factored`。每次执行只在 disposable snapshot 中生成隐藏的 `.memory/` MCP bundle，且 bundle 不包含 `policy_candidates`。
- **保护与提升**：初始 family skill 使用 `<!-- SKILL_BOOTSTRAP_START -->` / `<!-- SKILL_BOOTSTRAP_END -->` 标记持久化领域知识，`<!-- SKILL_MANAGED_START -->` / `<!-- SKILL_MANAGED_END -->` 标记可重写的流程与 policy 视图。编译器只重写 managed 区并保留 bootstrap 区；无标记的历史 `v000` 会在首次编译时自动当作 bootstrap。candidate 必须包含可复用成功子操作并改变 family package，hash 改变本身不构成提升理由。
- **实验归因**：报告结果时至少保留无 skill、seed-only 和 seed + evolution 三组，不能把 bootstrap 自身带来的收益归因为演化收益。
- **Scaffold + Evolution**：使用 `--initialization scaffold` 时，`v000` 只由固定通用 scaffold 构造；初始化阶段不会读取 train task 的 `instruction.md`/`task.toml`，也不会调用 evolution LLM。train task 仅在 `v000` 固定后进入 batch evolution。

实现入口：

- [evolution/bottleneck_pipeline.py](evolution/bottleneck_pipeline.py)：轨迹到 skill 的主流水线。
- [evolution/batch_loop.py](evolution/batch_loop.py)：批次快照、反思重试、候选提升和最终冻结。
- [evolution/exploration/skill_compiler.py](evolution/exploration/skill_compiler.py)：family skill 的增量编译。
- [evolution/memory_store.py](evolution/memory_store.py) 与 [evolution/memory_mcp_server.py](evolution/memory_mcp_server.py)：残差记忆的持久化、跨 batch 复现和只读检索。
- [run_skillflow_evolution.py](run_skillflow_evolution.py) 与 [run_skilllearnbench_evolution.py](run_skilllearnbench_evolution.py)：完整基准运行器。

## 安装与前置条件

### 基础环境

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/)

```bash
uv sync
```

演化聚类使用本地缓存的 `all-MiniLM-L6-v2` sentence-transformer 模型，并强制离线加载以保证可复现。若模型缓存于其他目录，可设置 `SKILLFLOW_EMBEDDING_MODEL` 为本地模型目录；若当前解释器缺少模型或依赖，演化会阻止发布 policy 并报告 `embedding_unavailable`，不会退化为词袋哈希聚类。

项目没有声明独立的 console-script 命令；请以 `python <script>.py` 方式运行入口脚本。

### 目录约定

根目录保留两个完整 benchmark runner，便于直接复制命令；需要 Docker 或特定数据集的辅助工具统一放在 `scripts/`：

```text
scripts/
├── datasets/
│   ├── fast_test_evolve.py                 # 离线 small_datasets 轨迹演化
│   └── skilllearnbench/
│       ├── prebuild_images.py              # 构建 SkillLearnBench task 镜像
│       └── prebuild_images.sh               # 上述脚本的 uv/.venv 启动器
└── docker/
    └── cleanup_images.sh                    # 清理 benchmark 产生的 Docker 镜像
```

如果从仓库外执行这些脚本，它们会自动定位仓库根目录；也可以先 `cd` 到仓库根目录以便日志和相对路径更直观。

旧的根目录脚本名已不再保留：`prebuild_skilllearnbench_images.sh` → `scripts/datasets/skilllearnbench/prebuild_images.sh`，`delete_images.sh` → `scripts/docker/cleanup_images.sh`，`fast_test_evolve.py` → `scripts/datasets/fast_test_evolve.py`。

### 完整基准运行

完整 benchmark 运行还需要：

- Docker（多数 Harbor 环境需要）；
- Harbor 及其可导入的 Python 环境；
- 对应的 benchmark 数据集与 canonical split 文件；
- 可达的模型 API 或 Anthropic-compatible gateway；
- 视运行环境而定的网络、代理和镜像访问权限。

## 凭据与网络配置

`llm_config.py` 定义了 `train`、`evolution`、`test` 三类模型 profile。**不要**把 API key、Bearer token、代理账号或带凭据的 endpoint 写入 README、Git 历史、命令行历史或运行日志。

Claude Code 的任务执行 profile 支持两种协议：

- `provider: anthropic`：Claude Code 直接访问该 profile 的 `base_url`。
- `provider: openai`：运行器自动启动 `docker/llm-adapter/compose.yaml` 中的 LiteLLM 适配器。Claude Code 仍发送 Anthropic Messages 请求，适配器再转发到 profile 的 OpenAI-compatible `/v1` 接口。任务容器通过外部 Docker 网络 `skillflow-llm-adapter` 访问 `http://llm-adapter-<profile>:4000`。

OpenAI profile 的上游密钥通过环境变量注入，例如：

```bash
export APIYI_API_KEY='...'
python run_skillflow_evolution.py --help
```

运行器需要 Docker Compose，并会复用同一个 profile 的适配器容器；不需要手动执行 `docker compose up`。若 API 服务不支持 OpenAI-compatible `/v1/chat/completions`，请继续使用 `provider: anthropic` 或更换上游网关。

推荐做法：

1. 通过环境变量、密钥管理服务、CI secret 或被 `.gitignore` 忽略的本地配置注入凭据。
2. 将 `configs/myevolution.yaml` 视为当前运行示例，而非可直接移植的生产配置；其中网络/代理设置必须按环境替换。
3. 如果凭据已被提交或出现在日志中，立即轮换，并检查生成的 trajectory、debug 输出和 run artifact 后再分享。
4. 如需隔离实验，可以为训练、演化和测试配置不同 profile；这不是运行器的强制要求。

两个完整 runner 也支持通过 `LLM_OVERRIDES` 一次性切换三阶段 profile。变量值是 JSON；命令行参数仍具有最高优先级：

```bash
export LLM_OVERRIDES="{\"train\":{\"provider\":\"anthropic\",\"model\":\"model-a\",\"base_url\":\"https://train.example\",\"api_key\":\"$TRAIN_API_KEY\"},\"evolution\":{\"provider\":\"openai\",\"model\":\"model-b\",\"base_url\":\"https://evolution.example/v1\",\"api_key\":\"$EVOLUTION_API_KEY\"},\"test\":{\"provider\":\"anthropic\",\"model\":\"model-c\",\"base_url\":\"https://test.example\",\"api_key\":\"$TEST_API_KEY\"}}"
python run_skillflow_evolution.py --config configs/myevolution.yaml
```

优先级为：CLI 参数 > `LLM_OVERRIDES` 环境变量 > runner 文件中的 `LLM_OVERRIDES` > `llm_config.py`。环境变量一旦设置，即使是空 JSON 对象，也不会再读取 runner 文件中的 override。建议只通过环境变量名注入密钥，避免把真实密钥放进 shell history、命令行参数或运行清单。

## 快速开始：离线轨迹演化

[scripts/datasets/fast_test_evolve.py](scripts/datasets/fast_test_evolve.py) 是轻量级的增量编译工具，适合检查“已有轨迹能否产生 skill”。它**不是**完整 benchmark runner：不启动 agent、不执行任务、不进行反思重试，也不实际运行 held-out 评估。

先仅检测轨迹、候选和聚类，不调用 LLM 或写入 skill package：

```bash
python scripts/datasets/fast_test_evolve.py --dry-run
```

对指定 trial 目录执行增量演化：

```bash
python scripts/datasets/fast_test_evolve.py \
  --job-dir small_datasets/trials \
  --family "Example Family" \
  --batch-size 3 \
  --test-count 2
```

将所有发现的 trial 用作训练，并写入单独目录：

```bash
python scripts/datasets/fast_test_evolve.py \
  --job-dir /path/to/trials \
  --family "Example Family" \
  --skills-dir /path/to/skills-output \
  --batch-size 1 \
  --test-count 0
```

### 输入与切分语义

该脚本仅扫描 `--job-dir` 的**直接子目录**，并要求每个 trial 至少包含以下一种轨迹：

```text
<trial>/agent/trajectory.json
<trial>/agent/claude-code.txt
<trial>/agent/claude_code.txt
```

脚本按 trial 目录名排序。默认 `--batch-size 3`、`--test-count 2`：末尾两个 trial 被保留为 held-out 列表，其余为训练 trial。`--test-count 0` 表示所有 trial 都参与训练。保留列表只会显示在最终摘要中，不会被这个脚本执行。

每个训练 batch 都会向同一个 `--skills-dir` 增量写入演化结果。默认输出目录为 `skills_output/fast_test_skills`。非 `--dry-run` 运行会先删除已有的目标 skills 目录；请始终为有价值的输出指定新的 `--skills-dir` 或先完成备份。

未提供 `--family` 时，脚本会从 trial 名称启发式推断 family；混合任务集请显式指定它，以避免生成过于宽泛或不准确的触发条件。

离线工具参数：`--job-dir`（默认 `small_datasets/trials`）、`--family`（自动推断）、`--output`（默认 `skills_output`）、`--skills-dir`（覆盖输出下的 `fast_test_skills`）、`--batch-size`（默认 `3`）、`--test-count`（默认 `2`，`0` 表示全部训练）、`--dry-run`、`--no-llm` 和 `--verbose`。

## 运行参数

### Evolution 共用参数

`--initialization`、`--min-occurrences`、`--batch-size`、`--max-retries`、`--train-epochs` 和 `--train-shuffle-seed` 由 [evolution/cli.py](evolution/cli.py) 统一注册。`run_skillflow_evolution.py` 和 `run_skilllearnbench_evolution.py` 中这些参数的含义一致。

- `--initialization`：`task-derived`（默认）从 train task 合同合成 `v000`；`scaffold` 使用固定通用模板，初始化不接触 train task 内容。
- `--min-occurrences`：候选能力需要被多少个不同 task 支持后才允许发布；论文对齐默认为 `3`，设置为 `1` 对应跨任务证据门控消融。
- `--batch-size`：一个训练 batch 中的任务数，默认 `3`。
- `--max-retries`：单个失败任务的**最大总尝试次数**，包含首次执行。例如 `3` 最多执行三次；`0` 禁用重试且只执行一次，默认 `2`。
- `--train-epochs`：完整重复该 family 训练集的次数；每个 epoch 从最新已发布版本继续，默认 `2`。
- `--train-shuffle-seed`：每个 epoch 重排训练任务的基础随机种子，默认 `0`；相同 seed 可复现相同顺序。
- `--min-reward`、`--demotion-threshold`：演化评估阈值。
- `--evolution-provider`、`--evolution-model`：演化阶段使用的模型覆盖。
- `--max-evolution-workers`：演化处理的最大 worker 数，默认 `3`。

### SkillFlow 参数

SkillFlow 的入口和常用启动方式：

```bash
python run_skillflow_evolution.py \
  --config configs/myevolution.yaml \
  --dataset-path data/skillsflow/<family> \
  --only-family <family> \
  --initialization scaffold \
  --batch-size 3 \
  --max-retries 2 \
  --train-epochs 3
```

不传 `--config` 时，runner 默认使用 `configs/myevolution.yaml`；在可复现实验中建议显式写出它。family 名称必须存在于 [utils/skillflow_family_splits.json](utils/skillflow_family_splits.json)，该文件定义 canonical train/test 切分。

- `--batch-concurrency`：同一 batch 内最大并行任务数；与 `--batch-size` 不同。
- `--family-concurrency`：多个 family 的独立运行进程最大并行数；默认 `2`。设为 `1` 可串行运行，family 内任务并行仍由 `--batch-concurrency` 控制。
- `--run-root-dir`：覆盖运行产物根目录，默认 `runs/skillflow`。

SkillFlow runner 的其余可调参数：

| 参数 | 默认值 | 作用 |
| --- | --- | --- |
| `-c, --config PATH` | `configs/myevolution.yaml` | Harbor/模型等基础配置 |
| `--dataset-path PATH` | 配置决定 | 数据集目录；和 `--only-family` 一起使用时必填 |
| `--batch-concurrency N` | `3` | 单个 batch 内并行任务数 |
| `--family-concurrency N` | `2` | 并行 family 数 |
| `--skip-existing-family` / `--no-skip-existing-family` | 关闭 | 跳过已有输出的 family |
| `--copy-task-skills` | 关闭 | 将任务自带 skill 一并复制到运行环境 |
| `--fast-test` | 关闭 | 将 Claude Code 限制为 5 轮并固定 reward=1 |
| `--train/evolution/test-llm-{provider,model,base-url,api-key}` | profile 配置 | 覆盖对应阶段的模型连接参数 |
| `--run-root-dir PATH` | `runs/skillflow` | 覆盖运行产物根目录 |

其中 `--only-family NAME` 是兼容性的隐藏参数，可用于只跑一个 family；可用 family 以 `utils/skillflow_family_splits.json` 为准。

若不使用 `--only-family`，runner 会按配置中的数据集组织并运行所有可解析的 family。

### SkillLearnBench 参数

SkillLearnBench 按上游 README 定义的 6 个真实世界类别维护共享 skill store，而不是把 20 个 task 各自当作一个 family。固定切分来自 [utils/skilllearnbench_splits.json](utils/skilllearnbench_splits.json)：每个类别按最接近 8:2 的整数计数分层，总计 `80 train / 20 test`。

runner 直接复用上游 `evaluate_skills.py` 定义的 20 个 task 级镜像：每个父任务使用 `<task>-1/environment` 构建一次 `eval-hyper-<task>:stable`，该任务的所有 instance 共用依赖层。每次 trial 启动后，runner 会依据当前 instance 的 Dockerfile `COPY` 指令，将非 skill 的输入文件覆盖到容器内对应路径；具体 instance 的 instruction 和 tests 仍在每次 trial 启动时由上游 runner 注入或挂载。

```bash
./scripts/datasets/skilllearnbench/prebuild_images.sh \
  --dataset-root /data01/syt/研究项目/skill自进化/SkillLearnBench \
  --workers 3
```

已有官方镜像时不需要执行预构建脚本。缺少镜像时，可以用 `--only-category information-retrieval` 只构建一个类别所需的父任务镜像；脚本会生成如 `eval-hyper-enterprise-information-search:stable` 的 task 级 tag。演化 runner 会把同一父任务下的 instance 映射到该镜像，并在容器启动后注入当前 skill 快照。预构建工具参数如下：

| 参数 | 默认值 | 作用 |
| --- | --- | --- |
| `--dataset-root PATH` | `/data01/syt/研究项目/skill自进化/SkillLearnBench` | SkillLearnBench 数据集根目录 |
| `--split-file PATH` | `utils/skilllearnbench_splits.json` | 固定 train/test 切分 |
| `--only-category NAME` | 全部 | 只构建指定类别；可重复传入 |
| `--task-name NAME` | 全部 | 只构建指定父任务；可重复传入 |
| `--agent NAME` | `claude-code` | 使用上游定义的 agent 安装层 |
| `--workers N` | `3` | 并行构建数 |
| `--retries N` | `3` | 每个镜像失败后的最大重试次数 |
| `--dry-run` | 关闭 | 只校验并打印待构建镜像，不调用 Docker |

清理 benchmark 镜像（包括 `eval-hyper-*` SkillLearnBench 镜像）时运行 `./scripts/docker/cleanup_images.sh`；该操作会删除匹配的本地镜像及其容器，请先确认当前 Docker 主机上没有需要保留的同名资源。

```bash
python run_skilllearnbench_evolution.py \
  --dataset-root /data01/syt/研究项目/skill自进化/SkillLearnBench \
  --initialization scaffold \
  --run-root-dir runs/skilllearnbench-scaffold-evolution \
  --family-concurrency 3 \
  --batch-size 3 \
  --batch-concurrency 3 \
  --max-retries 2 \
  --train-epochs 3
```

`--family-concurrency` 控制同时运行的 family 子进程数，默认为 `2`。每个 family 使用独立的 spawn 进程，进程内的 task 并发由 `--batch-concurrency` 控制。

SkillLearnBench 不创建时间戳运行目录，产物固定写入 `<run-root-dir>/<category>/`（默认 `runs/skilllearnbench-evolution-retry02/<category>/`）。默认情况下，已有完整 `result.json` 的 category 会在后续运行中跳过；中断后仅留下目录但没有 `result.json` 的 category 会重新运行。需要显式重跑已完成 category 时使用 `--no-skip-existing-family`。

当 `train` 或 `test` profile 使用 `provider: openai` 且 agent 为 Claude Code 时，runner 会在启动 family 进程前复用与 SkillFlow 相同的 LiteLLM adapter，并将 SkillLearnBench 的任务容器加入 `skillflow-llm-adapter` 网络。任务容器中的 Claude Code 仍使用 Anthropic Messages 协议，无需修改上游 SkillLearnBench 数据集代码。

`--only-category` 可重复传入；可选值为 `software-engineering`、`information-retrieval`、`productivity-tools`、`data-analytics`、`content-creative` 和 `utilities-other`。`--only-family` 作为兼容别名仍可使用。每个运行目录会写入实际 train/test task ID 的 `split_manifest.json`，held-out test 只使用训练结束后冻结的 skill 版本。

SkillLearnBench runner 的参数完整列表：

| 参数 | 默认值 | 作用 |
| --- | --- | --- |
| `--dataset-root PATH` | 环境相关的默认路径 | SkillLearnBench 数据集根目录 |
| `--split-file PATH` | `utils/skilllearnbench_splits.json` | 固定类别切分 |
| `--run-root-dir PATH` | `runs/skilllearnbench-evolution-retry02` | 运行产物根目录 |
| `--only-category NAME` | 全部 | 只运行一个或多个类别；可重复传入 |
| `--agent NAME` | `claude-code` | 上游 agent 名称 |
| `--model NAME` / `--test-model NAME` | profile 配置 | 覆盖 train/test agent 模型 |
| `--max-steps N` | `100` | 单次 agent trial 最大步数 |
| `--batch-concurrency N` | `3` | 类别内 batch 并行任务数 |
| `--family-concurrency N` | `2` | 并行类别进程数 |
| `--skip-existing-family` / `--no-skip-existing-family` | 跳过已完成 | 是否跳过已有 `result.json` 的类别 |
| `--dry-run` | 关闭 | 只校验并打印固定切分 |
| `--train/evolution/test-llm-{provider,model,base-url,api-key}` | profile 配置 | 覆盖对应阶段模型连接参数 |

## 一次完整 family run 做什么

对于每个 family，完整 runner 遵循以下实际执行顺序：

1. 读取固定的 canonical train/test split，初始化 family 的 skill version store（`v000`）。
2. 每个 epoch 按 `--train-shuffle-seed` 重排训练任务，按 `--batch-size` 取 batch，并从当前版本创建该 batch 的 skills snapshot。
3. 所有任务都使用同一快照执行；失败任务可在该快照上获得 reflection 并重试。
4. batch 结束后，收集其结果；从 verifier 通过轨迹或失败轨迹中的成功子操作提炼 reusable capability。
5. 将编译出的候选 skills 提升为下一版本，供后续训练 batch 使用。
6. 所有 epoch 的训练 batch 完成后，冻结最终 skill 版本及其内容哈希。
7. 使用这个冻结版本执行 held-out test；测试轨迹不会反馈到 skill 演化或版本选择。

没有成功子操作的失败轨迹会产生诊断产物：可解析的失败轨迹写入 `failure_diagnostics.json`，缺少 `trajectory.json`/Claude log/session log 的失败 attempt 写入 `missing_trajectory_diagnostics.json`。它们不会生成 script、修改已发布操作流程或提升 skill version。

典型运行产物包括 family split manifest、`train/epoch_*/batch_*/batch_summary.json`、各次 task attempt 的 trajectory/反思记录、skills version store、演化摘要和最终版本哈希。使用 `--train-epochs N` 时，每个 epoch 都会从最新已发布 skill 版本继续，并按 `--train-shuffle-seed` 确定性重排训练任务。两种 runner 的目录结构并非完全相同，因此应以每次 run 输出的路径为准。

## 生成的 skill 包

编译器为每个 family 维护 canonical skill binding，并将可分发 skill 与演化元数据分开保存。结构大致如下：

```text
<skills-root>/
├── <skill-slug>/
│   ├── SKILL.md
│   └── scripts/                 # 仅在有匹配的通用 recipe 时生成
│       └── capabilities/
│           └── <helper>.py
└── .evolution/
    ├── family_skill.json        # family → canonical skill slug
    └── state/
        └── <skill-slug>.json    # 机器可读的 capability state
```

- `SKILL.md` 是面向 agent 的操作手册，包含适用场景、输入、步骤、验证和常见陷阱。
- `scripts/capabilities/` 仅承载已审查、参数化的通用 helper；不会把某个任务的原始命令、绝对路径、业务常量或源数据写入 skill。
- `.evolution/state/` 保存证据与状态，不属于 agent 应直接加载的 skill 内容。
- 任务或后续工具也可能附带 `references/`、`assets/` 等补充文件，但它们不是每次编译都保证生成的内容。

## 直接调用 Python API

如需把已完成任务目录接入其他执行器，可直接调用 `evolve_from_job_dir`：

```python
from pathlib import Path
from evolution import evolve_from_job_dir

report = evolve_from_job_dir(
    job_dir=Path("/path/to/completed-trials"),
    task_family="Example Family",
    skills_dir=Path("/path/to/skills"),
    dry_run=True,
)
print(report.summary)
```

该 API 负责加载轨迹、解析探索过程、发现候选、聚类并编译 family skill。设置 `dry_run=True` 时仅返回检测报告，不进行 LLM 语义抽象或 skill 写入。

## 协议状态与可复现性

[workflow.md](workflow.md) 记录了项目的完整协议、指标建议和更严格的 snapshot/隔离设计目标。使用本仓库结果时请注意：

- 离线快速脚本只做轨迹驱动的编译演示，不能替代独立 held-out benchmark。
- 完整 runner 会在 held-out 前冻结最终版本；但任务执行本身仍可发生重试，重试不等于 test-time evolution。
- 可复现性依赖于固定 split、数据集版本、Docker/runtime 镜像、模型与 gateway 配置、网络条件以及密钥注入方式。
- artifact 路径和运行时行为在不同 benchmark 之间可能有所不同；请保留 split manifest、版本哈希和 run artifacts 以支持审计。

## 开发与检查

```bash
# 查看所有入口参数
python scripts/datasets/fast_test_evolve.py --help
python run_skillflow_evolution.py --help
python run_skilllearnbench_evolution.py --help
python scripts/datasets/skilllearnbench/prebuild_images.py --help

# 静态检查（开发依赖已通过 uv sync --group dev 安装时）
uv run ruff check .
uv run mypy evolution
```
