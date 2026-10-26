# Real-player check

Real dash.js players (4.7.4, default ABR) in headless Chromium and greedy TCP downloads share one paced
bottleneck that is split into a video slice and a bulk slice (strict mode). A slicer sets the shares every second.

    npm install dashjs@4.7.4 && mkdir -p www/dashjs && cp node_modules/dashjs/dist/dash.all.min.js www/dashjs/
    bash make_video.sh                  # 680 s test video, 6 rungs, 4 s segments
    python campaign.py 1,2,3            # 240 s runs (12 s hold), results/
    python campaign2.py                 # 600 s runs (36 s hold), results600/
    python analyze.py results && python analyze.py results600

Needs Python with playwright (Chromium installed), numpy, pandas, itu-p1203, and the simulator package of this
repository for the QoE models. Run one testbed at a time on a small machine: several in parallel can starve the
players of CPU, which shows up as stalls that have nothing to do with the bottleneck (each run logs the load).
