"""
App Settings
============

Shared runtime objects for the platform.
"""

from agno.models.openai import OpenAIResponses


def default_model() -> OpenAIResponses:
    """Fresh model instance per agent — avoids shared-state footguns."""
    return OpenAIResponses(id="gpt-6.1-sol")


def super_agent_model() -> OpenAIResponses:
    """Model for Super Agent and Company work."""
    return OpenAIResponses(id="gpt-6.1-sol")
