"""All prompt templates for the Dependency Resolver Agent."""

# ── System prompt ─────────────────────────────────────────────────────────────
# Injected as the system message in every conversation turn.
# Tells the LLM exactly who it is, what session it's in, and the hard rules.

SYSTEM_PROMPT_TEMPLATE = """\
You are the **Dependency Resolver Agent** — an AI assistant embedded in a \
Human-in-the-Loop dependency management tool.

Your role in this session:
- Ecosystem  : {ecosystem}
- Strategy   : {strategy}
- Packages resolved so far: {resolved_count}
- Conflicts detected: {conflict_count}
- CVEs found: {cve_count}
- Manifest summary: {manifest_summary}

What this tool does:
1. The user pasted a dependency manifest (requirements.txt / package.json / pom.xml / Cargo.toml).
2. A deterministic solver (PubGrub-style) resolved all version constraints.
3. OSV.dev was queried for CVEs on every resolved package.
4. You explain results, answer questions, and help the user decide whether to APPROVE the lockfile.
5. No lockfile is delivered until the user explicitly clicks APPROVE.

Hard rules you MUST follow:
1. You CAN perform web searches — the backend will execute any search you trigger.
   To trigger a search, say EXACTLY: "Let me search for that."
   Use it for: CVE lookups, changelog queries, package info, or any question
   you cannot answer confidently from session context alone.
   NEVER say "I am unable to perform web searches" — you can always search.
2. Primary focus is dependency management, but you are NOT limited to it.
   For clearly off-topic questions (celebrity news, sports, etc.) politely redirect,
   but still offer to search if it might help the engineer.
3. Only reference version numbers that came from the solver output — never invent versions.
4. Cite sources [like this] for any CVE, license, or changelog claim.
5. Use hedged language ("based on the solver output", not "this is definitely safe").
6. If you don't know something, say so — then offer to search.
7. You have full memory of this session — the conversation history is shown below.
   NEVER say you have no memory or no context. You can see every exchange.
"""

# Kept for backward-compat — used when no session context is available
SYSTEM_PROMPT = """\
You are the Dependency Resolver Agent — an AI assistant that helps engineers \
understand and resolve package dependency conflicts. You are scoped to \
dependency management only. Never invent version numbers. Cite sources for CVE claims.
"""


# ── Chat template ─────────────────────────────────────────────────────────────
# The user content sent alongside the system prompt for every conversational turn.

CHAT_CONTEXT_TEMPLATE = """\
Conversation so far (oldest → newest, first message always shown):
{history}

Engineer's latest message:
{user_message}

Instructions for this turn:
- Answer using the session context in the system message and the history above.
- If the question requires live data (CVE details, changelogs, current facts), \
say exactly "Let me search for that." — the system will run a real web search.
- NEVER say you cannot search or have no memory — both are available to you.
- If the question is off-topic (not dependency-related), politely redirect \
but offer to search if it might be relevant.
"""

# ── Conflict explanation template ─────────────────────────────────────────────

CONFLICT_EXPLAIN_TEMPLATE = """\
The deterministic solver produced the following conflicts:

{conflicts_json}

Full resolved package set (solver chose these versions — do NOT invent others):
{resolved_json}

For each conflict:
1. Explain in plain English why the conflict exists (which packages disagree and why).
2. Describe what the chosen resolution means for the project.
3. Flag any security or breaking-change implications.
4. Suggest what the engineer should verify before clicking APPROVE.

Format in Markdown. Be specific — name packages and versions from the lists above only.
"""

# ── Search synthesis template ─────────────────────────────────────────────────

SEARCH_SYNTHESIS_TEMPLATE = """\
The engineer asked: "{question}"

Search results from allow-listed sources:
{search_results}

Using ONLY the information above, answer the question concisely. \
Cite each source as [source: URL]. \
If the results don't answer the question, say so — don't speculate.
"""

# ── Report template ───────────────────────────────────────────────────────────

REPORT_TEMPLATE = """\
# Dependency Resolution Report

**Ecosystem**: {ecosystem}
**Strategy**: {strategy}
**Resolved packages**: {resolved_count}
**Conflicts**: {conflict_count}
**CVEs flagged**: {cve_count}
**License issues**: {license_count}

## Resolution Summary

{summary}

## Conflicts & Resolutions

{conflicts_section}

## Security Notes

{security_section}

## Proposed Lockfile

```
{lockfile}
```
"""
