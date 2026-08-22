"""
Shared Knowledge
================

The one knowledge base this platform keeps: a PgVector store every component can
read from, declared once and offered to anything Platform Builder builds.

It ships empty on purpose. Loading documents is a human act with cost and quality
consequences, so it happens where a human can see it — the Knowledge page in the
AgentOS UI, or the `/knowledge` REST routes that `AgentOS(knowledge=[...])` mounts.
Agents read; people load.
"""

from agno.knowledge import Knowledge

from db import create_knowledge

# The name is the reference, so it is the base's own name and not a label beside
# it: a Studio-built component stores this string and resolves the live base on
# load, exactly the way `learning_name` resolves the shared self — see
# app/learning.py. Renaming it breaks every component already wired to it.
KNOWLEDGE_NAME = "platform-knowledge"

# One base, not one per component. Vector rows carry no component identity, so a
# second base would be a second corpus to fill and keep current rather than a
# second view of the same one. Namespacing within a base is coming; until then,
# one store keeps "build me an agent that answers from our docs" answerable
# without asking the user which of several stores they meant.
platform_knowledge: Knowledge = create_knowledge(KNOWLEDGE_NAME, "platform_knowledge")
