# ai-excited-01 — Phoenix from a Supernova

Entry for make.fun's **"Make the AI judge excited"** bounty ($250).

## The image

One colossal phoenix-firebird bursting upward out of a supernova core:
layered flame wings sweeping the whole frame on a diagonal, a blinding
white-gold heart, a thin tilted ring of starlight cutting across the
blast, embers streaming upward, and a tiny black mountain ridge along
the bottom for scale. Hot orange/gold/cyan on deep indigo — one huge
shape that reads instantly, even small.

## How to run

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Writes `out/entry.png` (1024x1024, under 1 MiB). Python 3.13, pure
standard library only — no Pillow, no numpy, no network. Deterministic:
two runs produce byte-identical files.

## How it draws

1. A smooth "heat" field is painted at 256x256 with distance-field math
   (radial core glow, vertical flame body, two swept sine-ripple flame
   wings, a tail, a tilted ring, a mountain silhouette).
2. The field is bilinear-upscaled to 1024x1024 and mapped through a
   256-entry colour palette (indigo → violet → red → orange → gold →
   white-hot).
3. Full-resolution detail is stamped straight into the pixel buffer:
   stars, rising embers, cyan streaks at the wing tips.
4. The PNG is encoded by hand with `zlib` + `struct`.

## License

MIT — see [LICENSE](LICENSE).
