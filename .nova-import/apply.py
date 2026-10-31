"""Decode a declared, hash-checked research bundle; no arbitrary archive extraction."""
from pathlib import Path, PurePosixPath
import base64, gzip, hashlib, io, json, lzma, struct, tarfile

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / '.nova-import'
ready = json.loads((HERE / 'ready.json').read_text())
encoded = ''.join((HERE / f'part{i:02}.b64').read_text().strip() for i in range(ready['parts']))
payload = base64.b64decode(encoded, validate=True)
assert hashlib.sha256(payload).hexdigest() == ready['payload_sha256'], 'Transfer checksum mismatch'
raw = lzma.decompress(payload)
assert len(raw) < 8_000_000, 'Unexpected archive size'
with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as tf:
    members = tf.getmembers()
    assert all(m.isfile() for m in members), 'Only regular files are permitted'
    names = [m.name for m in members]
    assert len(names) == len(set(names)), 'Duplicate paths'
    body = {m.name: tf.extractfile(m).read() for m in members}
manifest_raw = body.pop('.nova-import/manifest.json')
assert hashlib.sha256(manifest_raw).hexdigest() == ready['manifest_sha256']
manifest = json.loads(manifest_raw)
assert set(body) == set(manifest), 'Undeclared archive members'
for name, value in body.items():
    rel = PurePosixPath(name)
    assert not rel.is_absolute() and '..' not in rel.parts
    assert len(value) == manifest[name]['size']
    assert hashlib.sha256(value).hexdigest() == manifest[name]['sha256'], name
    dest = ROOT / name
    assert dest.resolve().is_relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(value)

# Lossless numeric packing avoids shipping repeated textual n-gram counts.
meta = json.loads((HERE / 'counts-meta.json').read_text(encoding='utf-8'))
order = meta.pop('__group_order__')
expected = meta.pop('__json_sha256__')
alphabet = meta['alphabet']
N = len(alphabet)
packed = (HERE / 'counts.bin').read_bytes()
offset = 0
groups = {}
for name in order:
    n = struct.unpack_from('<I', packed, offset)[0]
    offset += 4
    length = N*N + 3*N
    a = struct.unpack_from('<' + 'H'*length, packed, offset)
    offset += 2*length
    u, g = a[:N], a[N:N+N*N]
    first, last = a[N+N*N:N+N*N+N], a[-N:]
    assert sum(u) == n and sum(first) == sum(last)
    assert sum(g) == n - sum(first)
    groups[name] = {
        'n': n,
        'u': [[c, v] for c, v in zip(alphabet, u) if v],
        'g': [[alphabet[i], alphabet[j], g[i*N+j]] for i in range(N) for j in range(N) if g[i*N+j]],
        'first': [[c, v] for c, v in zip(alphabet, first) if v],
        'last': [[c, v] for c, v in zip(alphabet, last) if v],
    }
assert offset == len(packed)
meta['groups'] = groups
text = json.dumps(meta, ensure_ascii=False, separators=(',', ':')).encode()
assert hashlib.sha256(text).hexdigest() == expected == ready['original_counts_json_sha256'], 'Decoded statistics differ from original F4'
(ROOT / 'data/v4_raw_ngrams.json.gz').write_bytes(gzip.compress(text, mtime=0))
print(f'PASS: {len(body)} declared files, {len(groups)} unchanged statistical groups, all SHA-256 checks')
