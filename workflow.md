# Skills 自进化工作流

本文档描述当前代码实际执行的 Skills 自进化流程。核心目标与论文一致：先从每次执行中保留实例级经验，失败时产生结构化反思记忆，再对跨任务重复出现的经验进行语义聚类，最后把共享的过程性规律编译进稳定的 family Skill。

## 1. 总体流程

```text
初始化 family Skill，得到 v000
        │
        ▼
为当前 batch 创建固定的 skills_snapshot
        │
        ▼
执行任务初始尝试 attempt_01
        │
        ├── 成功 ──► 保存成功轨迹
        │
        └── 失败
              │
              ▼
        根据轨迹和 verifier 生成反思
              │
              ▼
        将反思注入下一次 retry
              │
              ├── retry 成功 ──► 反思记忆获得成功验证
              └── retry 失败 ──► 继续反思和 retry，直到预算耗尽
        │
        ▼
暂存 batch 内所有 task 的所有 attempt
        │
        ├── 原始轨迹证据
        ├── verifier 成败标签
        └── reflection_attempt_*.md 反思记忆
        │
        ▼
解析 ExplorationTrace，并建立“失败反思 → 紧接着的 retry 结果”关联
        │
        ▼
生成两条候选证据流
        ├── 轨迹候选：成功步骤、短工作流、失败诊断
        └── 反思候选：失败现象、根因、纠正动作
        │
        ▼
参数化并按候选类型进行跨任务语义聚类
        │
        ▼
跨任务支持数和 verifier 证据门控
        │
        ▼
编译 candidate Skill
        ├── 创建或更新 Policy card
        ├── 局部修补相关 Skill section
        └── 可选生成参数化 helper script
        │
        ▼
Skill 内容发生变化时发布 v001、v002……
        │
        ▼
下一 batch 使用新版本；训练结束冻结为 final
```

## 2. 初始化 Skill 版本

每个 task family 使用独立的 Skill 版本存储。初始版本为 `v000`，其中包含：

```text
v000/
├── manifest.json
├── .claude/skills/<family-slug>/
│   ├── SKILL.md
│   ├── references/policies/
│   └── scripts/
│       ├── experimental/
│       └── capabilities/
└── .evolution/
    ├── manifest.json
    ├── lineage.json
    ├── metrics.json
    └── evidence.jsonl
```

`SKILL.md` 是 agent 实际可见的 family 主工作流；`.evolution` 保存私有的策略注册表、证据、指标和版本血缘，不作为任务答案直接暴露给 agent。

每个 batch 开始时，代码读取最新的 `v00N` 并复制出独占的 `skills_snapshot`。同一 batch 的初始执行和所有重试都使用同一快照，因此本 batch 学到的新内容只能影响后续 batch 或后续 epoch，不会泄漏给同 batch 中尚未完成的尝试。

## 3. 单个任务的执行、反思和重试

### 3.1 初始尝试

任务首先使用当前 batch 的 `skills_snapshot` 执行 `attempt_01`。执行完成后由 benchmark verifier 给出 `success`、`reward`、失败检查和异常信息。

- 初始尝试成功：直接保存轨迹，不生成失败反思，也不重试。
- 初始尝试失败：进入反思与重试循环。

因此，没有 `reflection_attempt_*.md` 不一定是遗漏；如果任务第一次就成功，这是预期行为。

### 3.2 生成 verifier-grounded 反思

失败后，`evolution/batch_reflection.py` 从本次失败中构造反思证据包，包括：

- task 和 family；
- reward 与异常；
- task objective 和 constraints；
- verifier 失败检查；
- verifier feedback；
- 编号后的关键轨迹步骤；
- 可能与失败相关的候选步骤。

反思模型必须输出以下结构：

```text
FAILURE OBSERVABLE: verifier 或运行时观察到的失败
CAUSAL STEP(S): 导致失败的轨迹步骤，无法判断时为 UNKNOWN
CAUSAL EVIDENCE: verifier 检查与轨迹证据
DIAGNOSIS CONFIDENCE: confirmed、likely 或 insufficient-evidence
ROOT CAUSE: 根因
CORRECTIVE ACTION: 下一次尝试应采用的纠正动作
MISSING: 缺失的技能、工具或验证能力
```

每次失败反思都会写入失败 attempt 的目录：

```text
reflection_input_attempt_NN.json
reflection_attempt_NN.md
retry_brief_attempt_NN.md
```

其中：

