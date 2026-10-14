import json, sqlite3, time, urllib.request, urllib.error, os

DB = os.path.expanduser("~/.omniroute/storage.sqlite")
key = sqlite3.connect(DB).execute("SELECT key FROM api_keys WHERE name='claude-test'").fetchone()[0]
MODEL = "openrouter/dots-studio/dots-3-note-preview:free"
URL = "http://localhost:20128/v1/chat/completions"
BASE = os.path.dirname(os.path.abspath(__file__))

results = []
for item in ("a", "b", "c"):
    with open(os.path.join(BASE, "fixtures", f"prompt_{item}.txt")) as f:
        prompt = f.read()
    payload = {"model": MODEL, "temperature": 0, "max_tokens": 700,
               "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    t0 = time.time()
    rec = {"item": item, "requested_model": MODEL, "temperature": 0, "max_tokens": 700}
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read())
            rec["http_status"] = resp.status
        with open(os.path.join(BASE, "outputs", f"omni_{item}.raw.json"), "w") as f:
            json.dump(body, f, indent=1)
        text = body["choices"][0]["message"]["content"] or ""
        with open(os.path.join(BASE, "outputs", f"omni_{item}.md"), "w") as f:
            f.write(text)
        rec["returned_model"] = body.get("model")
        rec["usage"] = body.get("usage")
        rec["finish_reason"] = body["choices"][0].get("finish_reason")
        rec["chars"] = len(text)
    except urllib.error.HTTPError as e:
        rec["http_status"] = e.code
        rec["error"] = e.read().decode(errors="replace")[:500]
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"[:500]
    rec["latency_s"] = round(time.time() - t0, 3)
    results.append(rec)
    print(json.dumps(rec))

with open(os.path.join(BASE, "attempts.json"), "w") as f:
    json.dump(results, f, indent=1)
