# EchoSlice HPC campaign report

Generated 2026-10-26 16:06:45 (job tag j600466).

## Completion

| exp | title | jobs | done | errors | missing | complete |
|---|---|---|---|---|---|---|
| E1 | effect size | 35100 | 35100 | 0 | 0 | yes |
| E2 | slicer period | 6840 | 6840 | 0 | 0 | yes |
| E4 | QoE-model sensitivity | 3600 | 3600 | 0 | 0 | yes |
| E5 | forecast headroom | 900 | 900 | 0 | 0 | yes |
| E6 | dynamic load | 16920 | 16920 | 0 | 0 | yes |
| E7 | unbalanced and shifting | 21990 | 21990 | 0 | 0 | yes |
| E9 | ablations | 2700 | 2700 | 0 | 0 | yes |
| E10 | imperfect telemetry | 4320 | 4320 | 0 | 0 | yes |
| E11 | app hints | 1080 | 1080 | 0 | 0 | yes |
| E12 | XR and L4S | 9990 | 9990 | 0 | 0 | yes |
| E13 | theory checks | 6090 | 6090 | 0 | 0 | yes |
| E14 | convergence | 1080 | 1080 | 0 | 0 | yes |

## E1. Effect size

Gap = loss in mean user MOS against the best static share (leave-one-seed-out, paired by seed), slicer period 1 s.

| family | slicer | cells | mean_gap_pct | worst_gap_pct | cells_gap_ge5 | cells_ci_above5 | mos_video | mos_game | mos_bulk |
|---|---|---|---|---|---|---|---|---|---|
| 2-slice shareable | Usage-proportional | 9 | 3.71 | 5.14 | 3 | 0 | 4.55 |  | 3.75 |
| 2-slice shareable | Forecast + 20% | 9 | 1.37 | 3.24 | 0 | 0 | 4.79 |  | 3.12 |
| 2-slice shareable | Open-loop QoE | 9 | 2.56 | 3.96 | 0 | 0 | 4.54 |  | 4.16 |
| 2-slice shareable | Open-loop QoE + SLA (1) | 9 | 2.56 | 3.96 | 0 | 0 | 4.54 |  | 4.16 |
| 2-slice shareable | EchoSlice-lite | 9 | 0.59 | 1.35 | 0 | 0 | 4.72 |  | 3.82 |
| 2-slice shareable | EchoSlice (v2) | 9 | 0.59 | 1.35 | 0 | 0 | 4.72 |  | 3.82 |
| 2-slice shareable | EchoSlice (v3) | 9 | 0.59 | 0.86 | 0 | 0 | 4.76 |  | 3.56 |
| 2-slice shareable | EchoSlice (v3), SLA (1) | 9 | 0.75 | 1.26 | 0 | 0 | 4.73 |  | 3.70 |
| 2-slice shareable | Static equal | 9 | 0.65 | 1.73 | 0 | 0 | 4.69 |  | 3.95 |
| 2-slice shareable | No slicing (PF) | 9 | 0.37 | 0.59 | 0 | 0 | 4.79 |  | 3.46 |
| 2-slice strict | Usage-proportional | 9 | 3.21 | 4.99 | 0 | 0 | 4.59 |  | 3.68 |
| 2-slice strict | Forecast + 20% | 9 | 1.35 | 3.21 | 0 | 0 | 4.79 |  | 3.11 |
| 2-slice strict | Open-loop QoE | 9 | 2.61 | 3.70 | 0 | 0 | 4.53 |  | 4.17 |
| 2-slice strict | Open-loop QoE + SLA (1) | 9 | 2.61 | 3.70 | 0 | 0 | 4.53 |  | 4.17 |
| 2-slice strict | EchoSlice-lite | 9 | 0.59 | 1.74 | 0 | 0 | 4.71 |  | 3.82 |
| 2-slice strict | EchoSlice (v2) | 9 | 0.59 | 1.74 | 0 | 0 | 4.71 |  | 3.82 |
| 2-slice strict | EchoSlice (v3) | 9 | 0.60 | 0.72 | 0 | 0 | 4.76 |  | 3.56 |
| 2-slice strict | EchoSlice (v3), SLA (1) | 9 | 0.69 | 0.90 | 0 | 0 | 4.73 |  | 3.71 |
| 2-slice strict | Static equal | 9 | 0.68 | 1.73 | 0 | 0 | 4.69 |  | 3.94 |
| 3-slice shareable | Usage-proportional | 9 | 9.94 | 12.31 | 9 | 9 | 4.65 | 2.13 | 3.92 |
| 3-slice shareable | Forecast + 20% | 9 | 2.73 | 4.31 | 0 | 0 | 4.81 | 3.71 | 3.04 |
| 3-slice shareable | Open-loop QoE | 9 | 4.74 | 5.59 | 1 | 1 | 4.61 | 3.11 | 4.10 |
| 3-slice shareable | Open-loop QoE + SLA (1) | 9 | 4.48 | 5.28 | 1 | 0 | 4.61 | 3.17 | 4.09 |
| 3-slice shareable | DRL, replay-trained | 9 | 0.95 | 1.84 | 0 | 0 | 4.65 | 4.34 | 3.26 |
| 3-slice shareable | DRL, loop-trained | 9 | 0.44 | 0.56 | 0 | 0 | 4.73 | 4.26 | 3.20 |
| 3-slice shareable | EchoSlice-lite | 9 | 0.50 | 0.76 | 0 | 0 | 4.70 | 4.18 | 3.40 |
| 3-slice shareable | EchoSlice (v2) | 9 | 0.50 | 0.76 | 0 | 0 | 4.70 | 4.18 | 3.40 |
| 3-slice shareable | EchoSlice (v3) | 9 | 0.91 | 1.45 | 0 | 0 | 4.74 | 4.14 | 3.18 |
| 3-slice shareable | EchoSlice (v3), SLA (1) | 9 | 1.56 | 2.60 | 0 | 0 | 4.67 | 4.24 | 3.17 |
| 3-slice shareable | Static equal | 9 | 0.17 | 0.56 | 0 | 0 | 4.69 | 4.12 | 3.63 |
| 3-slice shareable | No slicing (PF) | 9 | 1.12 | 1.95 | 0 | 0 | 4.80 | 3.78 | 3.40 |
| 3-slice strict | Usage-proportional | 9 | 12.73 | 18.17 | 9 | 9 | 4.41 | 2.14 | 3.91 |
| 3-slice strict | Forecast + 20% | 9 | 2.36 | 3.88 | 0 | 0 | 4.80 | 3.71 | 3.02 |
| 3-slice strict | Open-loop QoE | 9 | 4.59 | 5.52 | 1 | 0 | 4.58 | 3.12 | 4.11 |
| 3-slice strict | Open-loop QoE + SLA (1) | 9 | 4.33 | 5.29 | 1 | 0 | 4.58 | 3.18 | 4.10 |
| 3-slice strict | DRL, replay-trained | 9 | 1.44 | 2.28 | 0 | 0 | 4.59 | 4.30 | 3.26 |
| 3-slice strict | DRL, loop-trained | 9 | 0.67 | 1.49 | 0 | 0 | 4.76 | 4.00 | 3.23 |
| 3-slice strict | EchoSlice-lite | 9 | 0.74 | 1.08 | 0 | 0 | 4.70 | 4.03 | 3.42 |
| 3-slice strict | EchoSlice (v2) | 9 | 0.74 | 1.08 | 0 | 0 | 4.70 | 4.03 | 3.42 |
| 3-slice strict | EchoSlice (v3) | 9 | 0.87 | 1.45 | 0 | 0 | 4.73 | 4.01 | 3.27 |
| 3-slice strict | EchoSlice (v3), SLA (1) | 9 | 2.23 | 3.19 | 0 | 0 | 4.59 | 4.04 | 3.40 |
| 3-slice strict | Static equal | 9 | 0.21 | 0.70 | 0 | 0 | 4.66 | 4.12 | 3.59 |

![gap](../figures/fig_gap.png)

![pareto](../figures/fig_pareto.png)


## E2. Slicer period

Standard deviation of the video-slice share, by slicer period (columns, s), mean over ABR rules:

| slicer         |   seg_dur |     0.1 |     0.2 |     0.5 |   1.0 |     2.0 |     5.0 |
|:---------------|----------:|--------:|--------:|--------:|------:|--------:|--------:|
| echoslice      |         2 |   0.046 |   0.046 |   0.048 | 0.047 |   0.045 |   0.044 |
| echoslice      |         4 |   0.052 |   0.05  |   0.05  | 0.05  |   0.046 |   0.046 |
| echoslice      |         6 |   0.057 |   0.057 |   0.057 | 0.056 |   0.054 |   0.055 |
| echoslice-lite |         2 |   0.046 |   0.046 |   0.048 | 0.047 |   0.045 |   0.044 |
| echoslice-lite |         4 |   0.052 |   0.05  |   0.05  | 0.05  |   0.046 |   0.046 |
| echoslice-lite |         6 |   0.057 |   0.057 |   0.057 | 0.056 |   0.054 |   0.055 |
| echoslice3     |         2 |   0.049 |   0.046 |   0.048 | 0.049 |   0.049 |   0.054 |
| echoslice3     |         4 |   0.055 |   0.054 |   0.061 | 0.057 |   0.058 |   0.058 |
| echoslice3     |         6 |   0.061 |   0.068 |   0.066 | 0.064 |   0.064 |   0.068 |
| forecast+20%   |         2 |   0.132 |   0.079 |   0.049 | 0.041 |   0.037 |   0.035 |
| forecast+20%   |         4 |   0.215 |   0.12  |   0.063 | 0.046 |   0.039 |   0.035 |
| forecast+20%   |         6 |   0.24  |   0.154 |   0.076 | 0.05  |   0.037 |   0.032 |
| ol-qoe+10%     |         2 |   0.022 |   0.022 |   0.022 | 0.022 |   0.022 |   0.022 |
| ol-qoe+10%     |         4 |   0.023 |   0.023 |   0.023 | 0.023 |   0.023 |   0.023 |
| ol-qoe+10%     |         6 |   0.024 |   0.023 |   0.024 | 0.024 |   0.024 |   0.024 |
| static         |         2 | nan     | nan     | nan     | 0     | nan     | nan     |
| static         |         4 | nan     | nan     | nan     | 0     | nan     | nan     |
| static         |         6 | nan     | nan     | nan     | 0     | nan     | nan     |
| usage-prop     |         2 |   0.072 |   0.056 |   0.027 | 0.018 |   0.011 |   0.005 |
| usage-prop     |         4 |   0.085 |   0.066 |   0.033 | 0.021 |   0.01  |   0.005 |
| usage-prop     |         6 |   0.089 |   0.071 |   0.034 | 0.019 |   0.01  |   0.004 |

Mean user MOS:

| slicer         |   seg_dur |     0.1 |     0.2 |     0.5 |   1.0 |     2.0 |     5.0 |
|:---------------|----------:|--------:|--------:|--------:|------:|--------:|--------:|
| echoslice      |         2 |   4.365 |   4.362 |   4.362 | 4.368 |   4.377 |   4.378 |
| echoslice      |         4 |   4.389 |   4.392 |   4.392 | 4.391 |   4.396 |   4.396 |
| echoslice      |         6 |   4.373 |   4.378 |   4.379 | 4.386 |   4.377 |   4.385 |
| echoslice-lite |         2 |   4.365 |   4.362 |   4.362 | 4.368 |   4.377 |   4.378 |
| echoslice-lite |         4 |   4.389 |   4.392 |   4.392 | 4.391 |   4.396 |   4.396 |
| echoslice-lite |         6 |   4.373 |   4.378 |   4.379 | 4.386 |   4.377 |   4.385 |
| echoslice3     |         2 |   4.393 |   4.385 |   4.388 | 4.386 |   4.388 |   4.383 |
| echoslice3     |         4 |   4.372 |   4.384 |   4.379 | 4.381 |   4.384 |   4.376 |
| echoslice3     |         6 |   4.359 |   4.366 |   4.357 | 4.36  |   4.36  |   4.353 |
| forecast+20%   |         2 |   4.362 |   4.355 |   4.35  | 4.339 |   4.252 |   4.159 |
| forecast+20%   |         4 |   4.286 |   4.366 |   4.354 | 4.331 |   4.252 |   4.159 |
| forecast+20%   |         6 |   4.261 |   4.384 |   4.391 | 4.37  |   4.281 |   4.183 |
| ol-qoe+10%     |         2 |   4.252 |   4.252 |   4.237 | 4.211 |   4.198 |   4.202 |
| ol-qoe+10%     |         4 |   4.252 |   4.253 |   4.236 | 4.213 |   4.209 |   4.205 |
| ol-qoe+10%     |         6 |   4.257 |   4.259 |   4.238 | 4.217 |   4.21  |   4.211 |
| static         |         2 | nan     | nan     | nan     | 4.409 | nan     | nan     |
| static         |         4 | nan     | nan     | nan     | 4.413 | nan     | nan     |
| static         |         6 | nan     | nan     | nan     | 4.419 | nan     | nan     |
| usage-prop     |         2 |   3.91  |   3.972 |   3.985 | 3.991 |   4.055 |   4.077 |
| usage-prop     |         4 |   3.843 |   3.887 |   3.989 | 3.992 |   4.06  |   4.077 |
| usage-prop     |         6 |   3.676 |   3.844 |   3.923 | 3.988 |   4.068 |   4.088 |

