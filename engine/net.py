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
            code = getattr(e.response, "status_code", None)
            if code is not None and 400 <= code < 500 and code != 429:
                break  # missing / forbidden: retrying won't help
            # connection / DNS drops tend to last a while: back off longer than for a server hiccup
            time.sleep((10 if isinstance(e, requests.ConnectionError) else 2) * (i + 1))
    raise last
