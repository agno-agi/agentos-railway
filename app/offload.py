"""
Result Offloading
=================

Where big tool results go instead of into the conversation.

A tool that returns a whole web page, a whole source file, or a whole metrics
payload costs that much context on every later turn of the session. Offloading
writes anything past the threshold to a file store and leaves a short envelope
in the transcript — a preview, the size, and a `result_id` — then hands the
component `search_result` and `read_result` to go back for the parts it needs.
Nothing is lost, nothing is summarized, and no model call happens on the way in.

Declared once and shared: the framework never mutates the object it is given,
it takes a copy bound to each component's own database, so one declaration
configures every component that carries it.
"""

from agno.offload import ResultStore

# Payloads expire seven days out. The default is no expiry at all, and the
# sweeper only runs when a TTL is set — so a platform doing daily web fetches
# would grow this store forever. Seven days is long enough that a follow-up
# question days into the same session still resolves its result_id, and short
# enough that the store stays self-limiting without anyone maintaining it.
RESULT_TTL_SECONDS = 7 * 24 * 60 * 60

# db is deliberately unset. `bound()` fills it from whichever component is
# building the store, so this one object serves all of them — the opposite of
# the shared LearningMachine in app/learning.py, where the framework injects
# into the shared object itself and leaving db None would let the first
# component to run bind its own for every sharer.
#
# The threshold stays at the framework default: below one read_result page, a
# result costs more to fetch back than to keep inline.
result_store = ResultStore(ttl_seconds=RESULT_TTL_SECONDS)