![resonance](../figures/fig_resonance.png)


## E4. QoE-model sensitivity

Gap (%) by P.1203 device / bulk-MOS saturation point:

| cell           | slicer         |   mobile / 50 Mb/s |   mobile / 100 Mb/s |   mobile / 200 Mb/s |   pc / 50 Mb/s |   pc / 100 Mb/s |   pc / 200 Mb/s |
|:---------------|:---------------|-------------------:|--------------------:|--------------------:|---------------:|----------------:|----------------:|
| 24v/8g/6b dyn  | echoslice      |               0.67 |                0.53 |                0.5  |           0.59 |            0.57 |            0.55 |
| 24v/8g/6b dyn  | echoslice-lite |               0.67 |                0.53 |                0.5  |           0.59 |            0.57 |            0.55 |
| 24v/8g/6b dyn  | echoslice3     |               1.61 |                1.27 |                1.08 |           0.95 |            0.75 |            0.59 |
| 24v/8g/6b dyn  | forecast+20%   |               2.95 |                2.63 |                2.46 |           2.26 |            2.03 |            1.86 |
| 24v/8g/6b dyn  | ol-qoe+10%     |               5.64 |                5.73 |                6.13 |           3.96 |            4.23 |            4.54 |
| 24v/8g/6b dyn  | shared         |               1.96 |                1.79 |                1.74 |           1.28 |            1.21 |            1.16 |
| 24v/8g/6b dyn  | static         |               0.05 |               -0    |                0.03 |          -0.1  |           -0.05 |           -0.01 |
| 24v/8g/6b dyn  | usage-prop     |               9.23 |                9.36 |                9.61 |           9.2  |            9.43 |            9.69 |
| 32v/0g/6b tput | echoslice      |               0.37 |                0.39 |                0.45 |           0.64 |            0.77 |            0.9  |
| 32v/0g/6b tput | echoslice-lite |               0.37 |                0.39 |                0.45 |           0.64 |            0.77 |            0.9  |
| 32v/0g/6b tput | echoslice3     |               0.62 |                0.48 |                0.39 |           0.53 |            0.46 |            0.42 |
| 32v/0g/6b tput | forecast+20%   |               1.5  |                1.16 |                0.91 |           0.96 |            0.73 |            0.55 |
| 32v/0g/6b tput | ol-qoe+10%     |               5.51 |                5.43 |                5.74 |           2.4  |            2.55 |            2.82 |
| 32v/0g/6b tput | shared         |               0.89 |                0.64 |                0.47 |           0.4  |            0.27 |            0.16 |
| 32v/0g/6b tput | static         |               0.08 |                0.11 |                0.17 |           0.47 |            0.62 |            0.78 |
| 32v/0g/6b tput | usage-prop     |               2.59 |                2.48 |                2.48 |           3.21 |            3.22 |            3.3  |

## E5. Forecast headroom

| fam               |     h |   mos_user |   mos_video |   mos_game |   mos_bulk |   x_video |   x_game |   bulk_mbps |
|:------------------|------:|-----------:|------------:|-----------:|-----------:|----------:|---------:|------------:|
| 2-slice shareable | 0     |      3.198 |       2.96  |    nan     |      4.466 |     0.056 |  nan     |      60.429 |
| 2-slice shareable | 0.025 |      3.903 |       3.829 |    nan     |      4.298 |     0.219 |  nan     |      49.846 |
| 2-slice shareable | 0.05  |      4.518 |       4.633 |    nan     |      3.909 |     0.508 |  nan     |      31.701 |
| 2-slice shareable | 0.075 |      4.581 |       4.742 |    nan     |      3.725 |     0.599 |  nan     |      25.738 |
| 2-slice shareable | 0.1   |      4.585 |       4.765 |    nan     |      3.624 |     0.642 |  nan     |      22.992 |
| 2-slice shareable | 0.15  |      4.575 |       4.792 |    nan     |      3.416 |     0.714 |  nan     |      18.26  |
| 2-slice shareable | 0.2   |      4.555 |       4.809 |    nan     |      3.204 |     0.775 |  nan     |      14.536 |
| 2-slice shareable | 0.3   |      4.511 |       4.826 |    nan     |      2.835 |     0.858 |  nan     |       9.722 |
| 2-slice shareable | 0.5   |      4.458 |       4.831 |    nan     |      2.472 |     0.935 |  nan     |       6.598 |
| 2-slice shareable | 1     |      4.446 |       4.829 |    nan     |      2.404 |     0.95  |  nan     |       6.064 |
| 2-slice strict    | 0     |      3.207 |       2.97  |    nan     |      4.468 |     0.056 |  nan     |      60.272 |
| 2-slice strict    | 0.025 |      3.937 |       3.87  |    nan     |      4.295 |     0.224 |  nan     |      49.686 |
| 2-slice strict    | 0.05  |      4.524 |       4.642 |    nan     |      3.896 |     0.513 |  nan     |      31.237 |
| 2-slice strict    | 0.075 |      4.581 |       4.739 |    nan     |      3.74  |     0.592 |  nan     |      26.122 |
| 2-slice strict    | 0.1   |      4.586 |       4.764 |    nan     |      3.632 |     0.638 |  nan     |      23.243 |
| 2-slice strict    | 0.15  |      4.573 |       4.79  |    nan     |      3.418 |     0.715 |  nan     |      18.276 |
| 2-slice strict    | 0.2   |      4.556 |       4.81  |    nan     |      3.201 |     0.776 |  nan     |      14.438 |
| 2-slice strict    | 0.3   |      4.502 |       4.825 |    nan     |      2.78  |     0.858 |  nan     |       9.148 |
| 2-slice strict    | 0.5   |      4.403 |       4.83  |    nan     |      2.128 |     0.936 |  nan     |       4.126 |
| 2-slice strict    | 1     |      4.373 |       4.83  |    nan     |      1.934 |     0.95  |  nan     |       3.201 |
| 3-slice shareable | 0     |      3.199 |       3.245 |      2.139 |      4.427 |     0.056 |    0.051 |      57.352 |
| 3-slice shareable | 0.025 |      3.931 |       4.438 |      2.191 |      4.223 |     0.24  |    0.051 |      45.509 |
| 3-slice shareable | 0.05  |      4.025 |       4.624 |      2.195 |      4.072 |     0.351 |    0.052 |      38.424 |
| 3-slice shareable | 0.075 |      4.105 |       4.759 |      2.254 |      3.961 |     0.424 |    0.052 |      33.568 |
| 3-slice shareable | 0.1   |      4.121 |       4.776 |      2.332 |      3.888 |     0.463 |    0.055 |      30.915 |
| 3-slice shareable | 0.15  |      4.243 |       4.801 |      3.02  |      3.645 |     0.524 |    0.108 |      23.955 |
| 3-slice shareable | 0.2   |      4.333 |       4.819 |      3.801 |      3.098 |     0.573 |    0.232 |      13.431 |
| 3-slice shareable | 0.3   |      4.31  |       4.827 |      4.142 |      2.467 |     0.606 |    0.324 |       6.28  |
| 3-slice shareable | 0.5   |      4.296 |       4.827 |      4.158 |      2.357 |     0.615 |    0.334 |       5.459 |
| 3-slice shareable | 1     |      4.297 |       4.826 |      4.159 |      2.362 |     0.616 |    0.334 |       5.488 |

![headroom](../figures/fig_headroom.png)


## E6. Dynamic load

Gap (%) against the best static share over the whole 1200 s run (leave-one-seed-out). 'Static tuned at deploy' is the best static share for the load before the change, kept through it.

