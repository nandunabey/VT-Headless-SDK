# Accuracy & Validation

## Independent Research Validation

VIVE Ultimate Tracker hardware has been validated against 
the Vicon gold-standard motion capture system by researchers 
at Neuroscience Research Australia (NeuRA) and UNSW Sydney.

He, Y., Brodie, M.A., Kim, J., Humburg, P., Lord, S.R. et al.
"Validation of the HTC VIVE Ultimate Trackers Compared with 
the Vicon Motion Capture System at Slow, Moderate and Fast 
Gait Speeds"
Research Square preprint (2026)
https://doi.org/10.21203/rs.3.rs-6989733/v1

### Key findings

| Location | Speed   | Absolute Error (median) | CCC    |
|----------|---------|------------------------|--------|
| Sacrum   | 0.5 m/s | 1.04mm                 | >0.999 |
| Sacrum   | 1.0 m/s | 0.86mm                 | >0.999 |
| Sacrum   | 2.0 m/s | 1.24mm                 | >0.999 |
| Foot     | 0.5 m/s | 1.85mm                 | >0.98  |
| Foot     | 1.0 m/s | 2.43mm                 | >0.98  |
| Foot     | 2.0 m/s | 2.81mm                 | >0.98  |

Concordance Correlation Coefficient (CCC) > 0.99 is 
considered "almost perfect" agreement (McBride, 2005).

### Important caveat — headless mode - !!! More validation Needed!!! 

The above study used SteamVR with an active VIVE XR Elite 
HMD present in the session. The VUT Headless SDK runs 
SteamVR without a headset (VRApplication_Background mode).

Whether tracking accuracy differs in headless mode vs 
HMD-present mode has not yet been independently validated.

Anecdotal observation from SDK development:
- Position jitter at rest: ~0.1mm (measured from 
  stationary tracker, 60Hz stream)
- This is consistent with the published figures above

Headless mode accuracy validation is a planned feature 
of the research/benchmark tool (v0.3).

## Environmental Factors

Tracking accuracy is significantly affected by the
physical environment. VIVE Ultimate Trackers use SLAM
(visual simultaneous localisation and mapping) —
accuracy depends on:

- **Feature richness** — plain walls and featureless
  surfaces degrade tracking. Varied textures and
  patterns improve it.
- **Lighting** — consistent diffuse lighting is optimal.
  Direct sunlight, strobing, or very low light reduces
  accuracy.
- **Room size** — larger spaces with more visual anchors
  generally track better.
- **Map quality** — VIVE Hub's room scan builds the
  tracking map. Follow HTC's environment setup guidelines
  for best results before any research data collection.

For research deployments, characterise your specific
environment using the benchmark tool (v0.3) before
collecting study data.

## Noise Floor (measured via VUT Headless SDK)   -  !! MORE Valifation needed!! 

Methodology: single tracker placed on rigid stationary 
surface, recorded for 65 seconds at 64.1Hz, 
4,171 frames captured.

Tracker serial: 41-A33204726
Measurement date: 17 May 2026
SDK version: v0.1.0-alpha
Mode: Standard tracking, headless (VRApplication_Background)

Results:
| Axis | Std Dev | Peak Range |
|------|---------|------------|
| X    | 0.17mm  | 0.90mm     |
| Y    | 0.16mm  | 0.90mm     |
| Z    | 0.20mm  | 1.00mm     |
| 3D RMS | 0.30mm | — |

This represents the noise floor of the SDK in headless 
mode — i.e. the minimum measurable position uncertainty 
for a stationary object.

Note: this is a single-tracker measurement under
controlled indoor conditions. Results may vary with
environment, lighting, and tracker orientation.

## Vive Tracker 3.0 Accuracy

| Metric | Tracker 3.0 (LH) | VUT (SLAM) |
|--------|-----------------|------------|
| Position accuracy | <1mm | 1–3mm |
| Dark environments | ✓ | ✗ |
| Featureless rooms | ✓ | ✗ |
| Session persistence | ✓ Stable | Standard: drift |

Source: Valve published specifications.
Headless SDK validation: not yet available.

## Citation

If you use VUT Headless SDK in research, please cite 
the hardware validation study:

  He, Y. et al. (2026). Validation of the HTC VIVE 
  Ultimate Trackers Compared with the Vicon Motion 
  Capture System at Slow, Moderate and Fast Gait Speeds.
  Research Square. https://doi.org/10.21203/rs.3.rs-6989733/v1

And reference this SDK:
  Abeynayake, N. (2026). VUT Headless SDK.
  GitHub. https://github.com/nandunabey/VUT-Headless-SDK
