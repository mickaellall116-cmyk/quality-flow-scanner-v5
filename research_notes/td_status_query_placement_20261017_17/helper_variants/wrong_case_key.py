"""Edge helper-return fixture (-17): wrong-case placement key must refuse (exact-key binding)."""

def url_with_surrogate_query_param(url, credential_ref, allowed_hosts=None):
    return url + "?APIKEY=FIXTURE"