| pattern | strict | slicer | seeds | gap_pct | gap_lo | gap_hi | mos_video | mos_game | mos_bulk |
|---|---|---|---|---|---|---|---|---|---|
| bulk_wave | False | Usage-proportional | 30 | 11.00 | 10.39 | 11.56 | 4.78 | 1.72 | 3.10 |
| bulk_wave | False | Forecast + 10% | 30 | 6.98 | 6.09 | 7.83 | 4.78 | 2.34 | 3.32 |
| bulk_wave | False | Forecast + 20% | 30 | 4.36 | 3.79 | 5.00 | 4.81 | 3.58 | 2.08 |
| bulk_wave | False | Forecast + 30% | 30 | 4.74 | 4.16 | 5.40 | 4.81 | 3.59 | 1.95 |
| bulk_wave | False | Forecast + 50% | 30 | 4.86 | 4.22 | 5.57 | 4.81 | 3.57 | 1.94 |
| bulk_wave | False | Open-loop QoE | 30 | 3.02 | 2.64 | 3.44 | 4.63 | 3.13 | 3.82 |
| bulk_wave | False | Open-loop QoE + SLA (1) | 30 | 2.88 | 2.51 | 3.28 | 4.63 | 3.16 | 3.82 |
| bulk_wave | False | DRL, replay-trained | 30 | 1.16 | 1.00 | 1.31 | 4.54 | 4.25 | 3.02 |
| bulk_wave | False | DRL, replay-trained, SLA (1) | 30 | 1.77 | 1.62 | 1.94 | 4.49 | 4.29 | 3.00 |
| bulk_wave | False | DRL, loop-trained | 30 | 0.20 | 0.14 | 0.26 | 4.64 | 4.17 | 3.01 |
| bulk_wave | False | DRL, loop-trained, SLA (1) | 30 | 0.26 | 0.18 | 0.33 | 4.62 | 4.18 | 3.04 |
| bulk_wave | False | EchoSlice-lite | 30 | 0.68 | 0.49 | 0.89 | 4.65 | 4.08 | 2.99 |
| bulk_wave | False | EchoSlice (v2) | 30 | 1.32 | 0.93 | 1.78 | 4.59 | 4.00 | 3.17 |
| bulk_wave | False | EchoSlice (v3) | 30 | 1.91 | 1.60 | 2.20 | 4.72 | 4.07 | 2.35 |
| bulk_wave | False | EchoSlice (v3), SLA (1) | 30 | 2.79 | 2.21 | 3.43 | 4.52 | 4.22 | 2.68 |
| bulk_wave | False | Static equal | 30 | 0.36 | 0.23 | 0.49 | 4.59 | 3.95 | 3.50 |
| bulk_wave | False | No slicing (PF) | 30 | 1.75 | 1.52 | 1.99 | 4.79 | 3.54 | 2.94 |
| bulk_wave | False | Static tuned at deploy | 30 | 1.04 | 0.94 | 1.15 | 4.74 | 4.08 | 2.52 |
| bulk_wave | True | Usage-proportional | 30 | 11.78 | 10.77 | 12.93 | 4.75 | 1.74 | 2.87 |
| bulk_wave | True | Forecast + 10% | 30 | 6.82 | 5.92 | 7.65 | 4.78 | 2.27 | 3.36 |
| bulk_wave | True | Forecast + 20% | 30 | 4.05 | 3.56 | 4.58 | 4.80 | 3.60 | 2.03 |
| bulk_wave | True | Forecast + 30% | 30 | 4.46 | 3.96 | 5.05 | 4.80 | 3.63 | 1.88 |
| bulk_wave | True | Forecast + 50% | 30 | 4.50 | 3.96 | 5.11 | 4.80 | 3.63 | 1.86 |
| bulk_wave | True | Open-loop QoE | 30 | 2.97 | 2.62 | 3.34 | 4.61 | 3.11 | 3.84 |
| bulk_wave | True | Open-loop QoE + SLA (1) | 30 | 2.78 | 2.53 | 3.03 | 4.60 | 3.16 | 3.84 |
| bulk_wave | True | DRL, replay-trained | 30 | 1.31 | 1.14 | 1.49 | 4.51 | 4.20 | 3.06 |
| bulk_wave | True | DRL, replay-trained, SLA (1) | 30 | 1.78 | 1.61 | 1.95 | 4.47 | 4.22 | 3.07 |
| bulk_wave | True | DRL, loop-trained | 30 | -0.28 | -0.38 | -0.18 | 4.68 | 3.96 | 3.17 |
| bulk_wave | True | DRL, loop-trained, SLA (1) | 30 | -0.14 | -0.22 | -0.06 | 4.63 | 4.05 | 3.19 |
| bulk_wave | True | EchoSlice-lite | 30 | 0.91 | 0.72 | 1.12 | 4.65 | 3.92 | 3.02 |
| bulk_wave | True | EchoSlice (v2) | 30 | 1.49 | 1.18 | 1.84 | 4.63 | 3.78 | 3.14 |
| bulk_wave | True | EchoSlice (v3) | 30 | 2.13 | 1.77 | 2.50 | 4.71 | 3.99 | 2.36 |
| bulk_wave | True | EchoSlice (v3), SLA (1) | 30 | 2.56 | 2.08 | 3.05 | 4.55 | 4.00 | 2.86 |
| bulk_wave | True | Static equal | 30 | 0.51 | 0.41 | 0.61 | 4.55 | 3.95 | 3.48 |
| bulk_wave | True | Static tuned at deploy | 30 | 1.17 | 1.02 | 1.31 | 4.72 | 4.07 | 2.44 |
| churn | False | Usage-proportional | 30 | 9.11 | 8.67 | 9.59 | 4.66 | 2.28 | 4.17 |
| churn | False | Forecast + 10% | 30 | 6.71 | 6.15 | 7.20 | 4.73 | 2.61 | 4.08 |
| churn | False | Forecast + 20% | 30 | 1.08 | 0.83 | 1.36 | 4.77 | 3.95 | 3.52 |
| churn | False | Forecast + 30% | 30 | 1.17 | 1.01 | 1.35 | 4.78 | 4.20 | 3.07 |
| churn | False | Forecast + 50% | 30 | 1.64 | 1.44 | 1.83 | 4.78 | 4.27 | 2.84 |
| churn | False | Open-loop QoE | 30 | 4.61 | 4.26 | 4.95 | 4.61 | 3.22 | 4.24 |
| churn | False | Open-loop QoE + SLA (1) | 30 | 4.48 | 4.16 | 4.82 | 4.61 | 3.25 | 4.23 |
| churn | False | DRL, replay-trained | 30 | 0.37 | 0.24 | 0.50 | 4.68 | 4.40 | 3.42 |
| churn | False | DRL, replay-trained, SLA (1) | 30 | 0.47 | 0.34 | 0.60 | 4.67 | 4.42 | 3.40 |
| churn | False | DRL, loop-trained | 30 | 0.30 | 0.19 | 0.40 | 4.74 | 4.34 | 3.30 |
| churn | False | DRL, loop-trained, SLA (1) | 30 | 0.35 | 0.23 | 0.45 | 4.73 | 4.36 | 3.30 |
| churn | False | EchoSlice-lite | 30 | 0.45 | 0.30 | 0.61 | 4.70 | 4.24 | 3.56 |
| churn | False | EchoSlice (v2) | 30 | 1.17 | 0.92 | 1.44 | 4.63 | 4.29 | 3.54 |
| churn | False | EchoSlice (v3) | 30 | 0.79 | 0.58 | 0.99 | 4.72 | 4.26 | 3.34 |
| churn | False | EchoSlice (v3), SLA (1) | 30 | 1.23 | 1.06 | 1.41 | 4.68 | 4.35 | 3.27 |
| churn | False | Static equal | 30 | 0.07 | -0.02 | 0.16 | 4.69 | 4.22 | 3.74 |
| churn | False | No slicing (PF) | 30 | 0.56 | 0.45 | 0.67 | 4.77 | 4.00 | 3.59 |
| churn | False | Static tuned at deploy | 30 | 0.98 | 0.81 | 1.15 | 4.55 | 4.30 | 3.90 |
| churn | True | Usage-proportional | 30 | 23.27 | 21.23 | 25.16 | 3.52 | 2.28 | 4.48 |
| churn | True | Forecast + 10% | 30 | 6.18 | 5.66 | 6.69 | 4.72 | 2.61 | 4.09 |
| churn | True | Forecast + 20% | 30 | 0.76 | 0.50 | 1.03 | 4.76 | 3.92 | 3.52 |
| churn | True | Forecast + 30% | 30 | 1.19 | 0.94 | 1.43 | 4.78 | 4.22 | 2.89 |
| churn | True | Forecast + 50% | 30 | 2.74 | 2.51 | 2.94 | 4.78 | 4.27 | 2.36 |
| churn | True | Open-loop QoE | 30 | 4.26 | 3.88 | 4.63 | 4.58 | 3.24 | 4.25 |
| churn | True | Open-loop QoE + SLA (1) | 30 | 4.17 | 3.83 | 4.49 | 4.58 | 3.27 | 4.25 |
| churn | True | DRL, replay-trained | 30 | 0.81 | 0.65 | 0.97 | 4.62 | 4.37 | 3.41 |
| churn | True | DRL, replay-trained, SLA (1) | 30 | 1.14 | 1.00 | 1.30 | 4.60 | 4.38 | 3.39 |
| churn | True | DRL, loop-trained | 30 | 0.68 | 0.58 | 0.77 | 4.76 | 4.09 | 3.28 |
| churn | True | DRL, loop-trained, SLA (1) | 30 | 0.44 | 0.33 | 0.56 | 4.75 | 4.19 | 3.25 |
| churn | True | EchoSlice-lite | 30 | 0.96 | 0.70 | 1.23 | 4.66 | 4.10 | 3.61 |
| churn | True | EchoSlice (v2) | 30 | 1.83 | 1.40 | 2.37 | 4.66 | 3.98 | 3.54 |
| churn | True | EchoSlice (v3) | 30 | 1.60 | 1.14 | 2.16 | 4.66 | 4.03 | 3.50 |
| churn | True | EchoSlice (v3), SLA (1) | 30 | 2.18 | 1.72 | 2.71 | 4.59 | 4.13 | 3.47 |
| churn | True | Static equal | 30 | 0.05 | -0.07 | 0.18 | 4.66 | 4.23 | 3.68 |
| churn | True | Static tuned at deploy | 30 | 0.27 | 0.14 | 0.41 | 4.62 | 4.18 | 3.84 |
| game_surge | False | Usage-proportional | 30 | 10.65 | 10.07 | 11.22 | 4.80 | 2.04 | 2.79 |
| game_surge | False | Forecast + 10% | 30 | 6.70 | 5.99 | 7.39 | 4.77 | 2.55 | 3.23 |
| game_surge | False | Forecast + 20% | 30 | 3.76 | 3.15 | 4.41 | 4.81 | 3.55 | 2.41 |
| game_surge | False | Forecast + 30% | 30 | 4.73 | 4.13 | 5.41 | 4.82 | 3.67 | 1.94 |
| game_surge | False | Forecast + 50% | 30 | 5.03 | 4.47 | 5.65 | 4.82 | 3.68 | 1.83 |
| game_surge | False | Open-loop QoE | 30 | 5.39 | 4.92 | 5.85 | 4.59 | 2.95 | 3.75 |
| game_surge | False | Open-loop QoE + SLA (1) | 30 | 5.05 | 4.70 | 5.38 | 4.59 | 3.02 | 3.74 |
| game_surge | False | DRL, replay-trained | 30 | 0.25 | 0.10 | 0.42 | 4.61 | 4.30 | 3.07 |
| game_surge | False | DRL, replay-trained, SLA (1) | 30 | 0.50 | 0.34 | 0.65 | 4.59 | 4.32 | 3.07 |
| game_surge | False | DRL, loop-trained | 30 | 0.00 | -0.07 | 0.08 | 4.69 | 4.22 | 2.96 |
| game_surge | False | DRL, loop-trained, SLA (1) | 30 | 0.08 | -0.01 | 0.17 | 4.67 | 4.24 | 2.99 |
| game_surge | False | EchoSlice-lite | 30 | 0.73 | 0.49 | 1.00 | 4.65 | 4.03 | 3.17 |
| game_surge | False | EchoSlice (v2) | 30 | 0.85 | 0.56 | 1.18 | 4.65 | 4.12 | 3.03 |
| game_surge | False | EchoSlice (v3) | 30 | 0.81 | 0.52 | 1.11 | 4.72 | 4.01 | 2.90 |
| game_surge | False | EchoSlice (v3), SLA (1) | 30 | 1.24 | 0.98 | 1.49 | 4.59 | 4.18 | 3.05 |
| game_surge | False | Static equal | 30 | 0.27 | 0.16 | 0.37 | 4.63 | 4.07 | 3.34 |
| game_surge | False | No slicing (PF) | 30 | 2.16 | 1.92 | 2.38 | 4.79 | 3.52 | 3.00 |
| game_surge | False | Static tuned at deploy | 30 | 1.24 | 1.06 | 1.41 | 4.74 | 3.68 | 3.22 |
| game_surge | True | Usage-proportional | 30 | 17.36 | 14.26 | 20.54 | 4.24 | 2.03 | 2.90 |
| game_surge | True | Forecast + 10% | 30 | 5.85 | 5.23 | 6.48 | 4.77 | 2.52 | 3.25 |
| game_surge | True | Forecast + 20% | 30 | 2.80 | 2.11 | 3.49 | 4.81 | 3.56 | 2.39 |
| game_surge | True | Forecast + 30% | 30 | 3.94 | 3.38 | 4.58 | 4.81 | 3.69 | 1.85 |
| game_surge | True | Forecast + 50% | 30 | 4.59 | 4.08 | 5.14 | 4.82 | 3.68 | 1.67 |
| game_surge | True | Open-loop QoE | 30 | 4.71 | 4.33 | 5.10 | 4.55 | 2.96 | 3.77 |
| game_surge | True | Open-loop QoE + SLA (1) | 30 | 4.41 | 4.03 | 4.81 | 4.55 | 3.02 | 3.77 |
| game_surge | True | DRL, replay-trained | 30 | 0.60 | 0.41 | 0.81 | 4.52 | 4.26 | 3.09 |
| game_surge | True | DRL, replay-trained, SLA (1) | 30 | 0.85 | 0.63 | 1.07 | 4.50 | 4.27 | 3.09 |
| game_surge | True | DRL, loop-trained | 30 | -0.52 | -0.63 | -0.41 | 4.70 | 4.02 | 3.04 |
| game_surge | True | DRL, loop-trained, SLA (1) | 30 | -0.62 | -0.73 | -0.51 | 4.67 | 4.09 | 3.10 |
| game_surge | True | EchoSlice-lite | 30 | 1.26 | 0.97 | 1.56 | 4.66 | 3.71 | 3.17 |
| game_surge | True | EchoSlice (v2) | 30 | 0.85 | 0.42 | 1.33 | 4.64 | 3.88 | 3.10 |
| game_surge | True | EchoSlice (v3) | 30 | 0.38 | 0.11 | 0.66 | 4.69 | 3.91 | 2.98 |
| game_surge | True | EchoSlice (v3), SLA (1) | 30 | 1.56 | 1.20 | 1.94 | 4.54 | 4.02 | 3.10 |
| game_surge | True | Static equal | 30 | 0.57 | 0.45 | 0.68 | 4.55 | 4.06 | 3.29 |
| game_surge | True | Static tuned at deploy | 30 | 3.56 | 3.28 | 3.85 | 4.72 | 2.95 | 3.44 |
| video_peak | False | Usage-proportional | 30 | 20.92 | 18.63 | 23.50 | 3.81 | 1.76 | 4.06 |
| video_peak | False | Forecast + 10% | 30 | 6.95 | 5.80 | 7.98 | 4.73 | 2.24 | 3.56 |
| video_peak | False | Forecast + 20% | 30 | 1.26 | 1.00 | 1.52 | 4.76 | 3.84 | 2.61 |
| video_peak | False | Forecast + 30% | 30 | 1.68 | 1.49 | 1.88 | 4.77 | 3.98 | 2.26 |
| video_peak | False | Forecast + 50% | 30 | 1.95 | 1.77 | 2.15 | 4.76 | 4.00 | 2.16 |
| video_peak | False | Open-loop QoE | 30 | 5.07 | 4.44 | 5.69 | 4.53 | 2.93 | 3.84 |
| video_peak | False | Open-loop QoE + SLA (1) | 30 | 4.70 | 4.12 | 5.32 | 4.53 | 2.99 | 3.83 |
| video_peak | False | DRL, replay-trained | 30 | 1.41 | 1.25 | 1.57 | 4.50 | 4.25 | 2.98 |
| video_peak | False | DRL, replay-trained, SLA (1) | 30 | 1.94 | 1.75 | 2.13 | 4.46 | 4.27 | 2.96 |
| video_peak | False | DRL, loop-trained | 30 | 0.34 | 0.26 | 0.42 | 4.61 | 4.13 | 3.01 |
| video_peak | False | DRL, loop-trained, SLA (1) | 30 | 0.57 | 0.45 | 0.69 | 4.59 | 4.15 | 3.02 |
| video_peak | False | EchoSlice-lite | 30 | 2.17 | 1.58 | 2.87 | 4.45 | 4.15 | 3.16 |
| video_peak | False | EchoSlice (v2) | 30 | 1.49 | 1.12 | 1.87 | 4.51 | 4.08 | 3.18 |
| video_peak | False | EchoSlice (v3) | 30 | 1.10 | 0.77 | 1.48 | 4.61 | 4.18 | 2.73 |
| video_peak | False | EchoSlice (v3), SLA (1) | 30 | 2.44 | 1.94 | 2.99 | 4.51 | 4.22 | 2.73 |
| video_peak | False | Static equal | 30 | 0.59 | 0.44 | 0.75 | 4.58 | 3.92 | 3.37 |
| video_peak | False | No slicing (PF) | 30 | 0.56 | 0.33 | 0.78 | 4.73 | 3.64 | 3.21 |
| video_peak | False | Static tuned at deploy | 30 | 2.74 | 2.50 | 2.97 | 4.36 | 4.04 | 3.50 |
| video_peak | True | Usage-proportional | 30 | 20.81 | 18.28 | 23.28 | 3.77 | 1.74 | 4.07 |
| video_peak | True | Forecast + 10% | 30 | 6.00 | 4.93 | 7.02 | 4.73 | 2.26 | 3.56 |
| video_peak | True | Forecast + 20% | 30 | 0.68 | 0.43 | 0.94 | 4.75 | 3.84 | 2.55 |
| video_peak | True | Forecast + 30% | 30 | 1.75 | 1.51 | 1.98 | 4.76 | 4.00 | 1.98 |
| video_peak | True | Forecast + 50% | 30 | 2.71 | 2.52 | 2.89 | 4.76 | 4.02 | 1.70 |
| video_peak | True | Open-loop QoE | 30 | 4.48 | 3.95 | 5.03 | 4.50 | 2.94 | 3.85 |
| video_peak | True | Open-loop QoE + SLA (1) | 30 | 4.23 | 3.73 | 4.76 | 4.50 | 3.00 | 3.85 |
| video_peak | True | DRL, replay-trained | 30 | 1.26 | 1.04 | 1.49 | 4.46 | 4.20 | 3.02 |
| video_peak | True | DRL, replay-trained, SLA (1) | 30 | 1.52 | 1.28 | 1.79 | 4.44 | 4.20 | 3.02 |
| video_peak | True | DRL, loop-trained | 30 | 0.01 | -0.09 | 0.13 | 4.65 | 3.90 | 3.05 |
| video_peak | True | DRL, loop-trained, SLA (1) | 30 | 0.18 | 0.07 | 0.29 | 4.59 | 4.00 | 3.07 |
| video_peak | True | EchoSlice-lite | 30 | 1.94 | 1.30 | 2.75 | 4.43 | 4.03 | 3.19 |
| video_peak | True | EchoSlice (v2) | 30 | 1.52 | 1.01 | 2.13 | 4.52 | 3.88 | 3.18 |
| video_peak | True | EchoSlice (v3) | 30 | 0.52 | 0.20 | 0.85 | 4.58 | 3.96 | 3.12 |
| video_peak | True | EchoSlice (v3), SLA (1) | 30 | 2.32 | 1.56 | 3.16 | 4.46 | 3.95 | 3.11 |
| video_peak | True | Static equal | 30 | 0.32 | 0.21 | 0.42 | 4.56 | 3.91 | 3.30 |
| video_peak | True | Static tuned at deploy | 30 | 3.49 | 3.24 | 3.75 | 4.25 | 4.05 | 3.46 |