- `reflection_input_attempt_NN.json` 保存生成反思时使用的证据；
- `reflection_attempt_NN.md` 是完整反思记忆，也是后续自进化的输入；
- `retry_brief_attempt_NN.md` 是脱敏后注入下一次 retry 的内容。

绝对路径、凭据和可能泄露预期答案的 verifier 内容会在进入 retry prompt 前进行清理。

### 3.3 重试预算

当前 `EvolutionConfig.max_retries` 保留了历史字段名，但实际表示总尝试次数，而不是“初始尝试之外的重试次数”。

例如：

```text
max_retries = 3
```

表示最多执行：

```text
attempt_01：初始尝试
attempt_02：第一次反思引导的重试
attempt_03：第二次反思引导的重试
```

对应的真正 retry budget 为 `max_attempts - 1`。任何一次尝试成功后，当前任务的反思重试循环立即结束。

## 4. 保存所有 attempt，而不只保存最终结果

一个 batch 执行结束后，`BatchEvolutionLoop._stage_batch_outcomes()` 将每个任务的每次尝试复制到：

```text
train/epoch_NNN/batch_NNN/evolution/staged_batch/
├── batch_evidence.json
├── batch_summary.json
└── <task-name>/
    ├── attempt_manifest.json
    └── attempts/
        ├── attempt_01/
        │   ├── agent/trajectory.json
        │   ├── result.json
        │   ├── verifier/
        │   └── reflection_attempt_01.md
        ├── attempt_02/
        └── attempt_03/
```

`attempt_manifest.json` 为每个 attempt 保存：

- attempt number；
- success 和 reward；
- exception；
- 是否为最终 attempt；
- reflection 文件列表；
- verifier outcome 摘要；
- 原始 trajectory 是否存在。

这一步保证初始失败、每次重试以及最终成功都不会被最终结果覆盖。

## 5. 加载轨迹和反思记忆

`evolution/trajectory_loader.py` 按以下顺序加载原始轨迹：

1. `agent/trajectory.json`；
2. `agent/claude-code.txt`；
3. `agent/claude_code.txt`；
4. `sessions/agent.log`。

同时显式读取 `reflection_attempt_*.md`。反思不再被当作普通日志忽略，而是和产生它的失败 attempt 一起传给演化管线。

如果原始轨迹因为容器权限或挂载问题缺失，但反思文件仍然存在，则保留该反思记忆参与后续处理，同时在 `missing_trajectory_diagnostics.json` 中记录原始证据缺失。这样既不会丢掉反思，也不会把缺失轨迹伪装成完整证据。

## 6. 构造 ExplorationTrace 和反思验证关系

每个 attempt 被解析成一个 `ExplorationTrace`，其中包含：

- task、family、attempt number；
- verifier 是否通过和 reward；
- 原始 steps；
- tool calls、thinking、errors 和 artifacts；
- 使用过的 Skill、Policy、implementation 和 script；
- 该失败 attempt 产生的 reflection；
- reflection 紧接着指导的 retry 是成功、失败还是缺失。

对于同一个 task，代码按 attempt number 排序。一条反思只由紧接着的下一次 retry 验证，不能被更晚的成功追溯性验证。若 `attempt_N` 的反思直接指导 `attempt_N+1`，则记录：

```text
reflection_retry_outcome = success | failure | missing
reflection_verified_by_retry = (reflection_retry_outcome == success)
```

例如：

```text
attempt_01：失败，产生 R1
attempt_02：失败，说明 R1 对应的直接 retry 失败，并产生 R2
attempt_03：成功，说明 R2 对应的直接 retry 成功
```

此时 R1 的 `reflection_retry_outcome=failure`，保留为失败或未验证方法；只有 R2 的 `reflection_retry_outcome=success`，获得正向 verifier 支持。

代码还会为每条“反思 -> 紧邻 retry”边构造 `retry_transition`，而不是只查看任务的最终轨迹：

| 字段                                         | 含义                          |
| -------------------------------------------- | ----------------------------- |
| `from_attempt` / `to_attempt`            | 该反思连接的直接前后 attempt  |
| `retry_verifier_passed`                    | 紧邻 retry 是否通过 verifier  |
| `source_operations` / `retry_operations` | 两次 attempt 的参数化操作序列 |
| `retained_operations`                      | retry 中保留的操作            |
| `added_operations`                         | retry 新增的操作              |
| `removed_operations`                       | retry 移除的操作              |

