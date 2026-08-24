"""
Shared Learnings
==================

A shared learning machine that lets the platform learn about the users.
"""

from agno.learn import LearningMachine, LearningMode, UserMemoryConfig, UserProfileConfig

from app.settings import default_model
from db import get_postgres_db

SHARED_LEARNING_NAME = "shared-learning"

shared_learning = LearningMachine(
    name=SHARED_LEARNING_NAME,
    db=get_postgres_db(),
    model=default_model(),
    user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),
    user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),
)
