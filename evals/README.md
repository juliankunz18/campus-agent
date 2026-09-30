# Evaluation

A release to production needs two things (see the technical design):

1. 100 % passing permission and attack tests.
2. A correctness rate on the golden set above the target value. The rate `p` is
   estimated with a 95 % Wilson confidence interval.

## Datasets

| File | Content |
|---|---|
| `datasets/golden_set.synthetic.jsonl` | Synthetic questions for the fictional Musterverein |
| `datasets/attacks.jsonl` | Foreign data, role change by prompt, identity spoofing, own approval, injection in documents |

Each line is one case:

```json
{"id": "golden-statutes", "category": "golden", "role": "member",
 "question": "…", "expected_tools": ["search_knowledge"], "forbidden_tools": []}
```

Real questions of a group never belong in this public repository. They live in the
group's private deployment repository (for example `evals/golden_set.jsonl`).

## Commands

```bash
uv run python -m evals.runner validate evals/datasets/*.jsonl
uv run python -m evals.runner run evals/datasets/golden_set.synthetic.jsonl   # not implemented yet
```

`run` will execute each case against the dev deployment, score the tool usage
deterministically and add an LLM-as-judge for answer quality plus a manual sample.