因此上例会产生两条独立的变化证据：R1 对应 `attempt_01 -> attempt_02`，新增操作与一次失败 retry 关联；R2 对应 `attempt_02 -> attempt_03`，新增操作与一次成功 retry 关联。成功关联可以作为正向方法假设，失败关联保留为失败方法、约束或诊断证据，但二者都不被表述为严格的单因素因果证明。

需要注意：这表示该反思处于成功重试链中，是 verifier-grounded 的采用证据；它并不在逻辑上证明成功完全由某一句反思单独造成。因此后面仍然要求跨任务重复和语义聚类，避免把单次偶然成功直接编译成稳定规则。

## 7. 从反思生成实例级 Reflective Memory

`evolution/reflection_memory.py` 将每条反思转成论文形式的实例级记忆：

```text
memory = (context, observation, lesson, rationale)
```

当前字段映射为：

| 记忆字段        | 当前实现来源                                       |
| --------------- | -------------------------------------------------- |
| `context`     | task、family、attempt number、reflection 文件      |
| `observation` | `FAILURE OBSERVABLE`                            |
| `lesson`      | `CORRECTIVE ACTION`                              |
| `rationale`   | `ROOT CAUSE`，缺失时使用 `CAUSAL EVIDENCE`     |

`outcome`、`verified_by_retry`、`retry_outcome` 和 `retry_transition` 作为 verifier 证据元数据额外保留，不取代论文四元组中的 `observation`。

一个任务可以产生多条独立 memory。`reflection_memories.json` 同时写入 `task_retry_episodes`，按 task 保存全部 attempt、每条 reflection memory 的 ID、直接 retry 结果和操作变化。例如三次尝试会保留为：

```text
task_retry_episode
├── attempt_01 + R1 + transition(01 -> 02, failure)
├── attempt_02 + R2 + transition(02 -> 03, success)
└── attempt_03 + verifier success
```

这些 memory 分别参与后续 `intent + obstacle` 聚类；同一任务的多条反思不会被压成“只看最终成功”的单条记录，也不会因为数量多而虚增跨任务 support。

反思候选的三个语义字段为：

```text
intent   = FAILURE OBSERVABLE
obstacle = ROOT CAUSE 或 CAUSAL EVIDENCE
resolution = CORRECTIVE ACTION
```

其中只有 `intent + obstacle` 用于聚类；`resolution` 在聚类后作为带成败标签的方法证据交给策略归纳。

检索记忆和聚类候选采用不同表示：

- `memories` 保留文件名、单元格、数值和具体纠正动作，只清理凭据、绝对路径及可能泄露答案的 verifier 比较，并限制长度；
- `policy_candidates` 额外把路径和数值参数化，用于跨任务聚类，不暴露给 Agent；
- 成功轨迹中的 atomic substep 和短 workflow 只进入 `policy_candidates`，不会伪装成可检索记忆。

只要 staged batch 中存在反思记忆，就会生成：

```text
reflection_memories.json
```

其中保存每条记忆的 context、outcome、lesson、rationale、`verified_by_retry`、`retry_outcome` 和实际送入聚类的文本，便于审计反思是否真正参与自进化。

## 8. 候选发现：轨迹流和反思流

当前演化阶段并行使用两条证据流。

### 8.1 轨迹候选

从原始 trajectory 中提取：

- verifier 通过轨迹中的成功 atomic substep；
- verifier 通过轨迹中的短 workflow；
- 工具失败后恢复的过程；
- 最终被 verifier 拒绝的 artifact 诊断。

### 8.2 反思记忆候选

每条 `reflection_attempt_*.md` 形成一个 `recovery_candidate`：

- 紧接着的 retry 成功：`evidence_label = verified_success`；
- 紧接着的 retry 失败或缺失：`evidence_label = unresolved_failure`，并另外保留 `retry_outcome`。

这意味着“失败后重试成功”的任务不会只贡献最后一次成功轨迹，还会贡献导致重试的反思根因和纠正动作。

### 8.3 候选类型和证据标签

| `candidate_kind`     | 来源                       | 可能的标签                                                      |
| ---------------------- | -------------------------- | --------------------------------------------------------------- |
| `atomic_substep`     | 成功轨迹中的单个参数化操作 | `verified_success`                                            |
| `workflow`           | 成功轨迹中的相邻操作序列   | `verified_success`                                            |
| `recovery_candidate` | 轨迹失败模式或反思记忆     | `verified_success`、`tool_recovery`、`unresolved_failure` |

