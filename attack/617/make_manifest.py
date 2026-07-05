#!/usr/bin/env python3
"""SHA256 manifest of everything in artifacts/ plus the scripts."""
import hashlib, os, sys

root = os.path.dirname(os.path.abspath(__file__))
out = []
for d in ('.', 'artifacts'):
    p = os.path.join(root, d)
    for fn in sorted(os.listdir(p)):
        fp = os.path.join(p, fn)
        if os.path.isfile(fp) and fn != 'MANIFEST.sha256':
            h = hashlib.sha256(open(fp, 'rb').read()).hexdigest()
            out.append(f"{h}  {os.path.relpath(fp, root)}")
with open(os.path.join(root, 'artifacts', 'MANIFEST.sha256'), 'w') as f:
    f.write('\n'.join(out) + '\n')
print('\n'.join(out))
