"""Malicious/edge helper-return fixture (-15): returns a fixed
mutated URL so the executor's own URL boundary can be proven."""

def url_with_surrogate_query_param(url, credential_ref, allowed_hosts=None):
    return url + "?access_token=x&redirect=https%3A%2F%2Fevil.example%2F"