`tool_recovery` 只表示某个局部命令恢复成功，但整个任务没有通过 verifier。它可以作为失败方法进入同一问题 cluster 供 LLM 对比，但不能单独增加发布所需的 qualifying support，也不能直接发布为 Skill Policy。

## 9. 跨任务语义聚类

`evolution/bottleneck_clusterer.py` 先按以下类型分池：

```text
recovery_candidate
atomic_substep
workflow
```

不同类型不会混入同一个 cluster，但同一 `recovery_candidate` cluster 可以同时包含成功和失败的方法。每个候选用以下内容生成 embedding：

```text
intent: <参数化后的意图或失败现象>
obstacle: <参数化后的根因或过程障碍>
```

`resolution` 不参与 cluster membership。它在聚类之后以带结果标签的形式保留：

```text
source
outcome
retry_outcome
resolution
```

因此，只要 `intent + obstacle` 相似，不同解决方法仍会进入同一个问题 cluster，交由后续 LLM 比较哪些方法成功、哪些失败。

当前默认 embedding 模型为：

```text
all-MiniLM-L6-v2
```

可通过环境变量 `SKILLFLOW_EMBEDDING_MODEL` 修改。

当前聚类条件：

- cosine similarity 阈值为 `0.82`；
- 新候选必须与 cluster 中每个已有成员都达到阈值；
- `cluster.support` 按不同 `task_name` 数量计算，不按 attempt 数量计算；
- 默认至少需要 `min_occurrences = 3` 个不同任务支持，与论文实验中的 `m_min = 3` 一致。

因此，同一任务重试三次产生的三条相似反思不能单独满足“三个不同任务支持”的要求。它们会被完整保留，但只有相同过程性规律在不同任务中重复出现时，才满足论文所说的 cross-task recurrence。

如果 embedding 模型或依赖不可用，当前实现会返回 `embedding_unavailable`，不会悄悄退化成关键词聚类。

## 10. 聚类后的发布门控

聚类后按证据类型处理：

### 同时包含成功和失败方法的 cluster

所有可用 recovery 候选先按 `intent + obstacle` 一起聚类。若 cluster 达到不同任务的 qualifying support 且至少包含一条 `verified_success`，它可以用于创建 experimental Policy。qualifying support 只统计 `verified_success` 和 `unresolved_failure`，不统计单纯的 `tool_recovery`。策略设计器只把成功 resolution 作为 procedure 的正向证据；失败 resolution 用于生成 constraints、recovery 或 validation gate。

### 持续失败的反思

完全不含成功证据的 `unresolved_failure` cluster，仍必须在多个不同任务中重复出现，才可以形成 experimental recovery Policy。单个失败只保存在 `failure_diagnostics.json` 和 `reflection_memories.json`，不会直接成为稳定指导。

### 局部工具恢复但任务最终失败

`tool_recovery` 可以进入同问题 cluster 作为失败方法，但不计入发布门槛，也不会作为正向 procedure 证据，防止把“命令执行成功”错误等同于“任务解决成功”。

### 没有可复用证据

若没有满足条件的 cluster，也没有可用于更新 workflow 的 verifier-backed 成功证据，则报告：

```text
publication_block_reason = no_reusable_evidence
```

此时不会发布新的 Skill 版本。

## 11. 将 cluster 编译为 Skill

演化不会直接修改已发布版本，而是从当前版本复制一个 candidate：

```text
current v00N
    └── copy ──► batch/evolution/candidate
```

`compile_family_skill()` 按以下顺序修改 candidate。

### 11.1 用新成功证据转正已有 Policy

在创建本 batch 的新 Policy 之前，先检查以前版本中的 experimental Policy 是否在当前 batch 被 agent 显式采用并通过 verifier。

Policy 转为 active 通常要求：

- Policy 已经有来源 observations；
- 当前 trace 通过 verifier；
- trajectory 中能检测到对应 Policy ID 或公开 slug；
- implementation 转正还需要检测到 implementation ID；
- 带脚本的 implementation 还需要检测到对应脚本调用。

这样，新建 Policy 不会在创建它的同一批次中自行证明自己有效。

### 11.2 更新 `SKILL.md` 主工作流

论文对齐的主 pipeline 不再让原始 batch 轨迹直接重写整个主 workflow。未达到 recurrence 阈值的参数化单例证据进入私有 `policy_candidates`；具体反思另存为可检索 memory。达到阈值后，共享不变量通过 Policy card 和与该 Policy 绑定的局部 section patch 进入 Skill。这阻止单个成功轨迹绕过 candidate→policy 门控，也避免通用 workflow 污染 memory 检索。

