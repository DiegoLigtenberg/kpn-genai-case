from typing import Any, Optional, cast

from langgraph.graph import END, START, StateGraph

from src.models.app_schemas import InvoiceGraphState
from src.service.graph_nodes import (
    atomic_image_node,
    final_decision_node,
    make_extract_node,
    make_policy_node,
)
from src.service.llm_config import get_llm
from src.service.invoice_policy import DuplicateRegistry, PolicySettingsHolder, load_policy_settings


def build_graph(
    llm: Any,
    policy_holder: PolicySettingsHolder,
    duplicates: DuplicateRegistry,
):
    g = StateGraph(InvoiceGraphState)
    # LangGraph's stubs expect Runnable types; our plain callables are valid at runtime.
    g.add_node("atomic_image", cast(Any, atomic_image_node))
    g.add_node("extract", cast(Any, make_extract_node(llm, duplicates)))
    g.add_node("policy", cast(Any, make_policy_node(policy_holder)))
    g.add_node("final_decision", cast(Any, final_decision_node))

    g.add_edge(START, "atomic_image")
    g.add_edge("atomic_image", "extract")
    g.add_edge("extract", "policy")
    g.add_edge("policy", "final_decision")
    g.add_edge("final_decision", END)
    return g.compile()


def build_invoice_graph(
    *,
    llm: Optional[Any] = None,
    llm_type: str = "openai",
    policy_holder: Optional[PolicySettingsHolder] = None,
    duplicates: Optional[DuplicateRegistry] = None,
):
    llm = llm or get_llm(llm_type=llm_type)
    holder = policy_holder or PolicySettingsHolder(load_policy_settings())
    dup = duplicates or DuplicateRegistry()
    return build_graph(llm, holder, dup)
