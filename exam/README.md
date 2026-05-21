# MADF 实验方案

## 实验一：多模型对比实验

**目的**：评估不同 LLM 作为底层驱动模型时，MADF 讨论系统的质量差异。

### 实验设计

| 因子 | 值 |
|------|-----|
| 模型 | GPT-4o、Claude Sonnet 4.6、DeepSeek-V3、Qwen-Max、GPT-4o-mini |
| 角色组合 | 从 skills/ 中选择 3 个已生成的 Skill |
| 讨论主题 | 3 个主题（技术趋势、创业决策、教育哲学） |
| 讨论时长 | 180s |
| 重复次数 | 每条件 3 次（共 5×3×3 = 45 场讨论） |

### 评测方法：LLM-as-Judge

使用独立 GPT-4o 作为裁判，对每场讨论记录做 5 维打分（1-10）：

| 维度 | 定义 |
|------|------|
| **连贯性** | 对话是否自然衔接、Agent 是否引用前人发言 |
| **洞见深度** | 观点是否提供了新信息、独特视角、具体案例 |
| **角色一致性** | Agent 语言风格、知识领域、思维模式是否符合角色设定 |
| **参与质量** | Agent 间是否有真正的思想碰撞、互相建设 |
| **主题相关性** | 讨论是否紧扣主题 |

每个维度的 judge prompt 包含评分标准（1-10 分锚定）。

### 执行

```bash
# 完整对比实验
python exam/plot_all.py --run --comparison

# 单场调试
python exam/runner.py --topic "AI 创业方向" --model gpt-4o --duration 120
```

输出 `exam/results/comparison_results.json`，包含每场讨论的 transcript、stats、scores、reasonings。

### 图表

| 图表 | 内容 |
|------|------|
| `radar_chart.png` | 5 维能力雷达图 |
| `bar_comparison.png` | 综合得分柱状图 + 标准差 |
| `heatmap.png` | 模型×维度热力图 |
| `efficiency.png` | 轮次数 vs 强制发言率 |

## 实验二：消融实验

**目的**：评估各组件对讨论质量的边际贡献。

### 消融条件

| 条件 | 说明 |
|------|------|
| **A. 完整系统** | 确信度仲裁 + Jitter + 主持人开场/总结 + 铁律约束 |
| **B. 无确信度仲裁** | 用 round-robin 替换 confidence 仲裁 |
| **C. 无 Jitter** | 移除 confidence 确定性抖动 |
| **D. 无主持人开场** | 跳过 host intro，直接进入第一轮 |
| **E. 无主持人总结** | 讨论到时直接结束，不生成 summary |
| **F. 无铁律约束** | 移除"切题/不重复/为观众"三条铁律 |

### 执行

```bash
python exam/plot_all.py --run --ablation
```

输出 `exam/results/ablation_results.json`。

### 图表

| 图表 | 内容 |
|------|------|
| `ablation_bars.png` | 6 条件综合得分排序 |
| `ablation_radar.png` | 6 条件 5 维雷达对比 |
| `ablation_waterfall.png` | 各组件边际贡献 (相对基线) |
| `ablation_consistency.png` | 角色一致性专项分析 |

## 文件结构

```
exam/
├── README.md               # 本文件
├── config.py               # 实验参数配置
├── models.py               # 数据模型
├── runner.py               # 实验运行器 (调用真实 orchestrator)
├── judge.py                # LLM-as-Judge 评测
├── visualize_comparison.py # 对比实验可视化 (从 results/*.json 读取)
├── visualize_ablation.py   # 消融实验可视化
├── plot_all.py             # 一键入口
└── results/                # JSON 数据 + PNG 图表输出
```

## 前提条件

1. `.env` 中配置 `LLM_API_KEY`、`LLM_MODEL`、`TAVILY_API_KEY`
2. `skills/` 下有至少 3 个已生成的角色 Skill
3. PostgreSQL + Redis 可用