`compile_family_skill()` 仍保留显式 `workflow_traces` 接口供独立工具调用；两个完整 benchmark runner 走论文对齐 pipeline，传入空的 workflow 证据集。

### 11.3 创建或更新 Policy card

每个合格 cluster 被设计为结构化策略：

```text
trigger
procedure
constraints/invariants
recovery
validation
```

新 Policy 默认状态为 `experimental`。它被写入：

```text
references/policies/<policy-slug>.md
```

完整的 observations、task fingerprint、证据标签和 implementation 状态保存在私有 `.evolution/lineage.json`。

### 11.4 局部修补相关 section

编译器根据 cluster 的 intent、obstacle 和 proposal，从当前 `SKILL.md` 中检索相关 heading section。一个 cluster 最多替换一个 section，用于把策略放到实际决策点附近，例如：

- workflow；
- validation；
- recovery。

Policy card 保持可单独审计，同时其链接会被放置到相关 section 附近，而不是全部堆在 Skill 末尾。

### 11.5 可选 helper script

若 cluster 中存在重复、确定性、适合参数化的步骤，可以生成 Python helper：

```text
scripts/experimental/<helper>.py
```

脚本必须通过 AST 和安全检查，不能包含网络调用、shell 执行、隐藏路径、凭据或破坏性操作。implementation 获得后续 verifier-backed 显式采用证据后，才可进入：

```text
scripts/capabilities/<helper>.py
```

### 11.6 去重和写回

完成 Policy 局部 patch 后，编译器对重复的 planning、checking 和 validation 条目做确定性压缩，然后写回：

- `SKILL.md`；
- `references/policies/*.md`；
- `scripts/experimental/*.py`；
- `scripts/capabilities/*.py`；
- `.evolution/lineage.json`；
- `.evolution/evidence.jsonl`；
- `.evolution/metrics.json`；
- `.evolution/workflow_updates.jsonl`；
- `.evolution/skill_patches.jsonl`。

## 12. 发布新版本

candidate 编译完成后计算整个运行时 Skill tree 的 hash。

- candidate 缺少 family Skill：不发布；
- pipeline 返回 publication block：不发布；
- candidate hash 与当前版本相同：标记为 `unchanged`，不发布；
- candidate hash 发生变化：复制为新的不可变版本 `v001`、`v002`……。

表示转换与此发布门同步：candidate 只编译但未发布时仍保持 `representation=candidate`，对应反思仍保持 `representation=memory`；只有 `promote_candidate_version()` 成功后，二者才分别转为 `skill_factored` 和 `memory_residual`，并在批次审计文件中同步该状态。

发布后，下一个 batch 读取最新版本并创建新的 snapshot。因此 Skills 的变化顺序是：

```text
batch 1 使用 v000
batch 1 结束后发布 v001
batch 2 使用 v001
batch 2 结束后可能发布 v002
...
```

训练结束后，最新版本被冻结为：

```text
final/
```

## 13. Held-out test 阶段

当前 held-out test 使用冻结后的 final Skill 和训练期冻结的 residual memory store，但调用的是不带反思重试的 `execute_batch()`：

- test task 不进行 reflection retry；
- test task 不参与训练期聚类；
- test task 不更新 Skill；
- test task 可以通过只读 MCP 检索训练期 memory，但不会写入或重新排序 memory store；
- test 结果用于评估已经学到的 Skill 是否可以迁移。

这样可以避免在测试任务上继续学习造成数据泄漏。

## 14. 失败后重试成功的完整例子

假设三个不同训练任务都出现“修改了目标单元格，但没有验证值是否真的变化”的问题。

### Task A

```text
attempt_01：失败
reflection：根因是修改操作为 no-op；纠正动作是写入前后比较并运行 verifier
attempt_02：成功
```

Task A 的反思候选被标记为 `verified_success`，但 support 只有一个 task，默认还不会形成可发布 cluster。

### Task B

```text
attempt_01：失败
reflection：根因同样是未检测 no-op 修改；纠正动作是验证目标值变化
attempt_02：成功
```

Task B 的反思也被标记为 `verified_success`，但默认阈值下 `support=2` 时仍保留为 memory。

### Task C

```text
attempt_01：失败
reflection：根因同样是写入后没有重新读取目标值；纠正动作是重新读取并校验
attempt_02：成功
```

