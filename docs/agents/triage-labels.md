# Triage Labels (Multica `gjam` Mapping)

The engineering skills use five canonical triage roles. `gjam` already uses a workspace-wide Chinese label catalog, so we map canonical roles to existing `gjam` statuses/labels (without polluting the shared workspace label catalog) and fall back to status + description tags where no exact label exists.

Verify label UUIDs anytime via `multica --profile gjam label list --output json`.

| Canonical role | Mapping in `gjam` | Meaning |
| --- | --- | --- |
| `needs-triage` | Status `backlog` (unlabeled / unassessed) | Maintainer needs to evaluate this issue |
| `needs-info` | Status `blocked` + label `待人工` (`[状态] 需要用户拍板或给凭据`) | Waiting on reporter / user decision |
| `ready-for-agent` | Status `backlog` or `todo` + task type label (`实现` / `仿真` / `建模` / `调研`) + `卫星算力` | Fully specified, ready for an agent |
| `ready-for-human` | Status `blocked` or `in_review` + label `待人工` | Requires human implementation or sign-off |
| `wontfix` | Status `cancelled` + label `已归档` (and `已被覆盖` + `--duplicate-of <orig>` if superseded) | Will not be actioned |

## Notes

- **Category roles** (`bug` / `enhancement`): `gjam` classifies issues by deliverable type (`实现`, `仿真`, `建模`, `调研`, `运维`, `论文材料`) plus research line (`科研`, `卫星算力`, `工程`). Pick the deliverable type matching the primary output.
- If you later create dedicated `needs-triage` / `ready-for-agent` labels in `gjam`, update the middle column above so `/triage`, `/to-spec`, and `/to-tickets` apply them automatically.