![dynamic load](../figures/fig_dynload.png)


## E7. Unbalanced and shifting load

Gap (%) of window-averaged user MOS against the best single static split for the whole run (leave-one-seed-out). Headroom = how much a clairvoyant best split per 300 s window would gain over it; captured = share of that headroom a slicer actually gains (negative: it loses to the best static split; above 1 is possible because the per-window oracle only picks from the grid). SLA = share of (user, window) pairs meeting the slice target (video and gaming MOS >= 4, bulk MOS >= 3).

| cell | strict | slicer | gap_pct | gap_lo | gap_hi | headroom_pct | captured | sla | sla_video | sla_game | sla_bulk |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M1-video-heavy | False | Usage-proportional | 0.71 | 0.56 | 0.84 | 0.00 |  | 0.89 | 0.97 | 0.07 | 0.35 |
| M1-video-heavy | False | Forecast + 10% | 0.56 | 0.47 | 0.67 | 0.00 |  | 0.90 | 0.97 | 0.12 | 0.57 |
| M1-video-heavy | False | Forecast + 20% | 0.60 | 0.48 | 0.74 | 0.00 |  | 0.89 | 0.96 | 0.12 | 0.35 |
| M1-video-heavy | False | Forecast + 30% | 0.60 | 0.48 | 0.72 | 0.00 |  | 0.89 | 0.97 | 0.13 | 0.35 |
| M1-video-heavy | False | Forecast + 50% | 0.62 | 0.50 | 0.74 | 0.00 |  | 0.89 | 0.97 | 0.12 | 0.35 |
| M1-video-heavy | False | Open-loop QoE | 1.10 | 0.93 | 1.27 | 0.00 |  | 0.89 | 0.94 | 0.12 | 0.97 |
| M1-video-heavy | False | Open-loop QoE + SLA (0.5) | 1.13 | 0.97 | 1.29 | 0.00 |  | 0.88 | 0.93 | 0.11 | 0.97 |
| M1-video-heavy | False | Open-loop QoE + SLA (1) | 1.10 | 0.95 | 1.25 | 0.00 |  | 0.88 | 0.94 | 0.12 | 0.97 |
| M1-video-heavy | False | Open-loop QoE + SLA (2) | 1.12 | 0.96 | 1.28 | 0.00 |  | 0.88 | 0.94 | 0.12 | 0.97 |
| M1-video-heavy | False | DRL, replay-trained | 1.58 | 1.35 | 1.80 | 0.00 |  | 0.90 | 0.89 | 0.96 | 0.92 |
| M1-video-heavy | False | DRL, replay-trained, SLA (1) | 1.99 | 1.80 | 2.19 | 0.00 |  | 0.89 | 0.88 | 0.97 | 0.95 |
| M1-video-heavy | False | DRL, loop-trained | 1.09 | 0.92 | 1.26 | 0.00 |  | 0.91 | 0.91 | 0.94 | 0.93 |
| M1-video-heavy | False | DRL, loop-trained, SLA (1) | 1.27 | 1.10 | 1.44 | 0.00 |  | 0.91 | 0.90 | 0.97 | 0.90 |
| M1-video-heavy | False | EchoSlice-lite | 2.76 | 2.02 | 3.66 | 0.00 |  | 0.87 | 0.86 | 0.95 | 1.00 |
| M1-video-heavy | False | EchoSlice (v2) | 2.76 | 2.05 | 3.63 | 0.00 |  | 0.87 | 0.86 | 0.95 | 1.00 |
| M1-video-heavy | False | EchoSlice (v3) | -0.05 | -0.15 | 0.05 | 0.00 |  | 0.92 | 0.96 | 0.55 | 0.62 |
| M1-video-heavy | False | EchoSlice (v3), SLA (0.5) | 0.56 | 0.27 | 0.86 | 0.00 |  | 0.92 | 0.93 | 0.77 | 0.75 |
| M1-video-heavy | False | EchoSlice (v3), SLA (1) | 1.06 | 0.59 | 1.61 | 0.00 |  | 0.91 | 0.92 | 0.81 | 0.80 |
| M1-video-heavy | False | EchoSlice (v3), SLA (2) | 1.64 | 1.03 | 2.38 | 0.00 |  | 0.90 | 0.91 | 0.78 | 0.87 |
| M1-video-heavy | False | Static equal | 4.70 | 4.42 | 4.99 | 0.00 |  | 0.82 | 0.80 | 0.94 | 1.00 |
| M1-video-heavy | False | No slicing (PF) | 0.50 | 0.37 | 0.64 | 0.00 |  | 0.89 | 0.97 | 0.16 | 0.22 |
| M1-video-heavy | True | Usage-proportional | 5.41 | 1.25 | 10.71 | 0.00 |  | 0.79 | 0.85 | 0.07 | 0.50 |
| M1-video-heavy | True | Forecast + 10% | 0.54 | 0.45 | 0.64 | 0.00 |  | 0.90 | 0.97 | 0.09 | 0.60 |
| M1-video-heavy | True | Forecast + 20% | 0.57 | 0.47 | 0.68 | 0.00 |  | 0.89 | 0.97 | 0.13 | 0.37 |
| M1-video-heavy | True | Forecast + 30% | 0.58 | 0.49 | 0.66 | 0.00 |  | 0.89 | 0.97 | 0.12 | 0.33 |
| M1-video-heavy | True | Forecast + 50% | 0.59 | 0.50 | 0.69 | 0.00 |  | 0.89 | 0.97 | 0.13 | 0.35 |
| M1-video-heavy | True | Open-loop QoE | 1.36 | 1.22 | 1.50 | 0.00 |  | 0.87 | 0.93 | 0.09 | 0.97 |
| M1-video-heavy | True | Open-loop QoE + SLA (0.5) | 1.44 | 1.30 | 1.57 | 0.00 |  | 0.87 | 0.92 | 0.12 | 0.97 |
| M1-video-heavy | True | Open-loop QoE + SLA (1) | 1.42 | 1.28 | 1.55 | 0.00 |  | 0.88 | 0.93 | 0.12 | 0.97 |
| M1-video-heavy | True | Open-loop QoE + SLA (2) | 1.45 | 1.31 | 1.60 | 0.00 |  | 0.87 | 0.92 | 0.12 | 0.98 |
| M1-video-heavy | True | DRL, replay-trained | 3.14 | 2.86 | 3.41 | 0.00 |  | 0.86 | 0.85 | 0.95 | 0.93 |
| M1-video-heavy | True | DRL, replay-trained, SLA (1) | 3.49 | 3.22 | 3.75 | 0.00 |  | 0.85 | 0.84 | 0.95 | 0.95 |
| M1-video-heavy | True | DRL, loop-trained | 1.38 | 1.18 | 1.57 | 0.00 |  | 0.90 | 0.90 | 0.88 | 0.92 |
| M1-video-heavy | True | DRL, loop-trained, SLA (1) | 1.37 | 1.17 | 1.56 | 0.00 |  | 0.90 | 0.90 | 0.90 | 0.88 |
| M1-video-heavy | True | EchoSlice-lite | 4.63 | 3.79 | 5.47 | 0.00 |  | 0.81 | 0.80 | 0.81 | 0.93 |
| M1-video-heavy | True | EchoSlice (v2) | 4.63 | 3.78 | 5.47 | 0.00 |  | 0.81 | 0.80 | 0.81 | 0.93 |
| M1-video-heavy | True | EchoSlice (v3) | 0.49 | 0.15 | 1.09 | 0.00 |  | 0.90 | 0.95 | 0.43 | 0.60 |
| M1-video-heavy | True | EchoSlice (v3), SLA (0.5) | 1.34 | 0.90 | 1.84 | 0.00 |  | 0.89 | 0.92 | 0.68 | 0.72 |
| M1-video-heavy | True | EchoSlice (v3), SLA (1) | 2.06 | 1.53 | 2.67 | 0.00 |  | 0.88 | 0.90 | 0.72 | 0.80 |
| M1-video-heavy | True | EchoSlice (v3), SLA (2) | 3.79 | 2.51 | 5.15 | 0.00 |  | 0.83 | 0.84 | 0.68 | 0.82 |
| M1-video-heavy | True | Static equal | 9.48 | 9.09 | 9.87 | 0.00 |  | 0.70 | 0.67 | 0.94 | 1.00 |
| M2-gaming-heavy | False | Usage-proportional | 28.31 | 26.02 | 30.69 | 0.00 |  | 0.39 | 0.93 | 0.01 | 1.00 |
| M2-gaming-heavy | False | Forecast + 10% | 16.50 | 13.25 | 19.75 | 0.00 |  | 0.49 | 0.99 | 0.15 | 1.00 |
| M2-gaming-heavy | False | Forecast + 20% | 0.43 | 0.28 | 0.57 | 0.00 |  | 0.84 | 0.99 | 0.76 | 0.75 |
| M2-gaming-heavy | False | Forecast + 30% | 0.57 | 0.40 | 0.74 | 0.00 |  | 0.83 | 0.99 | 0.75 | 0.68 |
| M2-gaming-heavy | False | Forecast + 50% | 0.51 | 0.33 | 0.69 | 0.00 |  | 0.83 | 0.99 | 0.75 | 0.65 |
| M2-gaming-heavy | False | Open-loop QoE | 6.37 | 5.56 | 7.31 | 0.00 |  | 0.64 | 0.97 | 0.41 | 1.00 |
| M2-gaming-heavy | False | Open-loop QoE + SLA (0.5) | 6.38 | 5.53 | 7.29 | 0.00 |  | 0.64 | 0.97 | 0.42 | 1.00 |
| M2-gaming-heavy | False | Open-loop QoE + SLA (1) | 6.34 | 5.51 | 7.19 | 0.00 |  | 0.64 | 0.96 | 0.42 | 1.00 |
| M2-gaming-heavy | False | Open-loop QoE + SLA (2) | 6.55 | 5.72 | 7.44 | 0.00 |  | 0.64 | 0.96 | 0.41 | 1.00 |
| M2-gaming-heavy | False | DRL, replay-trained | 0.58 | 0.44 | 0.73 | 0.00 |  | 0.82 | 0.99 | 0.71 | 0.93 |
| M2-gaming-heavy | False | DRL, replay-trained, SLA (1) | 0.34 | 0.21 | 0.48 | 0.00 |  | 0.83 | 0.98 | 0.74 | 0.93 |
| M2-gaming-heavy | False | DRL, loop-trained | 1.79 | 1.57 | 2.01 | 0.00 |  | 0.78 | 1.00 | 0.62 | 0.97 |
| M2-gaming-heavy | False | DRL, loop-trained, SLA (1) | 1.63 | 1.43 | 1.84 | 0.00 |  | 0.78 | 1.00 | 0.63 | 0.97 |
| M2-gaming-heavy | False | EchoSlice-lite | 1.76 | 1.38 | 2.12 | 0.00 |  | 0.78 | 0.98 | 0.64 | 0.93 |
| M2-gaming-heavy | False | EchoSlice (v2) | 1.76 | 1.37 | 2.12 | 0.00 |  | 0.78 | 0.98 | 0.64 | 0.93 |
| M2-gaming-heavy | False | EchoSlice (v3) | 0.34 | 0.15 | 0.58 | 0.00 |  | 0.86 | 0.97 | 0.80 | 0.75 |
| M2-gaming-heavy | False | EchoSlice (v3), SLA (0.5) | 0.57 | 0.33 | 0.82 | 0.00 |  | 0.85 | 0.97 | 0.78 | 0.83 |
| M2-gaming-heavy | False | EchoSlice (v3), SLA (1) | 0.64 | 0.39 | 0.93 | 0.00 |  | 0.84 | 0.98 | 0.76 | 0.88 |
| M2-gaming-heavy | False | EchoSlice (v3), SLA (2) | 0.98 | 0.48 | 1.66 | 0.00 |  | 0.84 | 0.97 | 0.77 | 0.75 |
| M2-gaming-heavy | False | Static equal | 5.94 | 5.56 | 6.36 | 0.00 |  | 0.64 | 1.00 | 0.39 | 0.98 |
| M2-gaming-heavy | False | No slicing (PF) | 1.14 | 0.92 | 1.40 | 0.00 |  | 0.81 | 1.00 | 0.69 | 0.92 |
| M2-gaming-heavy | True | Usage-proportional | 28.80 | 26.35 | 31.04 | 0.00 |  | 0.39 | 0.95 | 0.00 | 1.00 |
| M2-gaming-heavy | True | Forecast + 10% | 16.68 | 13.54 | 19.69 | 0.00 |  | 0.48 | 0.98 | 0.13 | 1.00 |
| M2-gaming-heavy | True | Forecast + 20% | 0.41 | 0.23 | 0.61 | 0.00 |  | 0.83 | 0.99 | 0.75 | 0.62 |
| M2-gaming-heavy | True | Forecast + 30% | 0.62 | 0.42 | 0.81 | 0.00 |  | 0.81 | 0.98 | 0.75 | 0.37 |
| M2-gaming-heavy | True | Forecast + 50% | 0.59 | 0.40 | 0.78 | 0.00 |  | 0.81 | 0.98 | 0.75 | 0.33 |
| M2-gaming-heavy | True | Open-loop QoE | 5.65 | 4.78 | 6.63 | 0.00 |  | 0.65 | 0.97 | 0.43 | 0.98 |
| M2-gaming-heavy | True | Open-loop QoE + SLA (0.5) | 5.76 | 4.90 | 6.74 | 0.00 |  | 0.65 | 0.97 | 0.42 | 0.98 |
| M2-gaming-heavy | True | Open-loop QoE + SLA (1) | 5.78 | 4.90 | 6.73 | 0.00 |  | 0.65 | 0.97 | 0.42 | 0.98 |
| M2-gaming-heavy | True | Open-loop QoE + SLA (2) | 5.91 | 5.04 | 6.89 | 0.00 |  | 0.64 | 0.97 | 0.41 | 0.98 |
| M2-gaming-heavy | True | DRL, replay-trained | 1.02 | 0.82 | 1.23 | 0.00 |  | 0.79 | 0.99 | 0.66 | 0.95 |
| M2-gaming-heavy | True | DRL, replay-trained, SLA (1) | 0.93 | 0.71 | 1.15 | 0.00 |  | 0.79 | 0.98 | 0.66 | 0.95 |
| M2-gaming-heavy | True | DRL, loop-trained | 2.38 | 2.06 | 2.73 | 0.00 |  | 0.75 | 1.00 | 0.59 | 0.93 |
| M2-gaming-heavy | True | DRL, loop-trained, SLA (1) | 2.39 | 2.05 | 2.76 | 0.00 |  | 0.75 | 1.00 | 0.59 | 0.93 |
| M2-gaming-heavy | True | EchoSlice-lite | 2.37 | 1.83 | 2.95 | 0.00 |  | 0.76 | 0.98 | 0.61 | 0.95 |
| M2-gaming-heavy | True | EchoSlice (v2) | 2.37 | 1.84 | 2.94 | 0.00 |  | 0.76 | 0.97 | 0.61 | 0.95 |
| M2-gaming-heavy | True | EchoSlice (v3) | 0.87 | 0.48 | 1.42 | 0.00 |  | 0.82 | 0.94 | 0.77 | 0.60 |
| M2-gaming-heavy | True | EchoSlice (v3), SLA (0.5) | 1.37 | 1.04 | 1.74 | 0.00 |  | 0.80 | 0.93 | 0.72 | 0.77 |
| M2-gaming-heavy | True | EchoSlice (v3), SLA (1) | 2.22 | 1.53 | 3.03 | 0.00 |  | 0.78 | 0.89 | 0.72 | 0.82 |
| M2-gaming-heavy | True | EchoSlice (v3), SLA (2) | 2.79 | 1.99 | 3.70 | 0.00 |  | 0.77 | 0.88 | 0.70 | 0.77 |
| M2-gaming-heavy | True | Static equal | 5.90 | 5.51 | 6.33 | 0.00 |  | 0.64 | 1.00 | 0.39 | 0.98 |
| M3-bulk-heavy | False | Usage-proportional | 5.43 | 5.06 | 5.86 | 0.00 |  | 0.72 | 0.67 | 0.10 | 0.90 |
| M3-bulk-heavy | False | Forecast + 10% | 2.18 | 1.85 | 2.55 | 0.00 |  | 0.80 | 0.97 | 0.18 | 0.86 |
| M3-bulk-heavy | False | Forecast + 20% | 1.40 | 1.03 | 1.77 | 0.00 |  | 0.82 | 0.99 | 0.38 | 0.84 |
| M3-bulk-heavy | False | Forecast + 30% | 0.93 | 0.69 | 1.19 | 0.00 |  | 0.84 | 1.00 | 0.70 | 0.79 |
| M3-bulk-heavy | False | Forecast + 50% | 1.62 | 1.32 | 1.90 | 0.00 |  | 0.83 | 1.00 | 0.93 | 0.71 |
| M3-bulk-heavy | False | Open-loop QoE | 2.90 | 2.59 | 3.24 | 0.00 |  | 0.78 | 0.89 | 0.11 | 0.89 |
| M3-bulk-heavy | False | Open-loop QoE + SLA (0.5) | 2.84 | 2.52 | 3.17 | 0.00 |  | 0.78 | 0.89 | 0.13 | 0.88 |
| M3-bulk-heavy | False | Open-loop QoE + SLA (1) | 2.74 | 2.45 | 3.02 | 0.00 |  | 0.77 | 0.88 | 0.12 | 0.88 |
| M3-bulk-heavy | False | Open-loop QoE + SLA (2) | 2.71 | 2.37 | 3.05 | 0.00 |  | 0.78 | 0.88 | 0.12 | 0.89 |
| M3-bulk-heavy | False | DRL, replay-trained | 2.20 | 1.97 | 2.40 | 0.00 |  | 0.81 | 1.00 | 0.97 | 0.67 |
| M3-bulk-heavy | False | DRL, replay-trained, SLA (1) | 2.11 | 1.91 | 2.31 | 0.00 |  | 0.81 | 1.00 | 0.97 | 0.67 |
| M3-bulk-heavy | False | DRL, loop-trained | 2.55 | 2.32 | 2.78 | 0.00 |  | 0.79 | 1.00 | 0.95 | 0.64 |
| M3-bulk-heavy | False | DRL, loop-trained, SLA (1) | 2.54 | 2.32 | 2.75 | 0.00 |  | 0.79 | 1.00 | 0.95 | 0.64 |
| M3-bulk-heavy | False | EchoSlice-lite | 1.98 | 1.67 | 2.34 | 0.00 |  | 0.82 | 1.00 | 0.94 | 0.69 |
| M3-bulk-heavy | False | EchoSlice (v2) | 1.98 | 1.66 | 2.32 | 0.00 |  | 0.82 | 1.00 | 0.94 | 0.69 |
| M3-bulk-heavy | False | EchoSlice (v3) | 0.34 | 0.08 | 0.59 | 0.00 |  | 0.84 | 0.97 | 0.71 | 0.81 |
| M3-bulk-heavy | False | EchoSlice (v3), SLA (0.5) | 0.88 | 0.62 | 1.15 | 0.00 |  | 0.83 | 0.97 | 0.83 | 0.77 |
| M3-bulk-heavy | False | EchoSlice (v3), SLA (1) | 1.41 | 1.03 | 1.81 | 0.00 |  | 0.82 | 0.98 | 0.86 | 0.74 |
| M3-bulk-heavy | False | EchoSlice (v3), SLA (2) | 1.25 | 0.86 | 1.67 | 0.00 |  | 0.84 | 0.98 | 0.82 | 0.77 |
| M3-bulk-heavy | False | Static equal | 2.32 | 2.12 | 2.52 | 0.00 |  | 0.80 | 1.00 | 0.95 | 0.66 |
| M3-bulk-heavy | False | No slicing (PF) | 0.64 | 0.43 | 0.87 | 0.00 |  | 0.84 | 1.00 | 0.53 | 0.83 |
| M3-bulk-heavy | True | Usage-proportional | 4.85 | 4.53 | 5.21 | 0.00 |  | 0.71 | 0.63 | 0.12 | 0.89 |
| M3-bulk-heavy | True | Forecast + 10% | 1.34 | 1.09 | 1.61 | 0.00 |  | 0.79 | 0.95 | 0.17 | 0.87 |
| M3-bulk-heavy | True | Forecast + 20% | 0.73 | 0.47 | 1.03 | 0.00 |  | 0.81 | 0.98 | 0.38 | 0.83 |
| M3-bulk-heavy | True | Forecast + 30% | 0.67 | 0.31 | 1.03 | 0.00 |  | 0.82 | 1.00 | 0.70 | 0.75 |
| M3-bulk-heavy | True | Forecast + 50% | 2.85 | 2.38 | 3.29 | 0.00 |  | 0.75 | 1.00 | 0.89 | 0.59 |
| M3-bulk-heavy | True | Open-loop QoE | 2.25 | 1.94 | 2.58 | 0.00 |  | 0.77 | 0.85 | 0.14 | 0.89 |
| M3-bulk-heavy | True | Open-loop QoE + SLA (0.5) | 2.13 | 1.87 | 2.43 | 0.00 |  | 0.77 | 0.87 | 0.12 | 0.89 |
| M3-bulk-heavy | True | Open-loop QoE + SLA (1) | 2.10 | 1.85 | 2.40 | 0.00 |  | 0.77 | 0.87 | 0.12 | 0.89 |
| M3-bulk-heavy | True | Open-loop QoE + SLA (2) | 2.14 | 1.86 | 2.45 | 0.00 |  | 0.77 | 0.85 | 0.13 | 0.89 |
| M3-bulk-heavy | True | DRL, replay-trained | 3.93 | 3.58 | 4.27 | 0.00 |  | 0.71 | 1.00 | 0.95 | 0.51 |
| M3-bulk-heavy | True | DRL, replay-trained, SLA (1) | 3.98 | 3.65 | 4.31 | 0.00 |  | 0.71 | 1.00 | 0.95 | 0.50 |
| M3-bulk-heavy | True | DRL, loop-trained | 6.67 | 6.23 | 7.11 | 0.00 |  | 0.60 | 1.00 | 0.84 | 0.33 |
| M3-bulk-heavy | True | DRL, loop-trained, SLA (1) | 5.48 | 5.11 | 5.87 | 0.00 |  | 0.65 | 1.00 | 0.86 | 0.42 |
| M3-bulk-heavy | True | EchoSlice-lite | 2.21 | 1.84 | 2.59 | 0.00 |  | 0.79 | 1.00 | 0.82 | 0.67 |
| M3-bulk-heavy | True | EchoSlice (v2) | 2.21 | 1.83 | 2.60 | 0.00 |  | 0.79 | 1.00 | 0.82 | 0.67 |
| M3-bulk-heavy | True | EchoSlice (v3) | 0.09 | -0.17 | 0.35 | 0.00 |  | 0.82 | 0.94 | 0.57 | 0.82 |
| M3-bulk-heavy | True | EchoSlice (v3), SLA (0.5) | 1.20 | 0.75 | 1.67 | 0.00 |  | 0.80 | 0.94 | 0.70 | 0.76 |
| M3-bulk-heavy | True | EchoSlice (v3), SLA (1) | 2.13 | 1.74 | 2.56 | 0.00 |  | 0.77 | 0.93 | 0.74 | 0.69 |
| M3-bulk-heavy | True | EchoSlice (v3), SLA (2) | 2.37 | 1.90 | 2.84 | 0.00 |  | 0.79 | 0.92 | 0.78 | 0.72 |
| M3-bulk-heavy | True | Static equal | 7.30 | 6.85 | 7.73 | 0.00 |  | 0.57 | 1.00 | 0.95 | 0.26 |
| day_cycle | False | Usage-proportional | 9.57 | 8.96 | 10.21 | 1.71 | -5.60 | 0.72 | 0.94 | 0.03 | 0.87 |
| day_cycle | False | Forecast + 10% | 6.52 | 5.74 | 7.31 | 1.71 | -3.80 | 0.75 | 0.97 | 0.09 | 0.87 |
| day_cycle | False | Forecast + 20% | -0.60 | -0.78 | -0.44 | 1.71 | 0.35 | 0.86 | 0.97 | 0.59 | 0.81 |
| day_cycle | False | Forecast + 30% | -0.97 | -1.15 | -0.80 | 1.71 | 0.57 | 0.87 | 0.97 | 0.66 | 0.76 |
| day_cycle | False | Forecast + 50% | -0.77 | -0.96 | -0.59 | 1.71 | 0.45 | 0.86 | 0.97 | 0.68 | 0.69 |
| day_cycle | False | Open-loop QoE | 2.38 | 2.03 | 2.72 | 1.71 | -1.39 | 0.78 | 0.94 | 0.25 | 0.92 |
| day_cycle | False | Open-loop QoE + SLA (0.5) | 2.33 | 1.97 | 2.69 | 1.71 | -1.36 | 0.78 | 0.93 | 0.25 | 0.92 |
| day_cycle | False | Open-loop QoE + SLA (1) | 2.32 | 1.97 | 2.67 | 1.71 | -1.35 | 0.78 | 0.93 | 0.25 | 0.92 |
| day_cycle | False | Open-loop QoE + SLA (2) | 2.34 | 1.99 | 2.70 | 1.71 | -1.36 | 0.78 | 0.94 | 0.24 | 0.92 |
| day_cycle | False | DRL, replay-trained | -0.29 | -0.49 | -0.10 | 1.71 | 0.17 | 0.86 | 0.92 | 0.79 | 0.73 |
| day_cycle | False | DRL, replay-trained, SLA (1) | -0.28 | -0.49 | -0.11 | 1.71 | 0.16 | 0.86 | 0.91 | 0.81 | 0.72 |
| day_cycle | False | DRL, loop-trained | -0.01 | -0.24 | 0.21 | 1.71 | 0.00 | 0.84 | 0.93 | 0.71 | 0.72 |
| day_cycle | False | DRL, loop-trained, SLA (1) | -0.03 | -0.25 | 0.20 | 1.71 | 0.01 | 0.84 | 0.92 | 0.72 | 0.71 |
| day_cycle | False | EchoSlice-lite | 0.82 | 0.54 | 1.11 | 1.71 | -0.48 | 0.81 | 0.90 | 0.69 | 0.67 |
| day_cycle | False | EchoSlice (v2) | -0.32 | -0.59 | -0.06 | 1.71 | 0.18 | 0.86 | 0.89 | 0.82 | 0.83 |
| day_cycle | False | EchoSlice (v3) | -1.24 | -1.47 | -1.02 | 1.71 | 0.72 | 0.88 | 0.96 | 0.75 | 0.79 |
| day_cycle | False | EchoSlice (v3), SLA (0.5) | -0.92 | -1.14 | -0.68 | 1.71 | 0.53 | 0.89 | 0.94 | 0.82 | 0.76 |
| day_cycle | False | EchoSlice (v3), SLA (1) | -0.72 | -1.00 | -0.46 | 1.71 | 0.42 | 0.88 | 0.93 | 0.84 | 0.76 |
| day_cycle | False | EchoSlice (v3), SLA (2) | -0.47 | -0.71 | -0.22 | 1.71 | 0.27 | 0.88 | 0.93 | 0.82 | 0.74 |
| day_cycle | False | Static equal | 2.65 | 2.42 | 2.88 | 1.71 | -1.55 | 0.76 | 0.85 | 0.53 | 0.74 |
| day_cycle | False | No slicing (PF) | -0.94 | -1.09 | -0.79 | 1.71 | 0.55 | 0.86 | 0.97 | 0.60 | 0.79 |
| day_cycle | False | Static tuned at deploy | 2.47 | 2.19 | 2.73 | 1.71 | -1.44 | 0.78 | 0.96 | 0.30 | 0.78 |
| day_cycle | True | Usage-proportional | 4.12 | 2.56 | 6.32 | 8.05 | -0.51 | 0.70 | 0.91 | 0.02 | 0.87 |
| day_cycle | True | Forecast + 10% | 0.36 | -0.37 | 1.11 | 8.05 | -0.04 | 0.75 | 0.96 | 0.09 | 0.87 |
| day_cycle | True | Forecast + 20% | -7.07 | -7.34 | -6.79 | 8.05 | 0.88 | 0.85 | 0.97 | 0.59 | 0.79 |
| day_cycle | True | Forecast + 30% | -7.23 | -7.48 | -7.00 | 8.05 | 0.90 | 0.85 | 0.97 | 0.65 | 0.69 |
| day_cycle | True | Forecast + 50% | -6.52 | -6.73 | -6.31 | 8.05 | 0.81 | 0.84 | 0.97 | 0.69 | 0.53 |
| day_cycle | True | Open-loop QoE | -3.89 | -4.29 | -3.47 | 8.05 | 0.48 | 0.77 | 0.93 | 0.24 | 0.92 |
| day_cycle | True | Open-loop QoE + SLA (0.5) | -3.94 | -4.34 | -3.53 | 8.05 | 0.49 | 0.77 | 0.92 | 0.25 | 0.92 |
| day_cycle | True | Open-loop QoE + SLA (1) | -4.00 | -4.40 | -3.58 | 8.05 | 0.50 | 0.77 | 0.92 | 0.25 | 0.92 |
| day_cycle | True | Open-loop QoE + SLA (2) | -3.93 | -4.31 | -3.53 | 8.05 | 0.49 | 0.77 | 0.92 | 0.25 | 0.92 |
| day_cycle | True | DRL, replay-trained | -5.26 | -5.39 | -5.13 | 8.05 | 0.65 | 0.81 | 0.89 | 0.74 | 0.57 |
| day_cycle | True | DRL, replay-trained, SLA (1) | -5.15 | -5.28 | -5.02 | 8.05 | 0.64 | 0.80 | 0.88 | 0.75 | 0.57 |
| day_cycle | True | DRL, loop-trained | -4.41 | -4.57 | -4.26 | 8.05 | 0.55 | 0.79 | 0.92 | 0.67 | 0.45 |
| day_cycle | True | DRL, loop-trained, SLA (1) | -4.86 | -5.02 | -4.70 | 8.05 | 0.60 | 0.80 | 0.93 | 0.68 | 0.50 |
| day_cycle | True | EchoSlice-lite | -1.75 | -2.23 | -1.24 | 8.05 | 0.22 | 0.72 | 0.86 | 0.56 | 0.43 |
| day_cycle | True | EchoSlice (v2) | -5.14 | -5.47 | -4.80 | 8.05 | 0.64 | 0.81 | 0.85 | 0.70 | 0.81 |
| day_cycle | True | EchoSlice (v3) | -7.22 | -7.47 | -6.95 | 8.05 | 0.90 | 0.86 | 0.95 | 0.69 | 0.74 |
| day_cycle | True | EchoSlice (v3), SLA (0.5) | -6.32 | -6.75 | -5.80 | 8.05 | 0.79 | 0.85 | 0.91 | 0.76 | 0.74 |
| day_cycle | True | EchoSlice (v3), SLA (1) | -5.53 | -6.07 | -4.94 | 8.05 | 0.69 | 0.83 | 0.89 | 0.79 | 0.66 |
| day_cycle | True | EchoSlice (v3), SLA (2) | -4.75 | -5.52 | -3.82 | 8.05 | 0.59 | 0.82 | 0.89 | 0.77 | 0.63 |
| day_cycle | True | Static equal | 0.23 | 0.15 | 0.29 | 8.05 | -0.03 | 0.65 | 0.76 | 0.53 | 0.41 |
| day_cycle | True | Static tuned at deploy | 10.80 | 10.59 | 11.02 | 8.05 | -1.34 | 0.65 | 0.96 | 0.14 | 0.19 |
| flash_crowd | False | Usage-proportional | 12.31 | 11.86 | 12.75 | 0.47 | -26.18 | 0.68 | 0.99 | 0.03 | 0.86 |
| flash_crowd | False | Forecast + 10% | 7.49 | 6.96 | 7.98 | 0.47 | -15.91 | 0.70 | 0.98 | 0.06 | 0.94 |
| flash_crowd | False | Forecast + 20% | 2.27 | 1.94 | 2.62 | 0.47 | -4.82 | 0.77 | 0.99 | 0.34 | 0.79 |
| flash_crowd | False | Forecast + 30% | 1.94 | 1.62 | 2.29 | 0.47 | -4.11 | 0.77 | 1.00 | 0.39 | 0.67 |
| flash_crowd | False | Forecast + 50% | 2.17 | 1.85 | 2.50 | 0.47 | -4.60 | 0.75 | 1.00 | 0.43 | 0.44 |
| flash_crowd | False | Open-loop QoE | 5.69 | 5.36 | 6.01 | 0.47 | -12.08 | 0.69 | 0.94 | 0.09 | 0.98 |
| flash_crowd | False | Open-loop QoE + SLA (0.5) | 5.56 | 5.22 | 5.91 | 0.47 | -11.82 | 0.69 | 0.94 | 0.09 | 0.97 |
| flash_crowd | False | Open-loop QoE + SLA (1) | 5.46 | 5.18 | 5.76 | 0.47 | -11.62 | 0.69 | 0.94 | 0.09 | 0.97 |
| flash_crowd | False | Open-loop QoE + SLA (2) | 5.44 | 5.10 | 5.77 | 0.47 | -11.57 | 0.69 | 0.95 | 0.09 | 0.97 |
| flash_crowd | False | DRL, replay-trained | -0.15 | -0.25 | -0.06 | 0.47 | 0.33 | 0.84 | 0.96 | 0.63 | 0.80 |
| flash_crowd | False | DRL, replay-trained, SLA (1) | -0.15 | -0.24 | -0.06 | 0.47 | 0.32 | 0.84 | 0.96 | 0.64 | 0.81 |
| flash_crowd | False | DRL, loop-trained | 0.47 | 0.37 | 0.57 | 0.47 | -1.01 | 0.82 | 0.98 | 0.55 | 0.73 |
| flash_crowd | False | DRL, loop-trained, SLA (1) | 0.40 | 0.30 | 0.50 | 0.47 | -0.84 | 0.82 | 0.98 | 0.57 | 0.73 |
| flash_crowd | False | EchoSlice-lite | 1.59 | 1.23 | 2.01 | 0.47 | -3.39 | 0.77 | 0.97 | 0.39 | 0.84 |
| flash_crowd | False | EchoSlice (v2) | 0.75 | 0.49 | 1.02 | 0.47 | -1.58 | 0.81 | 0.95 | 0.56 | 0.78 |
| flash_crowd | False | EchoSlice (v3) | 0.34 | 0.10 | 0.59 | 0.47 | -0.72 | 0.81 | 0.98 | 0.53 | 0.71 |
| flash_crowd | False | EchoSlice (v3), SLA (0.5) | 1.15 | 0.69 | 1.70 | 0.47 | -2.43 | 0.80 | 0.97 | 0.54 | 0.69 |
| flash_crowd | False | EchoSlice (v3), SLA (1) | 1.32 | 0.76 | 2.03 | 0.47 | -2.80 | 0.79 | 0.95 | 0.55 | 0.69 |
| flash_crowd | False | EchoSlice (v3), SLA (2) | 1.56 | 0.97 | 2.35 | 0.47 | -3.31 | 0.79 | 0.95 | 0.55 | 0.66 |
| flash_crowd | False | Static equal | 1.71 | 1.55 | 1.87 | 0.47 | -3.64 | 0.77 | 0.97 | 0.32 | 0.90 |
| flash_crowd | False | No slicing (PF) | 1.66 | 1.50 | 1.81 | 0.47 | -3.52 | 0.77 | 0.99 | 0.34 | 0.79 |
| flash_crowd | False | Static tuned at deploy | 2.31 | 2.14 | 2.49 | 0.47 | -4.90 | 0.75 | 0.96 | 0.27 | 0.93 |
| flash_crowd | True | Usage-proportional | 18.43 | 15.10 | 22.15 | 2.05 | -9.02 | 0.47 | 0.62 | 0.03 | 0.84 |
| flash_crowd | True | Forecast + 10% | 5.13 | 4.33 | 6.06 | 2.05 | -2.51 | 0.68 | 0.95 | 0.07 | 0.95 |
| flash_crowd | True | Forecast + 20% | -0.63 | -1.02 | -0.19 | 2.05 | 0.31 | 0.77 | 0.98 | 0.35 | 0.79 |
| flash_crowd | True | Forecast + 30% | -0.78 | -1.23 | -0.24 | 2.05 | 0.38 | 0.76 | 0.99 | 0.39 | 0.64 |
| flash_crowd | True | Forecast + 50% | 0.44 | -0.00 | 0.96 | 2.05 | -0.21 | 0.72 | 1.00 | 0.44 | 0.22 |
| flash_crowd | True | Open-loop QoE | 3.17 | 2.83 | 3.48 | 2.05 | -1.55 | 0.68 | 0.93 | 0.09 | 0.97 |
| flash_crowd | True | Open-loop QoE + SLA (0.5) | 2.98 | 2.67 | 3.28 | 2.05 | -1.45 | 0.68 | 0.93 | 0.10 | 0.97 |
| flash_crowd | True | Open-loop QoE + SLA (1) | 2.93 | 2.60 | 3.26 | 2.05 | -1.43 | 0.69 | 0.93 | 0.10 | 0.98 |
| flash_crowd | True | Open-loop QoE + SLA (2) | 2.86 | 2.51 | 3.21 | 2.05 | -1.40 | 0.69 | 0.93 | 0.10 | 0.97 |
| flash_crowd | True | DRL, replay-trained | -1.99 | -2.11 | -1.87 | 2.05 | 0.97 | 0.82 | 0.95 | 0.59 | 0.80 |
| flash_crowd | True | DRL, replay-trained, SLA (1) | -1.90 | -2.02 | -1.78 | 2.05 | 0.93 | 0.82 | 0.94 | 0.58 | 0.82 |
| flash_crowd | True | DRL, loop-trained | -1.63 | -1.77 | -1.48 | 2.05 | 0.79 | 0.80 | 0.98 | 0.51 | 0.68 |
| flash_crowd | True | DRL, loop-trained, SLA (1) | -1.57 | -1.69 | -1.45 | 2.05 | 0.77 | 0.79 | 0.97 | 0.50 | 0.71 |
| flash_crowd | True | EchoSlice-lite | 2.48 | 1.90 | 3.11 | 2.05 | -1.21 | 0.71 | 0.97 | 0.23 | 0.73 |
| flash_crowd | True | EchoSlice (v2) | -1.36 | -1.58 | -1.12 | 2.05 | 0.66 | 0.79 | 0.96 | 0.50 | 0.72 |
| flash_crowd | True | EchoSlice (v3) | -2.04 | -2.36 | -1.65 | 2.05 | 1.00 | 0.80 | 0.97 | 0.53 | 0.68 |
| flash_crowd | True | EchoSlice (v3), SLA (0.5) | -1.28 | -1.79 | -0.75 | 2.05 | 0.62 | 0.79 | 0.95 | 0.55 | 0.67 |
| flash_crowd | True | EchoSlice (v3), SLA (1) | -0.97 | -1.56 | -0.42 | 2.05 | 0.47 | 0.78 | 0.92 | 0.59 | 0.65 |
| flash_crowd | True | EchoSlice (v3), SLA (2) | -0.47 | -1.01 | 0.16 | 2.05 | 0.23 | 0.77 | 0.92 | 0.53 | 0.68 |
| flash_crowd | True | Static equal | 0.17 | 0.07 | 0.26 | 2.05 | -0.08 | 0.75 | 0.95 | 0.32 | 0.86 |
| flash_crowd | True | Static tuned at deploy | 7.11 | 6.79 | 7.43 | 2.05 | -3.47 | 0.69 | 0.97 | 0.07 | 0.95 |

