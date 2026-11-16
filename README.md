# ai-excited-01 — Phoenix out of a supernova

A pure-stdlib Python program that procedurally draws one 1024x1024 PNG
for make.fun's "Make the AI judge excited" bounty: a colossal phoenix
bursting upward out of a supernova core, wings swept back, embers
trailing, over a deep indigo starfield, with a thin glowing orbit ring
tilted across the core and a tiny mountain ridge at the bottom for scale.

## Run

```sh
MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py
```

Writes `entry.png` into `$MAKEFUN_OUTPUT_DIR` (default `/output`).
Deterministic: two runs produce byte-identical files. No third-party
modules, no network — only `zlib`, `struct`, `math`, `os`, `random`.