参数化后，三条反思的 intent 和 obstacle 语义相似度达到阈值，并且来自三个不同 task：

```text
cluster.support = 3
```

该 cluster 随后可以被编译成类似以下过程性策略：

```text
Trigger: 当任务要求修改现有 artifact 中的目标值时
Procedure: 读取原值，计算新值，拒绝 no-op patch，写入后重新读取
Constraint: 保持无关内容不变
Recovery: 若新旧值相同，重新检查方向和 authoritative field
Validation: 运行 task verifier，并显式确认目标值已经变化
```

这个策略来自三条实例级反思的共享不变量，而不是直接复制 Task A、Task B 或 Task C 的文件名、数值或答案。

## 15. 关键配置

| 配置                         | 当前含义                          | 默认值         |
| ---------------------------- | --------------------------------- | -------------- |
| `batch_size`               | 每个演化 batch 的任务数           | 由入口配置决定 |
| `max_retries`              | 包含初始尝试在内的最大总尝试数    | `3`          |
| `train_epochs`             | family 训练任务的完整遍历轮数     | `1`          |
| `train_shuffle_seed`       | 每个 epoch 的任务洗牌种子         | `0`          |
| `min_occurrences`          | cluster 需要的不同 task 支持数    | `3`          |
| `include_failure_evidence` | 是否让失败轨迹和失败反思参与发现  | `true`       |
| `strict_cross_task`        | Policy 后续验证是否要求跨任务证据 | `true`       |
| `require_policy_use`       | Policy 转正是否要求轨迹中显式采用 | `true`       |
| `immediate_promotion`      | 是否跳过后续采用验证直接转 active | `false`      |

## 16. 如何审计一次运行是否真的发生了自进化

不能只看最终成功率。建议按以下顺序检查：

1. 检查 `attempt_manifest.json`，确认失败任务是否存在多个 attempt。
2. 检查失败 attempt 下是否存在 `reflection_attempt_*.md`。
3. 检查后续 attempt 的 `success`，确认是否存在失败转成功。
4. 对存在失败反思的 batch，检查 `reflection_memories.json`，确认反思被提取，并查看 `retry_outcome` 和 `verified_by_retry`；若所有任务初始成功，该文件可以不存在。
5. 检查 `failure_diagnostics.json`，确认持续失败的经验没有被误标为成功策略。
6. 检查 `.evolution/lineage.json`，确认哪些 cluster 创建或更新了 Policy。
7. 检查 `.evolution/workflow_updates.jsonl` 和 `skill_patches.jsonl`，确认 `SKILL.md` 是否实际修改。
8. 检查版本目录和 `manifest.json`，确认是否从 `v000` 发布了 `v001` 或更高版本。
9. 检查后续 batch 的 `skills_snapshot/manifest.json`，确认它实际使用了新版本。
10. 检查 held-out test 使用的是 `final`，且没有把 test retry 当作训练证据。
11. 检查 `skill_versions/memory_store.json`：`memories` 应只含 `memory_kind=reflection_episode` 的可检索经验，`policy_candidates` 中才允许 atomic/workflow 聚类证据；再从 trajectory 中核对 `mcp__experience_memory__*` 调用与 `memory-*` 命中 ID。

只有同时存在“反思/轨迹证据、聚类或 workflow 更新、Skill 内容变化、版本发布、后续 batch 使用”这些证据，才能称为完整的 Skills 自进化闭环。

## 17. 当前实现边界

- 初始成功任务不会生成失败反思，但成功轨迹仍参与程序步骤发现。
- 单个任务的多次重试不会增加跨任务 support。
- 成功 retry 只验证直接指导该 retry 的上一条反思，但仍不是严格的单因素因果证明。
- 反思解析依赖规定的结构化标题；缺失字段会使用保守的 fallback。
- 未通过 verifier 的局部工具恢复不能直接成为公开 Policy。
- embedding 不可用时停止发布，不使用弱化的关键词聚类。
- 新 Policy 默认是 experimental，需要后续显式采用并成功后才能转为 active。
- held-out test 默认不反思、不重试、不更新 Skill。
- Memory MCP 使用 embedding cosine + BM25 混合检索，并用语义、混合分数和词项覆盖率阈值拒绝低相关候选；embedding 服务不可用时只允许高覆盖率的严格 BM25 回退。它仍只按需检索或按 ID 读取，不自动把全部记忆塞入上下文；trajectory 会记录实际查询、检索模式与命中，供 matched-information 实验审计。
