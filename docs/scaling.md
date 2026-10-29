# Scaling guidance

## Initial deployment

Start with one always-running API instance, one Uvicorn worker and PostgreSQL.
Redis is not required or included in the starter. MCP uses the framework defaults,
and Agno generates its internal scheduler credential automatically. The API needs
no attached disk. Local engineering state may be lost when its container is replaced;
see [sandbox setup](harnesses.md) for optional isolation and checkpoint recovery.

## Optional multi-replica architecture

The same architecture applies across cloud providers; service provisioning,
networking, credentials and load-balancer settings depend on the deployment target.
Keep those details in the provider's deployment instructions and keep the shared
deployment skill pointed at this guide.

| Component | Responsibility |
| --- | --- |
| PostgreSQL | Saved conversations, Company records, schedule claims and the durable execution queue |
| AgentCore | Isolated coding agent execution outside API containers |
| S3 | Coding agent workspace and native-session checkpoints, restored after compute replacement |
| Redis | Shared live run events and cancellation across API instances |
| API replicas and load balancer | Serve requests using the same database, authorization and coordination configuration |

S3, AgentCore and Redis are valid additions as the platform grows. Before enabling
multiple API instances:

1. If you use coding agents, configure [AgentCore and S3](harnesses.md#aws-agentcore-sandbox)
   with the same repository and checkpoint bucket/prefix for the platform's replicas.
   Platforms without coding agents do not need these sandbox resources.
2. Install the Redis client and configure Agno's existing `QueueConfig.redis`
   with a shared private Redis connection. Keep the durable queue in PostgreSQL.
3. Configure a shared internal scheduler credential and consistent JWT/MCP
   authentication across replicas. Independently generated scheduler tokens do
   not authenticate calls routed to another instance.
4. Choose MCP transport settings for the clients you support. Modern requests
   are sessionless; legacy transport sessions need affinity or explicit stateless
   mode, which gives up their back-channel requests and transport resumability.
5. Keep queue timing/retry settings consistent and size database connections for
   the workload. Use always-running instances for scheduler and queue workers.

Sticky sessions alone cannot share run events or cancellation: a request may
reach instance A while a queue worker on B executes it. Redis supplies that shared
coordination in the current Agno implementation. PostgreSQL supplies queue durability
and worker-lease recovery; S3 supplies last-checkpoint coding agent recovery. These
solve different parts of failure handling. Retrying a run can repeat external
side effects, and checkpoints do not restore live processes or unsaved changes.

## Verify before increasing replicas

Test through different instances and the provider's public endpoint: submit,
stream, reconnect and cancel a run; continue a saved conversation; verify access
controls, MCP clients and scheduled work. Replace an API instance and sandbox,
then verify the expected queue and checkpoint recovery. Check generated-file and
upload delivery separately: S3 checkpoints are not general artifact hosting.

The starter does not provision or enable this optional architecture automatically.
