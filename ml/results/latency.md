
<!-- run 2026-10-11 12:21, fraud check on -->
| measurement | n | p50 ms | p95 ms | p99 ms | max ms |
|---|---|---|---|---|---|
| /v1/score (direct) | 500 | 5.6 | 8.4 | 17.8 | 38.9 |
| gateway payment intent, fraud check on | 200 | 60.1 | 83.6 | 94.6 | 110.5 |

<!-- run 2026-10-11 12:22, fraud check off -->
| measurement | n | p50 ms | p95 ms | p99 ms | max ms |
|---|---|---|---|---|---|
| /v1/score (direct) | 100 | 5.7 | 7.7 | 15.5 | 15.6 |
| gateway payment intent, fraud check off | 200 | 42.7 | 64.7 | 85.8 | 121.2 |
