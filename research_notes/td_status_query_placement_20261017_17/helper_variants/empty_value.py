"""Edge helper-return fixture (-17): placement key with an empty value must refuse."""

def url_with_surrogate_query_param(url, credential_ref, allowed_hosts=None):
    return url + "?apikey="
