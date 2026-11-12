"""HTTP helper. Uses the OS certificate store (truststore) so it works behind TLS-inspecting proxies."""
import time

import requests

try:
    import truststore

    truststore.inject_into_ssl()
except Exception:  # pragma: no cover
    pass

USER_AGENT = "soundtrack-engine/0.1 (personal research project; matches data curves to CC-licensed music; 1 req / 2 s)"

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT


def get(url, *, retries=3, timeout=60, **kw):
    last = None
    for i in range(retries):
        try:
            r = _session.get(url, timeout=timeout, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last
