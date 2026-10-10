# Design decisions and tradeoffs

### Why idempotency, and why Redis `SET NX EX`
A merchant's client can always retry a request that timed out without knowing whether
it actually went through - without idempotency, that retry would charge the card twice.
`SETNX key "processing" EX 60` atomically claims the key so a second, concurrent
request with the same `Idempotency-Key` sees it's already in flight (409) rather than
racing the first one; once the first request finishes, it overwrites the key with the
final result (`EX 24h`), so later replays return the cached outcome instead of
re-running authorization. **Simplification:** unlike real Stripe, this sim doesn't hash
the request body, so reusing a key with different parameters silently returns the
original result instead of erroring.

### Why retries with backoff, and why they're centralized
Every inter-service call in this system funnels through one function,
`common.http.post_with_retry` - this was a deliberate refactor in Day 4 (it started as
copy-pasted `httpx.post` + `try/except` in each service). Centralizing it meant the
Day 5 integration tests could get the entire real chain running in-process just by
monkeypatching that one function per service, instead of mocking each service
individually.

### Reversal keyed by a client-generated `request_id`
The failure mode is specifically "the issuer approved, but the response never arrived."
At the moment the gateway needs to clean that up, it has, by definition, never
received anything from the issuer - no server-generated authorization id, no
confirmation of anything. The only thing it's guaranteed to still have is the
`request_id` *it itself generated* before making the call. So the issuer persists its
approval keyed by that same id (sent by the caller, not invented by the issuer), which
lets a reversal reference "undo whatever you did for this request" using information
the caller already had - this mirrors how real card networks use the original
transaction's reference for a network reversal/advice message, rather than an id from
a response that may never arrive.

One bug this surfaced: a retried authorize request carries the *same* `request_id` on
every attempt. The issuer's first attempt persists the record and then sleeps (to
simulate the lost response); the caller's retry is a brand new HTTP request that also
reaches the issuer and also tries to record an approval for the same `request_id` -
which collided with the primary key and raised an unhandled exception. Fixed by making
`record_authorization` a no-op if that `request_id` is already recorded
(`services/issuer/accounts.py`).

### Why settlement polls the gateway over HTTP instead of a second Redis pattern
Redis already demonstrates one pattern (the idempotency lock). Settlement could have
used a Redis sorted set as a delay queue instead, but that would mean two different
inter-service communication styles in one project. Staying consistent with the rule
used everywhere else - services never share a database file, they talk over HTTP - felt
like the better teaching choice, even though a real delay queue is a reasonable
alternative design.

### Why services never share a database file
Each service (`gateway`, `issuer`, `settlement`, ...) has its own SQLite file and no
other service ever opens it directly. This is what makes "one sqlite file per service"
in the setup checklist meaningful rather than cosmetic: it's the thing that forces
every cross-service interaction to go through an HTTP contract, which is the whole
point of simulating separate companies in the first place.

### Why integration tests don't need Docker
All five services are plain FastAPI apps. Since every inter-service call already goes
through the one `post_with_retry` chokepoint (see above), the test suite monkeypatches
it to dispatch to each service's own `TestClient` based on URL prefix instead of making
a real network call. A thread pool + `future.result(timeout=...)` makes this faithful
even for the reversal scenario: a handler that sleeps past its caller's timeout
genuinely times out in the test the same way a real `httpx` call would, abandoned
thread and all. The one exception is idempotency, which needs a real Redis - CI runs
one as a service container; locally, `docker compose up -d redis` is enough.

### Simplified settlement fee
`settlement_fee_bps` (290 = 2.9%) is percentage-only. Real processors also charge a
flat per-transaction fee (Stripe's is $0.30) - omitted here to keep the ledger math in
one dimension.

### The Day-2 bind-mount lesson
The first version of `docker-compose.yml` bind-mounted the whole repo (`.:/app`) into
every container for live-reload convenience. On Windows this silently shadowed each
image's own `.venv` with the host's Windows-style venv (`Scripts/` not `bin/`), so
`uvicorn` wasn't actually importable at runtime - and it went unnoticed because a
stray local `uvicorn` process from manual testing was still squatting on port 8000,
answering health checks while the container itself had crashed. The fix was to drop
the bind mounts entirely: the image's own copy of the source is authoritative, and a
rebuild (`docker compose up --build`) is required to pick up code changes. Slower
inner loop, but no more silent host/container path mismatches.

### Other excluded scope
Encryption at rest, authorization/capture as separate steps, chargebacks, and
multi-currency are all left out - see the README's "What's excluded" section. None of
these change the architecture; they'd each add a dimension (key management, a second
API call per payment, a dispute lifecycle, currency conversion) orthogonal to what this
project is teaching.
