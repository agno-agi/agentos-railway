"""
Shared Learning
===============

The self this platform keeps for each human: user profile and user memory,
declared once and carried by every reference agent — and, through the registry,
by anything Platform Builder builds at runtime.
"""

from agno.learn import LearningMachine, LearningMode, UserMemoryConfig, UserProfileConfig

from app.settings import default_model
from db import get_postgres_db

# The name is what makes this a registry resource rather than one component's
# private machine: a Studio-built component stores a reference to the name and
# resolves this live instance on load, exactly the way knowledge resolves.
SHARED_SELF_NAME = "user-self"

# db and model are declared here deliberately. The framework injects them into a
# shared machine only when they are unset, so on a machine that left them None the
# first component to run would bind its own — permanently, for every component
# sharing it. Declaring both keeps that choice with this file.
#
# One self per human, platform-wide: profile and memory rows are keyed by user id
# alone (`user_profile_<user_id>`, `memories_<user_id>`), never by component. So a
# built agent wired to learning joins this same self whether it references this
# machine by name or takes the zero-config default — on one database there is no
# such thing as a component-private self. What this declaration adds is a reviewed
# configuration, a name the builder can discover, and db/model chosen up front.
#
# Entity memory stays off here on purpose. Entities are the shared world, and the
# world is Agno's claim under one-claim-one-home — the team lead's own machine adds
# entity_memory on top of this same pair.
shared_self = LearningMachine(
    name=SHARED_SELF_NAME,
    db=get_postgres_db(),
    model=default_model(),
    user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),  # private to each user
    user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),  # private to each user
)
