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
| **Success path** | Formatter + linter → tests → scrape → persist → export → rclone (retry). |
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
## Large-Output & Context-Handling Guidelines

**Prevent stdout overflows** (no single line > 1600 bytes) by fetching and slicing before printing:

1. **Fetch programmatically**  
   Default to a Python pattern (requests + BeautifulSoup + textwrap) to download and wrap pages.  
   ```python
   import requests, textwrap
   from bs4 import BeautifulSoup

   URL  = "https://example.com/large-page"
   html = requests.get(URL, timeout=15).text                 # ① pull page
   text = BeautifulSoup(html, "html.parser").get_text()      # ② strip tags
   safe = "\n".join(textwrap.wrap(text, width=1600))         # ③ hard-wrap
   print(safe[:4000])                                        # ④ print only the needed snippet

2. **Avoid giant single-line prints**
   Wrap or slice parsed text (textwrap.wrap(text, 1600) or text[:4000]) so no line exceeds the limit.

3. **Targeted keyword/regex search**
Filter for relevance first (e.g. only lines containing a keyword or matching a regex) to avoid dumping entire pages.

4. **Chunk large outputs**
If you need more context, emit in segments:

print(safe[0:4000])
print(safe[4000:8000])
…and so on

5. **Leverage cached/local docs**
Store frequently-used references under knowledge/ in pre-wrapped form to avoid repeated external fetches.

6. **Complete context over speed**
When in doubt, fetch and slice multiple segments rather than answering prematurely with missing info.

7. **Maintain reproducibility**
Install any extra parsing libs in your venv (e.g. pip install bs4) so environments stay predictable
Feel free to drop or adjust any bullet to match your style—this covers all the bases for safe, complete context retrieval.


