"""Research Agent -- Research & Innovation Division.

General-purpose, any topic (marketing research, competitor analysis,
AI trends, business opportunities, strategic planning, tech, medicine,
design -- Mohamed's explicit instruction, 2026-08-03: "ready for any
question, cannot name everything").

Real web search (ddgs -- DuckDuckGo, no API key/billing needed,
deliberately chosen over a paid search API to keep moving after the
Maps billing pause) grounds every answer in actual current sources,
then Ollama synthesizes a clear answer citing them. Mohamed's explicit
choice over Ollama-alone (2026-08-03) -- a 3B model answering
specialized questions (medicine, current AI trends) from memory alone
would be a real accuracy risk for a "ready for anything" agent.
"""


def web_search(query: str, max_results: int = 5) -> dict:
    """Real web search via Tavily -- switched from ddgs (2026-08-03,
    same session) after DuckDuckGo/Bing/Brave scraping all started
    failing outright ("No results found" even for trivial queries like
    "python programming") -- a known failure mode for unofficial
    scraping libraries once they detect automated/repeated requests.
    Tavily is a real API built for exactly this use case (LLM/agent
    research), free tier, no credit card required. Never raises --
    same fail-safe pattern as every other external call in this
    project."""
    import os

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return {"ok": False, "reason": "TAVILY_API_KEY not configured in .env yet."}

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        response = client.search(query, max_results=max_results)
    except Exception as e:
        return {"ok": False, "reason": str(e)}

    return {
        "ok": True,
        "backend": "tavily",
        "results": [
            {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
            for r in response.get("results", [])
        ],
    }


RESEARCH_SYSTEM_PROMPT = (
    "You are a research assistant. You are given a question and a set of real "
    "web search results (title, URL, snippet). Answer the question using ONLY "
    "information from those results -- if they don't actually answer it, say so "
    "plainly rather than guessing from your own memory. Cite sources by putting "
    "the URL in parentheses after the relevant claim. Keep the answer clear and "
    "well-organized, suitable for a chat message."
)


def research_topic(question: str, max_results: int = 5) -> dict:
    """Full pipeline: real search -> Ollama synthesis grounded in those
    real results, with citations. Every attempt logged to
    memory_experience -- a real audit trail of what was researched and
    when, same principle as every other real-world-action agent in
    this project."""
    from agents.rii._memory_helpers import safe_add_experience
    from shared.models.ollama_client import chat as ollama_chat

    search = web_search(question, max_results=max_results)
    if not search.get("ok"):
        safe_add_experience(
            division="rii",
            agent_id="rii-research-v0.1",
            event_type="research_attempted",
            context=question,
            outcome="search_failed",
            metadata={"reason": search["reason"]},
        )
        return {"ok": False, "stage": "search", "reason": search["reason"]}

    if not search["results"]:
        safe_add_experience(
            division="rii",
            agent_id="rii-research-v0.1",
            event_type="research_attempted",
            context=question,
            outcome="no_results",
        )
        return {"ok": False, "stage": "search", "reason": "No search results found for that query."}

    sources_text = "\n\n".join(
        f"[{i + 1}] {r['title']}\nURL: {r['url']}\n{r['snippet']}" for i, r in enumerate(search["results"])
    )
    prompt = f"QUESTION: {question}\n\nSEARCH RESULTS:\n{sources_text}"

    result = ollama_chat(prompt, system=RESEARCH_SYSTEM_PROMPT)
    if not result.get("ok"):
        safe_add_experience(
            division="rii",
            agent_id="rii-research-v0.1",
            event_type="research_attempted",
            context=question,
            outcome="synthesis_failed",
            metadata={"reason": result["reason"]},
        )
        return {"ok": False, "stage": "synthesis", "reason": result["reason"]}

    safe_add_experience(
        division="rii",
        agent_id="rii-research-v0.1",
        event_type="research_attempted",
        context=question,
        outcome="ok",
        metadata={"source_count": len(search["results"]), "sources": [r["url"] for r in search["results"]]},
    )
    return {"ok": True, "answer": result["reply"], "sources": search["results"]}
