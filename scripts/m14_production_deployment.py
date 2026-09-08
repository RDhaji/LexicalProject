import hashlib, http.client, json, os, sqlite3, subprocess, time
from datetime import datetime, timezone

t_start = time.perf_counter()
base_dir = '/Users/rd/Desktop/LexicalProject'

# 1. Manifest and Artifact Attestation
manifest_path = os.path.join(base_dir, 'dist/RELEASE_MANIFEST.json')
assert os.path.exists(manifest_path), 'Missing RELEASE_MANIFEST.json'
with open(manifest_path) as f:
    manifest = json.load(f)

db_path = os.path.join(base_dir, 'dist/data/lexical_graph.db')
assert os.path.exists(db_path), f'Missing distribution DB artifact at {db_path}'

h = hashlib.sha256()
with open(db_path, 'rb') as f:
    while b := f.read(65536): h.update(b)
actual_sha = h.hexdigest()
assert actual_sha == manifest['artifacts']['lexical_graph.db']['sha256'], 'SHA256 mismatch'

# 2. Client Distribution Bundle Integrity
required_client_files = ['index.html', 'manifest.json', 'sw.js', 'worker.js', 'db_client.js', 'workspace_client.js', 'graph_renderer.js']
for fname in required_client_files:
    target = os.path.join(base_dir, 'dist/client', fname)
    assert os.path.exists(target) and os.path.getsize(target) > 0, f'Missing client asset: {fname}'

# 3. HTTP-206 Byte-Range Streaming Server Verification
srv = subprocess.Popen(['python3', os.path.join(base_dir, 'serve_client.py')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.5)
try:
    conn = http.client.HTTPConnection('localhost', 8080, timeout=5)
    conn.request('GET', '/dist/data/lexical_graph.db', headers={'Range': 'bytes=0-15'})
    res = conn.getresponse()
    header_bytes = res.read()
    assert res.status == 206, f'Expected HTTP 206 Partial Content, got {res.status}'
    assert header_bytes.startswith(b'SQLite format 3\x00'), f'Corrupt SQLite header: {header_bytes}'
finally:
    srv.terminate()
    srv.wait()

# 4. Vertical Slice Latency Verification on Deployed DB (<250ms SLA)
conn = sqlite3.connect(db_path)
cur = conn.cursor()
latencies = []
for lemma in ['run', 'fast', 'happy', 'go', 'good', 'bad', 'bank']:
    t0 = time.perf_counter()
    cur.execute('SELECT id FROM lexemes WHERE lemma = ? LIMIT 1', (lemma,))
    assert cur.fetchone() is not None, f"Missing fixture '{lemma}' in deployed DB"
    latencies.append((time.perf_counter() - t0) * 1000)
conn.close()
max_lat = max(latencies)
assert max_lat < 250, f'Latency SLA breach: {max_lat:.2f}ms >= 250ms'

# 5. Lock Milestone 14 to PROGRESS.md
entry = f"""
## Milestone 14: Production Deployment & Live Distribution Verification
- Status: COMPLETED
- Timestamp: {datetime.now(timezone.utc).isoformat()}
- Deployment Target: dist/
- Verification Gates:
  - Artifact SHA256 Match: PASSED ({actual_sha})
  - Client Bundle Assets (7/7): PASSED
  - HTTP-206 Byte-Range Partial Content: PASSED (Status 206, valid SQLite header)
  - Vertical Slice SLA Latency: PASSED (max {max_lat:.2f}ms < 250ms)
- Status: PRODUCTION RELEASE DEPLOYED
- Immediate Next: None (All Scheduled Milestones Complete)
"""
with open(os.path.join(base_dir, 'PROGRESS.md'), 'a') as f:
    f.write(entry)

print(f'M14 Deployment Verification PASSED (4/4 checks) in {time.perf_counter() - t_start:.2f}s | Max Latency: {max_lat:.2f}ms')
