"""LangGraph flow draft for the agentic search method.

The executable runner stays dependency-light; this module documents the node
boundaries used when LangGraph is installed.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgenticState(TypedDict, total=False):
    product_id: str
    keyword: str
    raw_results: list[dict[str, Any]]
    evaluated_results: list[dict[str, Any]]


def plan_node(state: AgenticState) -> AgenticState:
    return state


def search_node(state: AgenticState) -> AgenticState:
    return state


def evaluate_node(state: AgenticState) -> AgenticState:
    return state


def build_langgraph_flow():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError("Install langgraph to build the optional graph flow.") from exc

    graph = StateGraph(AgenticState)
    graph.add_node("plan", plan_node)
    graph.add_node("search", search_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "evaluate")
    graph.add_edge("evaluate", END)
    return graph.compile()