![E7](../figures/fig_e7.png)


![E7 SLA trade-off](../figures/fig_e7_sla.png)

### E7 (final). Mean QoE against the worst slice's SLA

Hypervolume of each slicer family's (mean user MOS, worst-slice SLA) points, relative to the front of all static splits of the same cell (1.0 = as good as the best static splits chosen per cell with hindsight). Reference point: 10% below the best static split, SLA 0.

| cell            | strict   |   DRL, trained in loop |   DRL, trained on replay |   EchoSlice (v3) |   Forecast + h |   Open-loop QoE + SLA |   Static splits (clairvoyant per cell) |
|:----------------|:---------|-----------------------:|-------------------------:|-----------------:|---------------:|----------------------:|---------------------------------------:|
| M1-video-heavy  | False    |                  0.891 |                    0.85  |            0.8   |          0.125 |                 0.137 |                                      1 |
| M1-video-heavy  | True     |                  0.859 |                    0.721 |            0.686 |          0.115 |                 0.144 |                                      1 |
| M2-gaming-heavy | False    |                  0.703 |                    0.912 |            0.876 |          0.752 |                 0.206 |                                      1 |
| M2-gaming-heavy | True     |                  0.621 |                    0.826 |            0.765 |          0.675 |                 0.26  |                                      1 |
| M3-bulk-heavy   | False    |                  0.614 |                    0.689 |            0.874 |          0.817 |                 0.127 |                                      1 |
| M3-bulk-heavy   | True     |                  0.266 |                    0.433 |            0.872 |          0.779 |                 0.158 |                                      1 |
| day_cycle       | False    |                  0.951 |                    1.043 |            1.178 |          1.009 |                 0.276 |                                      1 |
| day_cycle       | True     |                  1.682 |                    1.983 |            2.649 |          2.472 |                 0.808 |                                      1 |
| flash_crowd     | False    |                  0.783 |                    0.945 |            0.733 |          0.446 |                 0.063 |                                      1 |
| flash_crowd     | True     |                  1.086 |                    1.308 |            1.138 |          0.777 |                 0.135 |                                      1 |

