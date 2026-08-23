"""
Result Offloading
=========================

Where big tool results go instead of into the conversation.

A tool that returns a whole web page, a whole source file, or a whole metrics
payload costs that much context on every later turn of the session. Offloading
writes anything past the threshold to a file store and leaves a short envelope
in the transcript — a preview, the size, and a `result_id` — then hands the
component `search_result` and `read_result` to go back for the parts it needs.
"""

from agno.offload import ResultStore

RESULT_TTL_SECONDS = 7 * 24 * 60 * 60

result_store = ResultStore(ttl_seconds=RESULT_TTL_SECONDS)
