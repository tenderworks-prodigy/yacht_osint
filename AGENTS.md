# AGENTS.md
Central manifest for all automated agents, bots, and CI tasks in **yacht_osint**.

---

## scaffold‑bot
| Item | Spec |
|------|------|
| **Purpose** | Maintain repo structure, configs, stubs, and small code patches. |
| **Triggers** | Manual (pull‑request comments or direct prompts). |
| **Post‑task protocol** | 1. `pip install -r requirements.txt`  <br>2. `pytest -q` → expect **“0 failed”**  <br>3. On test failure: open Issue `ci‑fail`, do **not** merge. |

---

## osint‑ci
| Item | Spec |
|------|------|
| **Purpose** | Nightly OSINT pipeline (`.github/workflows/pipeline.yml`). |
| **Triggers** | Cron `0 2 * * *` UTC & manual `workflow_dispatch`. |
| **Success path** | Exports CSVs, rclone upload to Drive, Sheet refresh. |
| **Failure path** | Step “On failure open issue” creates Issue `osint‑ci‑fail`. |

---

## qa‑reporter
| Item | Spec |
|------|------|
| **Purpose** | Generate HTML data‑quality report (`src/reporting/dq_report.py`). |
| **Triggers** | Final step of nightly pipeline. |
| **Output** | Saves `dq_report.html` to Drive and comments on Issue if errors. |

---

## style
- Formatter: **`black`**
- Linter: **`ruff --fix`**
- Scaffold‑bot must run both before committing.

---

## test‑protocol
~~~bash
pip install -r requirements.txt
pytest -q              # must exit with “0 failed”
~~~

---

## secrets‑contract
- Never print or log: `HF_TOKEN`, `GROQ_API_KEY`, `RCLONE_CONFIG`, `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_CX`.
- Access via `${{ secrets.* }}` in GitHub Actions or `os.environ[...]` locally.

---

## deploy‑hook  *(optional – not active)*
If a tag prefixed `release/` is pushed:
~~~bash
gh release create "$TAG" --generate-notes
~~~

---

## rollback‑rule
If **`main`** pipeline fails twice consecutively:
1. `git revert HEAD~1`
2. Push `revert/*` branch
3. Open Issue tagging `@tenderworks-prodigy/maintainers`

---