Mean-QoE gap (%) of the best point of each family whose worst-slice SLA is at least 0.7 (blank: no point reaches it):

| cell            | strict   |   DRL, trained in loop |   DRL, trained on replay |   EchoSlice (v3) |   Static splits (clairvoyant per cell) |
|:----------------|:---------|-----------------------:|-------------------------:|-----------------:|---------------------------------------:|
| M1-video-heavy  | False    |                   1.09 |                     1.58 |           nan    |                                   0.34 |
| M1-video-heavy  | True     |                   1.37 |                     3.14 |           nan    |                                   1.3  |
| M2-gaming-heavy | False    |                 nan    |                     0.34 |           nan    |                                   0.69 |
| M2-gaming-heavy | True     |                 nan    |                   nan    |           nan    |                                   1.82 |
| M3-bulk-heavy   | False    |                 nan    |                   nan    |           nan    |                                   0    |
| M3-bulk-heavy   | True     |                 nan    |                   nan    |           nan    |                                   0.09 |
| day_cycle       | False    |                 nan    |                    -0.29 |            -1.23 |                                   0.71 |

![frontier](../figures/fig_frontier.png)


## E9. Ablations of EchoSlice (v3)

Gap (%) to the best static split of each cell, 30 seeds; 'abl-freeze-at-eval' stops probing when scoring starts, so its difference to the full method is the QoE cost of probing in stationary cells.

