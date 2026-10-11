"""Training/serving parity: the Redis features must equal the offline ones, row for row."""

import fakeredis

from ml.check_parity import mismatches, replay
from ml.generate_data import generate
from ml.offline_features import compute_features


def test_redis_features_match_offline_features():
    df = generate(n=3000, seed=7)
    r = fakeredis.FakeRedis(decode_responses=True)

    offline = compute_features(df)
    online = replay(r, df, prefix="parity")

    bad = mismatches(offline, online)
    assert not bad.any(), offline[bad].head().join(online[bad].head(), rsuffix="_redis")
    # Sanity: the sample actually exercises the windows, not just all-ones.
    assert offline["attempts_per_ip_60s"].max() > 10
    assert offline["decline_rate_ip_5m"].max() > 0.5
