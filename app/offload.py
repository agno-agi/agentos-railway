"""
Result Offloading
=========================

Offload big tool results to a database instead of the context window.

A tool that returns a whole web page, a whole source file, or a whole metrics
payload costs that much context on every later turn of the session. Offloading
writes anything past the threshold to a database and leaves a short envelope
in the transcript — a preview, the size, and a `result_id` — then hands the
component `search_result` and `read_result` to go back for the parts it needs.
"""

from agno.offload import ResultStore

# Platform agents only. The four reference components do long back-and-forth work
# over big tool payloads — source files, metrics, registry listings, web pages —
# and that is what this is for. A new agent does not get it by default; wire it
# only when an agent's tool results are measured to outgrow its context.
RESULT_TTL_SECONDS = 7 * 24 * 60 * 60

result_store = ResultStore(ttl_seconds=RESULT_TTL_SECONDS)
