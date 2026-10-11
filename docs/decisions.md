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

### Fraud features: one definition, two paths, and a parity test between them
The fraud model is trained on features computed offline from a CSV
(`ml/offline_features.py`) but served from features computed live in Redis
(`services/fraud/features.py`). If the two drift apart - a window off by one, a
boundary that's inclusive on one side and exclusive on the other - the model silently
scores inputs it never saw in training (training/serving skew). Three things guard
against that:

- **One definition.** Feature names and window sizes live only in
  `services/fraud/features.py`; the offline code imports them.
- **A parity test.** `tests/unit/test_feature_parity.py` replays generated traffic
  through Redis (fakeredis) and requires the same numbers as the offline path on every
  row; `python -m ml.check_parity` does the same at larger scale against real Redis.
- **Boundary unit tests.** Random millisecond timestamps almost never land exactly on a
  window edge, so the parity test alone missed a deliberately planted inclusive/exclusive
  bug. `test_short_window_boundary_is_exclusive` catches it.

**The current payment's outcome is never a feature.** A real-time scorer runs before
the issuer has decided, so it can't know whether this payment will be declined. Using it
offline would leak the answer into training. So each payment touches Redis twice:
`observe()` at score time records the attempt and returns features, then
`record_outcome()` after authorization records a decline. A side effect: a payment the
fraud check blocks still counts as an attempt, so an attacker can't reset their own
counters by getting blocked.

**Sorted sets, one round trip.** Each window is a sorted set scored by timestamp; trim
with `ZREMRANGEBYSCORE` (inclusive, which drops an event exactly `window` seconds old),
count with `ZCOUNT` using an exclusive `(` lower bound. Distinct cards per IP is a sorted
set keyed by card with its last-seen time as the score. All trims, adds, counts and
TTLs go in one `MULTI` pipeline - one network round trip per score, no Lua needed.

### Why the fraud service serves gradient boosting, and no sequence model (yet)
The original plan had an optional GRU over each IP's recent events. It was skipped on
purpose: gradient boosting on the six window features plus amount already reached
F1 0.95 on the synthetic test slice (vs 0.54 for the rules), so a sequence model had little
room to show a real gain, and PyTorch would have added ~200 MB to the ML dependencies and
slowed every CI run. Sequence models are the natural next step once the data has
attackers that the window features can't separate - e.g. slow campaigns, which are
already the model's weakest category.

### Why the fraud model is trained at image build time
`ml/artifacts/` is gitignored, so the fraud image can't just copy a model in. Instead its
Docker build runs `ml.generate_data` + `ml.train` (fixed seed, ~30 s), gated by a
`TRAIN_FRAUD_MODEL` build arg so the other services' images are unchanged. The
alternative - committing `gbm.joblib` - would tie the repo to one scikit-learn version's
pickle format and put an opaque binary in review diffs. Building it from code keeps the
model reproducible from what's in git. Adding `.dockerignore` came with this: without it,
`COPY . .` also copied the host's `.venv` and any locally trained artifacts into the image.

The service reads the model's feature order and block threshold from the artifact's JSON
metadata rather than redefining them, so a retrained model can't silently be fed columns
in the wrong order.

### Other excluded scope
Encryption at rest, authorization/capture as separate steps, chargebacks, and
multi-currency are all left out - see the README's "What's excluded" section. None of
these change the architecture; they'd each add a dimension (key management, a second
API call per payment, a dispute lifecycle, currency conversion) orthogonal to what this
project is teaching.
