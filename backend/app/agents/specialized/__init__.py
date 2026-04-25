"""
Specialized LangGraph Agents

This module implements a supervisor-worker architecture using LangGraph agents.
The supervisor orchestrates specialized worker agents (OCR, Classifier, Extractor, Forgery, Scorer).
"""

from app.agents.specialized.supervisor import create_supervisor_graph

__all__ = ["create_supervisor_graph"]