| slicer              |   M1T |   M2F |   M3T |   dayT |   flashT |   vpT |   mean |   worst |
|:--------------------|------:|------:|------:|-------:|---------:|------:|-------:|--------:|
| abl-fixed-gain      |  0.21 |  0.27 |  0.51 |  -7.2  |    -1.71 |  0.58 |  -1.22 |    0.58 |
| abl-freeze-at-eval  |  0.36 |  0.39 | -0.15 |  -7.18 |    -2.2  |  0.14 |  -1.44 |    0.39 |
| abl-hold24          |  0.3  |  0.27 | -0.15 |  -7.61 |    -2.64 |  0.06 |  -1.63 |    0.3  |
| abl-hold6           |  0.55 |  0.68 |  2.3  |  -5.8  |     2.91 |  4.41 |   0.84 |    4.41 |
| abl-no-hold         |  0.5  |  0.65 |  1.72 |  -6.17 |     1.79 |  3.51 |   0.33 |    3.51 |
| abl-no-moves        |  0.49 |  0.34 |  0.09 |   3.23 |     6.82 |  2.55 |   2.25 |    6.82 |
| abl-no-prior        |  6.91 |  2.63 |  3.97 |  -1.03 |     1.31 |  0.63 |   2.4  |    6.91 |
| abl-pair-sign       |  1.74 |  1.5  |  2.48 |  -5.52 |     0.62 |  3.43 |   0.71 |    3.43 |
| abl-prior-only      |  0    |  0.44 | -0.33 |  -8.04 |    -3.28 | -0.65 |  -1.98 |    0.44 |
| abl-rate0.5         |  1.39 |  0.51 |  1.81 |  -6.54 |    -0.36 |  2.65 |  -0.09 |    2.65 |
| abl-rate0.5-noprobe |  6.66 |  9.86 |  2.5  |  -1.68 |     2.89 |  4.15 |   4.06 |    9.86 |
| abl-rate2           |  0.24 |  0.23 |  0.94 |  -6.67 |    -1.82 |  2.02 |  -0.84 |    2.02 |
| abl-rate2-noprobe   | -0.04 |  0.14 |  3.13 |  -6.24 |     0.45 |  4.3  |   0.29 |    4.3  |
| abl-share-space     |  0.33 |  0.43 |  0.49 |  -7.36 |    -2.67 | -0.29 |  -1.51 |    0.49 |
| echoslice           |  4.63 |  1.76 |  2.21 |  -5.14 |    -1.36 |  1.42 |   0.59 |    4.63 |

Worst-slice SLA:

| slicer              |   M1T |   M2F |   M3T |   dayT |   flashT |   vpT |
|:--------------------|------:|------:|------:|-------:|---------:|------:|
| abl-fixed-gain      |  0.36 |  0.62 |  0.57 |   0.65 |     0.44 |  0.53 |
| abl-freeze-at-eval  |  0.32 |  0.58 |  0.55 |   0.58 |     0.47 |  0.48 |
| abl-hold24          |  0.42 |  0.69 |  0.57 |   0.69 |     0.54 |  0.54 |
| abl-hold6           |  0.12 |  0.59 |  0.46 |   0.5  |     0.12 |  0.2  |
| abl-no-hold         |  0.12 |  0.56 |  0.43 |   0.52 |     0.17 |  0.26 |
| abl-no-moves        |  0.34 |  0.61 |  0.56 |   0.19 |     0.08 |  0.57 |
| abl-no-prior        |  0.7  |  0.57 |  0.52 |   0.36 |     0.23 |  0.6  |
| abl-pair-sign       |  0.41 |  0.62 |  0.42 |   0.61 |     0.47 |  0.46 |
| abl-prior-only      |  0.37 |  0.69 |  0.6  |   0.7  |     0.59 |  0.51 |
| abl-rate0.5         |  0.29 |  0.67 |  0.36 |   0.57 |     0.37 |  0.54 |
| abl-rate0.5-noprobe |  0.22 |  0.34 |  0.24 |   0.3  |     0.29 |  0.31 |
| abl-rate2           |  0.29 |  0.57 |  0.68 |   0.58 |     0.46 |  0.3  |
| abl-rate2-noprobe   |  0.35 |  0.51 |  0.55 |   0.39 |     0.1  |  0    |
| abl-share-space     |  0.34 |  0.66 |  0.54 |   0.64 |     0.52 |  0.55 |
| echoslice           |  0.65 |  0.6  |  0.62 |   0.67 |     0.47 |  0.52 |

![ablations](../figures/fig_ablation.png)


## E10. Imperfect telemetry

Gap (%) to the best static split (static splits do not read telemetry), mean over the four cells:

| slicer        |   delay2s |   delay5s |   drop20 |   none |   qnoise0.1 |   qnoise0.3 |   qoe-from-kpm |
|:--------------|----------:|----------:|---------:|-------:|------------:|------------:|---------------:|
| drl-loop      |     -0.97 |     -0.92 |    -0.95 |  -1    |       -0.97 |       -0.94 |          -0.96 |
| echoslice3    |     -1.89 |     -1.81 |    -2.08 |  -1.96 |       -2.06 |       -2.03 |          -2.51 |
| echoslice3-l1 |     -0.65 |     -0.44 |    -0.62 |  -0.53 |       -0.39 |       -0.34 |          -0.89 |
| forecast+20%  |      1.01 |      2.12 |    -0.96 |  -1.32 |       -1.32 |       -1.32 |          -1.32 |
| ol-qoe+10%    |      2.22 |      2.7  |     1.25 |   1.18 |        1.18 |        1.18 |           1.18 |
| usage-prop    |      7.43 |      6.37 |     8.52 |   9.51 |        9.51 |        9.51 |           9.51 |

Worst cell:

