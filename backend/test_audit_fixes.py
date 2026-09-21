import urllib.request
import json
import time

def call_diag(message, eq_id=1, phone="+2347010299562"):
    url = "http://localhost:8080/api/diagnose"
    payload = json.dumps({"message": message, "equipment_id": eq_id, "phone_number": phone}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
    dt = time.time() - t0
    return dt, json.loads(body)

print("=" * 60)
print("TEST 1: GREETING FAST-PATH ('hi')")
print("=" * 60)
dt1, res1 = call_diag("hi")
print(f"Latency: {dt1*1000:.2f} ms")
print(f"Response: {res1}")

print("\n" + "=" * 60)
print("TEST 2: SANY PILOT PRESSURE SPEC (TEST-047 GROUND TRUTH)")
print("=" * 60)
dt2, res2 = call_diag("what is the pilot system pressure on a SANY SY215C")
print(f"Latency: {dt2:.2f} s")
print(f"Response:\n{res2}")

print("\n" + "=" * 60)
print("TEST 3: ACOUSTIC SYMPTOM WITH LIVE NORMAL BASELINE TELEMETRY")
print("=" * 60)
dt3, res3 = call_diag("my machine is making a weird sound", eq_id=1)
print(f"Latency: {dt3:.2f} s")
print(f"Response:\n{res3}")
