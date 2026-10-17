"""Edge helper-return fixture (-17): percent-encoded extra key must refuse after decoding."""

def url_with_surrogate_query_param(url, credential_ref, allowed_hosts=None):
    return url + "?apikey=FIXTURE&acc%65ss_token=FIXTURE"
