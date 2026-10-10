# Architecture

## The two flows

### 1. Authorization (real-time)

The customer's card never reaches the merchant. It goes straight to the gateway's
`POST /v1/tokens`, which Luhn-validates it and returns an opaque `tok_...` stored
against the real number in the gateway's own SQLite table (`services/gateway/vault.py`,
`services/gateway/db.py`). This is the PCI point: everything downstream of this call —
the merchant's code, the payment_intent, the acquirer, the processor — only ever
handles tokens or gets the raw card number passed internally over the network, never
stored by the merchant.

`POST /v1/payment_intents` then walks the chain described in the root README's sequence
diagram. Two details worth calling out:

- **Idempotency** happens first, before any downstream call: the gateway claims the
  `Idempotency-Key` in Redis (`services/gateway/idempotency.py`) and, if it's seen this
  key before, returns the cached result without re-running authorization at all.
- **Every hop carries a `request_id`** that the gateway generates once per attempt and
  that flows unchanged through `acquirer -> processor -> network -> issuer`. This is
  what makes the reversal flow below possible.

### 2. Settlement ("days later", compressed to seconds)

`services/settlement/worker.py` polls the gateway's `GET /v1/payment_intents?unsettled=true`
on a short interval. Once `settlement_delay_seconds` has elapsed since a successful
intent was created, it records three balanced movements in its own ledger
(`services/settlement/ledger.py`) and tells the gateway the intent is settled:

```
issuer_clearing   --(amount)-->  acquirer_clearing
acquirer_clearing --(amount - fee)--> merchant_payable
acquirer_clearing --(fee)-->     platform_fee_revenue
```

Each arrow is one debit and one credit of the same amount - the whole point of
double-entry bookkeeping. Summed across all three movements, `acquirer_clearing` nets
to zero (it's just a pass-through), `issuer_clearing` nets to `-amount`, and
`merchant_payable` / `platform_fee_revenue` net to the merchant's payout and the
platform's fee revenue, respectively.

### 3. The reversal path

The scenario the spec asks for explicitly: *the issuer approves, but the response never
reaches the gateway.* Walking through what actually happens:

1. Gateway generates `request_id`, sends it down the chain along with a demo-only
   `X-Simulate-Lost-Response` flag.
2. The issuer approves, **persists an `Authorization` row keyed by `request_id`**, then
   (because the flag is set) sleeps past every caller's timeout.
3. Every hop's retry budget (`common/http.py`) exhausts in turn, each one timing out
   against its immediate neighbor rather than the issuer directly - the delay doesn't
   multiply across hops, since each layer only waits on its own call.
4. The gateway's own call to the acquirer raises `UpstreamError`. It never got a
   response, so it doesn't know whether the issuer approved - but it still has the
   `request_id` it generated in step 1. It fires `POST /v1/reversals {request_id}` down
   the same path.
5. Each service relays the reversal one hop deeper, the same shape as its authorize
   relay. The issuer looks up `request_id`, finds the approved record from step 2, and
   flips it to `reversed`.
6. The merchant sees a plain `failed` / `upstream_timeout` payment_intent. Behind the
   scenes, the phantom approval has been cleaned up.

This only works because the reversal is keyed by a **client-generated** id, not a
server-generated one the caller never received - see
[decisions.md](decisions.md#reversal-keyed-by-a-client-generated-request_id).

## What was built when

| Day | What |
|---|---|
| 1 | Tooling (uv, Docker, git), `common/luhn.py`, a "hello" gateway service |
| 2 | `issuer`, `network`, `processor` - the back half of the authorization chain |
| 3 | `acquirer`, `gateway` tokenization + `payment_intents` - the front half |
| 4 | Idempotency, signed webhooks, timeouts/retries, the reversal path |
| 5 | Settlement worker + ledger, integration tests, CI, these docs |

## Service boundaries

Every service owns exactly one SQLite file and talks to every other service only over
HTTP - no service ever opens another service's database file. This is why settlement
polls the gateway's API instead of reading `gateway.db` directly, even though in this
monorepo-style layout it technically could.
