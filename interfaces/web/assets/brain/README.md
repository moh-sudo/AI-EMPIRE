# Brain hemisphere source data

Real, MRI-derived human brain geometry — not procedurally generated.

- **Source:** [NIH 3D](https://3d.nih.gov/) (National Institutes of Health), entries [3DPX-000757](https://3d.nih.gov/discover/3DPX-000757) (left hemisphere) and [3DPX-000758](https://3d.nih.gov/discover/3DPX-000758) (right hemisphere)
- **Origin:** "Left/Right hemisphere of the brain of Rajat Jain (25), obtained with an MRI scan and used in UCSF's and UCSD's glassbrain project." (neuroscapelab, [glassbrain project](http://neuroscapelab.com/projects/glass-brain/))
- **License:** Public Domain
- **Files:** `lh_NIH3D.glb` (~5.0 MB, ~138k vertices), `rh_NIH3D.glb` (~5.0 MB, ~138k vertices)
- **Downloaded:** 2026-08-25

Loaded and aligned by `interfaces/web/js/AnatomyCheck.js` — see that file's comments for the real coordinate-system fix applied (the source data's own up-axis isn't Three.js's Y-up) and how the two hemispheres are positioned relative to each other.