| slicer        |   delay2s |   delay5s |   drop20 |   none |   qnoise0.1 |   qnoise0.3 |   qoe-from-kpm |
|:--------------|----------:|----------:|---------:|-------:|------------:|------------:|---------------:|
| drl-loop      |      1.46 |      1.6  |     1.5  |   1.38 |        1.43 |        1.5  |           1.61 |
| echoslice3    |      1.2  |      1.43 |     0.96 |   0.93 |        0.88 |        0.87 |           0.37 |
| echoslice3-l1 |      2.33 |      2.85 |     1.82 |   2.32 |        2.63 |        2.65 |           2.55 |
| forecast+20%  |      6.32 |      6.96 |     2.23 |   1.86 |        1.86 |        1.86 |           1.86 |
| ol-qoe+10%    |      5.26 |      5.94 |     4.23 |   4.1  |        4.1  |        4.1  |           4.1  |
| usage-prop    |     16.06 |     12.82 |    17.15 |  18.43 |       18.43 |       18.43 |          18.43 |

![telemetry](../figures/fig_telemetry.png)


## E11. App hints (cooperative mode) and a lying app

Gap (%) to the best static split; 'hint-liar' = the gaming app reports 3x its true saturation rate.

| cell            |   echoslice3 |   echoslice3-l1 |   hint |   hint-l1 |   hint-liar |
|:----------------|-------------:|----------------:|-------:|----------:|------------:|
| M1-video-heavy  |         0.22 |            1.56 |   0.16 |      0.51 |        0.4  |
| M2-gaming-heavy |         0.61 |            1.43 |   1.27 |      2.69 |        1.12 |
| M3-bulk-heavy   |         0.22 |            1.77 |   1.47 |      2.88 |        2.24 |
| X1-xr           |         1.2  |            3.54 |   4.03 |      3.49 |        3.8  |
| day_cycle       |        -4.23 |           -3.13 |  -3.38 |     -2.95 |       -3.41 |
| flash_crowd     |        -0.85 |            0.17 |   2.97 |      2.08 |        1.93 |

Worst-slice SLA:

| cell            |   echoslice3 |   echoslice3-l1 |   hint |   hint-l1 |   hint-liar |
|:----------------|-------------:|----------------:|-------:|----------:|------------:|
| M1-video-heavy  |         0.38 |            0.6  |   0.23 |      0.38 |        0.36 |
| M2-gaming-heavy |         0.57 |            0.63 |   0.51 |      0.49 |        0.44 |
| M3-bulk-heavy   |         0.6  |            0.63 |   0.61 |      0.54 |        0.63 |
| X1-xr           |         0.1  |            0.19 |   0.03 |      0.04 |        0.04 |
| day_cycle       |         0.68 |            0.69 |   0.57 |      0.57 |        0.59 |
| flash_crowd     |         0.5  |            0.51 |   0.17 |      0.25 |        0.24 |

## E12. XR and L4S cells

X1: 24 video, 6 XR (5-60 Mb/s, 20 ms frame budget), 6 bulk. X2: X1 with TCP Prague + L4S marking for video and bulk. X3: 24 video, 8 cloud gaming, 6 bulk, all TCP over L4S. Gap (%) to the best static split:

| slicer          |   X1-xr shareable |   X1-xr strict |   X2-xr-l4s shareable |   X2-xr-l4s strict |   X3-game-l4s shareable |   X3-game-l4s strict |
|:----------------|------------------:|---------------:|----------------------:|-------------------:|------------------------:|---------------------:|
| drl-loop        |              0.25 |           0.99 |                  0.85 |               1.1  |                    0.14 |                -0.01 |
| drl-twin        |              0.04 |          -0.23 |                  0.21 |               0.14 |                    1.22 |                 2.25 |
| echoslice       |              0.51 |           1.39 |                  0.87 |               1.16 |                    0.46 |                 0.62 |
| echoslice-lite  |              0.51 |           1.39 |                  0.87 |               1.16 |                    0.46 |                 0.62 |
| echoslice3      |              1.16 |           1.24 |                  1.14 |               1.77 |                    0.88 |                 0.73 |
| echoslice3-l1   |              2.5  |           4.59 |                  2.27 |               5.41 |                    1.67 |                 1.7  |
| forecast+20%    |              3.5  |           2.67 |                  2.66 |               2.82 |                    1.49 |                 1.64 |
| ol-qoe+10%      |              5.38 |           4.59 |                  3.71 |               4.45 |                    2.39 |                 3.81 |
| ol-qoe+10%-sla1 |              4.4  |           3.83 |                  2.96 |               3.54 |                    2.51 |                 3.8  |
| shared          |              3.36 |         nan    |                  2.83 |             nan    |                    1.05 |               nan    |
| static          |              0.27 |           0.09 |                  0.26 |               0.19 |                    0.06 |                 0.21 |
| usage-prop      |              8.65 |           7.52 |                  4.89 |               5.26 |                    3.91 |                 7.37 |

Worst-slice SLA:

| slicer          |   X1-xr shareable |   X1-xr strict |   X2-xr-l4s shareable |   X2-xr-l4s strict |   X3-game-l4s shareable |   X3-game-l4s strict |
|:----------------|------------------:|---------------:|----------------------:|-------------------:|------------------------:|---------------------:|
| drl-loop        |              0.09 |           0.01 |                  0.02 |               0.01 |                    0.72 |                 0.71 |
| drl-twin        |              0.19 |           0.14 |                  0.36 |               0.21 |                    0.63 |                 0.61 |
| echoslice       |              0.16 |           0.09 |                  0.16 |               0.09 |                    0.69 |                 0.58 |
| echoslice-lite  |              0.16 |           0.09 |                  0.16 |               0.09 |                    0.69 |                 0.58 |
| echoslice3      |              0.12 |           0.07 |                  0.13 |               0.11 |                    0.48 |                 0.54 |
| echoslice3-l1   |              0.19 |           0.18 |                  0.17 |               0.11 |                    0.46 |                 0.62 |
| forecast+20%    |              0.01 |           0.02 |                  0.02 |               0    |                    0.39 |                 0.38 |
| ol-qoe+10%      |              0    |           0    |                  0    |               0    |                    0.28 |                 0.12 |
| ol-qoe+10%-sla1 |              0    |           0    |                  0    |               0    |                    0.28 |                 0.13 |
| shared          |              0    |         nan    |                  0    |             nan    |                    0.53 |               nan    |
| static          |              0.08 |           0.07 |                  0.08 |               0.08 |                    0.7  |                 0.7  |
| usage-prop      |              0    |           0    |                  0    |               0    |                    0.09 |                 0    |

Mean per-UE queue delay of L4S flows (ms):

| slicer          |   X2-xr-l4s shareable |   X2-xr-l4s strict |   X3-game-l4s shareable |   X3-game-l4s strict |
|:----------------|----------------------:|-------------------:|------------------------:|---------------------:|
| drl-loop        |                  0.67 |               0.67 |                    0.77 |                 0.72 |
| drl-twin        |                  0.97 |               0.9  |                    0.98 |                 1.11 |
| echoslice       |                  0.94 |               0.9  |                    0.75 |                 0.82 |
| echoslice-lite  |                  0.94 |               0.9  |                    0.75 |                 0.82 |
| echoslice3      |                  0.89 |               0.99 |                    0.67 |                 0.66 |
| echoslice3-l1   |                  1.26 |               1.6  |                    0.95 |                 0.95 |
| forecast+20%    |                  0.6  |               0.59 |                    0.6  |                 0.61 |
| ol-qoe+10%      |                  0.83 |               0.96 |                    0.78 |                 0.92 |
| ol-qoe+10%-sla1 |                  0.83 |               0.95 |                    0.79 |                 0.9  |
| shared          |                  0.46 |             nan    |                    0.46 |               nan    |
| static          |                  0.77 |               0.87 |                    0.77 |                 0.83 |
| usage-prop      |                  0.46 |               0.44 |                    0.43 |                 0.42 |

## E13. Theory checks

App response from randomised share steps (median over runs):

| app         |   runs |   beta |   ratio |   tau_s |   delay_s |   h_star_pred |
|:------------|-------:|-------:|--------:|--------:|----------:|--------------:|
| bulk-cubic  |     30 |  0.777 |   1.002 |   2.81  |         0 |        -0.002 |
| bulk-prague |     30 |  0.796 |   0.95  |   3.12  |         0 |         0.053 |
| gaming-gcc  |     30 |  0.564 |   0.642 |  47.635 |         0 |         0.558 |
| video-bola  |     30 |  0.244 |   0.846 |   0.145 |         0 |         0.182 |
| video-dyn   |     30 |  0.241 |   0.837 |   0.145 |         0 |         0.195 |
| video-tput  |     30 |  0.451 |   0.864 |   0.574 |         0 |         0.158 |
| xr-gcc      |     30 |  0.487 |   0.523 |  45.107 |         0 |         0.914 |

Knife-edge: ratio = steady offered load / capacity given (politeness when < 1), tau = adaptation time, and the headroom knife-edge it predicts, h* = 1/ratio - 1, against the measured knife-edge of forecast + h (strict and shareable):

| app        | strict   |   h_star_meas |   x_floor |   x_top |   ratio |   beta |   tau_s |   delay_s |   h_star_pred |
|:-----------|:---------|--------------:|----------:|--------:|--------:|-------:|--------:|----------:|--------------:|
| gaming-gcc | False    |          0.18 |     0.052 |   0.633 |   0.642 |  0.564 |  47.635 |         0 |         0.558 |
| gaming-gcc | True     |          0.18 |     0.052 |   0.632 |   0.642 |  0.564 |  47.635 |         0 |         0.558 |
| video-bola | False    |          0.06 |     0.116 |   0.855 |   0.846 |  0.244 |   0.145 |         0 |         0.182 |
| video-bola | True     |          0.06 |     0.11  |   0.856 |   0.846 |  0.244 |   0.145 |         0 |         0.182 |
| video-dyn  | False    |          0.06 |     0.114 |   0.856 |   0.837 |  0.241 |   0.145 |         0 |         0.195 |
| video-dyn  | True     |          0.06 |     0.11  |   0.857 |   0.837 |  0.241 |   0.145 |         0 |         0.195 |
| video-tput | False    |          0.06 |     0.056 |   0.858 |   0.864 |  0.451 |   0.574 |         0 |         0.158 |
| video-tput | True     |          0.06 |     0.056 |   0.858 |   0.864 |  0.451 |   0.574 |         0 |         0.158 |
| xr-gcc     | False    |          0.22 |     0.091 |   0.635 |   0.523 |  0.487 |  45.107 |         0 |         0.914 |
| xr-gcc     | True     |          0.22 |     0.091 |   0.633 |   0.523 |  0.487 |  45.107 |         0 |         0.914 |

Resonance: Spearman correlation between the video-share swing and the predicted gain G (per-period averaging times the EWMA filter, at the segment on-off frequency): all 0.78; per slicer forecast a=0.3 0.98, usage a=0.2 0.95, usage a=0.5 0.96, usage a=1 0.97.


![theory](../figures/fig_theory.png)


## E14. Convergence (1,800 s runs, QoE per minute)

Minutes until the 3-minute rolling gap to the best static split stays below 1% (blank: never), and the mean gap over the first 5 and last 10 minutes:

| slicer        |   M1F |   M1T |   M2F |   M2T |   M3F |   M3T |
|:--------------|------:|------:|------:|------:|------:|------:|
| drl-loop      |    29 |   nan |   nan |   nan |   nan |   nan |
| echoslice     |    24 |    26 |    18 |   nan |   nan |   nan |
| echoslice3    |     4 |     4 |     4 |   nan |     4 |     4 |
| echoslice3-l1 |   nan |   nan |    27 |   nan |   nan |   nan |
| forecast+20%  |     4 |     4 |     5 |     6 |   nan |     4 |
| ol-qoe+10%    |    28 |   nan |   nan |   nan |   nan |   nan |

Gap over the last 10 minutes (%):

| slicer        |   M1F |   M1T |   M2F |   M2T |   M3F |   M3T |
|:--------------|------:|------:|------:|------:|------:|------:|
| drl-loop      |  0.94 |  1.3  |  2.07 |  2.63 |  2.64 |  6.75 |
| echoslice     |  0.92 |  1.01 |  0.79 |  1.09 |  2.1  |  1.48 |
| echoslice3    | -0.19 |  0.1  |  0.49 |  1.17 |  0.61 |  0.15 |
| echoslice3-l1 |  1.1  |  2.08 |  0.85 |  2.17 |  2.4  |  2.38 |
| forecast+20%  |  0.51 |  0.47 |  0.75 |  0.68 |  1.49 |  0.78 |
| ol-qoe+10%    |  0.99 |  1.18 |  6.15 |  5.89 |  2.85 |  2.22 |

![convergence](../figures/fig_convergence.png)


## DRL training (PPO)

- loop: selected iteration 59 (validation utility 2.788, 2400 training episodes)
- twin: selected iteration 139 (validation utility 3.546, 5600 training episodes)

![DRL learning](../figures/fig_drl.png)

