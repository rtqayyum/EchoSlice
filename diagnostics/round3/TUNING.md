# EchoSlice v3: how its defaults were fixed

All tuning used held-out seeds 101–104, which no campaign run uses (campaign seeds are 1–30). Each number is the mean gap (%) of window-averaged user MOS to the best static split of the same cell on those seeds; the bracket is the worst-slice SLA. Raw runs: `cache.jsonl`, harness: `tune.py`.

## Steps

1. **Pairwise sign search from a count prior (first v3 sketch).** Mean gap 1.28% on 9 cells, worse than v2 (0.98%). The trace showed why: one utility difference over 6 s has a standard deviation of about 0.15 MOS, close to the signal, so sign-based steps random-walk.
2. **Prior only, no probing.** With per-session reference rates of 4 Mb/s (video) and 10 Mb/s (gaming) the prior alone gave 2.25%. Rates of 6 Mb/s (a 1080p rung) and 12 Mb/s (a typical cloud-gaming stream) gave 0.29% on six stationary cells, the best of the four rate pairs tried. These became the slice-template defaults. The XR template (30 Mb/s) was not tuned.
3. **What to learn closed loop.** SPSA on a share offset (as in v1/v2) on top of the prior: −0.73%. Pairwise sign search: +0.14%. SPSA on the log of the per-session rates (rate space, two parameters for three slices): −1.13% on 7 cells, worst 0.70%. Rate space was kept, because the learned per-session rates stay valid when session counts change.
4. **Probe size.** In rate space, probes of ±10% gave −0.50% (7 cells), ±15% gave −1.13%, ±25% gave −0.96%. ±15% kept.
5. **Wrong template.** With all reference rates halved, the prior alone loses 4.76% on average (worst 9.0%); with probing the gap is 0.13%. With rates doubled: prior alone −0.03% (worst 3.74%), with probing −0.60% (worst 3.05%).
6. **SLA weight.** λ = 0.5 and 1 (and λ = 2, tested with ±10% probes) raise the worst-slice SLA in the video-heavy cell (0.31 → 0.50, 0.61, 0.55) but not in every cell, and they cost mean QoE (mean gap −0.66% and +0.34% on 7 cells; +1.25% on 9 cells for λ = 2). λ stays a campaign sweep, not a default.

## Final defaults (`sim/slicers.py`, `EchoSlice3`)

Prior from session counts × reference rates (video 6 Mb/s, gaming 12 Mb/s, XR 30 Mb/s); bulk gets the rest. SPSA on log-rates, probes ±15% (c0 = 0.15), a0 = 0.6, A = 5, Spall exponents 0.602 / 0.101, step cap 0.3, restart on a ≥ max(2, 25%) change in a rate-bounded slice's session count, warm-up 30 s, hold 12 s scored on the last 6 s. λ = 0 unless stated.

Held-out result of the defaults (7 cells, λ = 0): M1 shareable 0.02%, M1 strict 0.35%, M2 shareable 0.15%, M3 strict 0.61%, 24/8/6 strict 0.70%, day cycle strict −7.61%, flash crowd strict −2.11%. Forecast + 20% on the same seeds: 0.88, 0.67, 0.23, 0.69, 0.64, −7.53, −1.07. Worst-slice SLA of v3 is at least that of Forecast + 20% in all seven cells.

## QoE monitor variant (kept off)

The QoE monitor scores a video player that completed no segment inside the scoring window as delivering no video (MOS 1). A variant that scores it at the quality of its last segment (`hold_last`) made v3 worse on the same 7 cells and seeds: mean gap −0.33% (worst 1.26%) against −1.13% (worst 0.70%), and λ = 1 became much worse (+1.56%). The original monitor is kept for every slicer.
