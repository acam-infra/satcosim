# Issue tracker: Multica (`--profile gjam`)

Issues, specs, and sub-issues for `satcosim` live in Multica under profile `gjam`. Every `multica` command below **must** pass `--profile gjam` (the default profile points to a different workspace).

## Workspace & Project Defaults

- **Profile**: `gjam`
- **Workspace ID**: `24121790-298d-4af4-bd07-19b55f78c9d0` (`LAB-*` identifiers)
- **Default project (`科研 · Satellite`)**: `75c795bb-8da2-43f6-b743-2caf76371132`
- **Infra/tooling alternative (`工具 · Sandbox`)**: `42a676df-b114-4c38-93fc-f44f5c7500da` (use only for pure host/runner/tooling tasks outside Satellite research)

## Statuses & Auto-Start Safety

Valid status keys in `gjam`: `backlog`, `todo`, `in_progress`, `in_review`, `blocked`, `done`, `cancelled`.

- Moving an issue to `todo` or assigning an agent without `--no-start` can trigger a Multica server-side agent run.
- When an agent is working **locally in the current session** (`/implement`, `/implement-spec`, `/wayfinder`, `/triage`), create issues in `backlog` and pass `--no-start` on status/update transitions so Multica does not spawn duplicate remote runs.
- Only omit `--no-start` (or assign a Multica runtime agent at `todo`) when intentionally dispatching work to a remote Multica worker per [docs/BRANCHING.md](../BRANCHING.md) §8.

## Core Operations (Main Issues & Sub-Issues)

`<id>` accepts either the human key (`LAB-1779`) or UUID. For multi-line UTF-8 descriptions/comments, write a temporary UTF-8 file inside the working directory (or pass `--description-stdin` / `--content-stdin`) instead of inline escaping.

- **Create main issue (Spec / Epic / Map)**:
  ```bash
  multica --profile gjam issue create \
    --project 75c795bb-8da2-43f6-b743-2caf76371132 \
    --title "<title>" \
    --description-file <path> \
    --status backlog \
    --output json
  ```
- **Create sub-issue under a main issue**:
  ```bash
  multica --profile gjam issue create \
    --project 75c795bb-8da2-43f6-b743-2caf76371132 \
    --parent <parent-id> \
    [--stage <N>] \
    --title "<title>" \
    --description-file <path> \
    --status backlog \
    --output json
  ```
  Use `--stage <N>` (`>= 1`) when sub-issues execute in ordered barrier stages; omit `--stage` for unstaged or DAG-linked tickets.
- **List sub-issues (grouped by stage)**:
  ```bash
  multica --profile gjam issue children <parent-id> --output json
  ```
  Returns `{"stages": [...], "unstaged": [...], "total": <n>}`.
- **Read an issue and its comments**:
  ```bash
  multica --profile gjam issue get <id> --output json
  multica --profile gjam issue comment list <id> --compact --output json
  ```
- **List open issues in the project**:
  ```bash
  multica --profile gjam issue list \
    --project 75c795bb-8da2-43f6-b743-2caf76371132 \
    --fields id,identifier,title,status,parent_issue_id,stage,labels,assignee_id \
    --output json
  ```
- **Attach/reparent or update an issue**:
  ```bash
  multica --profile gjam issue update <id> --parent <parent-id> [--stage <N>] --no-start --output json
  ```
  Pass `--parent ""` to detach a sub-issue.
- **Comment on an issue**:
  ```bash
  multica --profile gjam issue comment add <id> --content-file <path> --output json
  ```
  If running inside a Multica comment-triggered session, include `--parent <trigger-comment-id>`.
- **Labels**:
  ```bash
  multica --profile gjam issue label add <id> <label-id>
  multica --profile gjam issue label remove <id> <label-id>
  ```
  Discover `<label-id>` values with `multica --profile gjam label list --output json`. See `docs/agents/triage-labels.md` for role mapping.
- **Status transitions & closing**:
  ```bash
  multica --profile gjam issue status <id> in_progress --no-start
  multica --profile gjam issue status <id> in_review --no-start
  multica --profile gjam issue status <id> done --no-start
  multica --profile gjam issue status <id> cancelled --duplicate-of <orig-id> --no-start
  ```
  Always post the closing/explanation comment before marking `done` or `cancelled`.

## Blocking Edges & Frontier

Multica does not have a GitHub-style `blocked-by` edge field between arbitrary issues; represent blocking with **two complementary mechanisms**:

1. **Stage barrier (`--stage <N>`)**: for sub-issues under the same `--parent`, stage `N` is blocked until all sub-issues in stages `< N` are `done` or `cancelled`.
2. **Explicit `Blocked by:` header**: for fine-grained dependencies across tickets, put `Blocked by: LAB-xxx, LAB-yyy` (or `Blocked by: None`) at the top of the sub-issue description.

A ticket is **unblocked** when all earlier stages under its parent (if staged) AND every issue listed in its `Blocked by:` line have `status` in `{"done", "cancelled"}`.

## Pull Requests as a Triage Surface

**PRs as a request surface: no.** (External PRs are not auto-ingested into Multica triage.)

## Skill Hookups

- **Publish to the issue tracker** (`/to-spec`, `/to-tickets`): create a main issue (for specs) or `--parent <spec-id>` sub-issues (for tickets) in `backlog` under project `75c795bb-8da2-43f6-b743-2caf76371132`. Use `Blocked by:` lines (and `--stage` where phased) to encode dependencies.
- **Fetch the relevant ticket** (`/implement`, `/implement-spec`, `/code-review`): run `multica --profile gjam issue get <id> --output json` and `issue comment list <id> --compact --output json`.

## Wayfinding Operations

Used by `/wayfinder`. The **map** is a main issue (tagged with `汇总索引` or `重要`, or labelled per `triage-labels.md`); its **child tickets** are created with `--parent <map-id>`.

- **Map**: main issue holding `## Destination`, `## Notes`, `## Decisions so far`, `## Not yet specified`, `## Out of scope`.
- **Child ticket**: sub-issue created with `--parent <map-id>`, holding `## Question` (and `Blocked by:` if gated).
- **Frontier query**: run `multica --profile gjam issue children <map-id> --output json`; filter items whose `status` is not `done`/`cancelled`/`in_progress`, with `assignee_id == null` and all `Blocked by:` blockers in `done`/`cancelled`.
- **Claim**: `multica --profile gjam issue status <id> in_progress --no-start` (plus `--assignee` only when assigning a human or intentionally dispatching a remote agent).
- **Resolve**: post resolution comment (`issue comment add`), mark `done --no-start`, and append a one-line context pointer (`- [<title>](<id>): <gist>`) to the map's `## Decisions so far`.
