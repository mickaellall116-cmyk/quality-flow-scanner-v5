"""Placement-faithful NONSECRET fixture stub (-17).

Mirrors the sanctioned helper construction (url_with_surrogate_
query_param: append exactly one (placement_param, value) pair via
urllib.parse.urlencode) using the PROVEN placement parameter for
custom.twelvedata and a dummy fixture value. Exists because the -11
stub returns the URL unchanged (bare query), which the r3 boundary
correctly refuses: the final credentialized URL must carry exactly
one nonempty credential parameter. Never a real credential."""
import urllib.parse

PLACEMENT_PARAM = "apikey"  # proven: see PLACEMENT_PROOF.md


def url_with_surrogate_query_param(url, credential_ref, allowed_hosts=None):
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query.append((PLACEMENT_PARAM, "FIXTURE"))
    return urllib.parse.urlunsplit(
        parsed._replace(query=urllib.parse.urlencode(query)))
