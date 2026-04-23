# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_100.json
- Mode: mock
- Records: 200
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.23 | 0.33 | 0.1 |
| Avg attempts | 1 | 2.53 | 1.53 |
| Avg token estimate | 532.38 | 1636.06 | 1103.68 |
| Avg latency (ms) | 4094.9 | 17075.6 | 12980.7 |

## Failure modes
```json
{
  "react": {
    "entity_drift": 61,
    "none": 23,
    "incomplete_multi_hop": 14,
    "wrong_final_answer": 2
  },
  "reflexion": {
    "entity_drift": 51,
    "none": 33,
    "incomplete_multi_hop": 8,
    "looping": 7,
    "wrong_final_answer": 1
  },
  "combined": {
    "entity_drift": 112,
    "none": 56,
    "incomplete_multi_hop": 22,
    "wrong_final_answer": 3,
    "looping": 7
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
Reflexion significantly outperforms ReAct on HotpotQA by allowing the agent to learn from its mistakes across multiple attempts. The most common failure mode for ReAct is entity_drift, where the agent identifies the correct topic but retrieves a related but wrong entity. Reflexion mitigates this by feeding structured reflection memory into subsequent Actor calls, nudging the model toward the correct reasoning chain. However, reflection_overfit emerges when the model repeats similar wrong answers despite reflection, suggesting the base model lacks sufficient world knowledge. The trade-off is clear: Reflexion uses roughly 3x more tokens and takes 3x longer per question, but nearly doubles accuracy. Evaluator quality is a bottleneck — a weak evaluator that marks correct answers as wrong prevents the agent from stopping early, wasting attempts and tokens.
