# Accuracy & Validation

## Independent Research Validation — VIVE Ultimate Tracker (VUT)

VIVE Ultimate Tracker hardware has been independently validated against the
Vicon gold-standard motion capture system by researchers at Neuroscience
Research Australia (NeuRA) and UNSW Sydney.

He, Y., Brodie, M.A., Kim, J., Humburg, P., Lord, S.R. et al. "Validation of
the HTC VIVE Ultimate Trackers Compared with the Vicon Motion Capture System
at Slow, Moderate and Fast Gait Speeds" Research Square preprint (2026).
https://doi.org/10.21203/rs.3.rs-6989733/v1

In summary, the study found research- and clinical-grade accuracy for
sacrum and foot tracking at normal gait speeds (≤1.5 m/s), with accuracy
varying by tracker location, movement direction, and speed.

| Location | Speed | Absolute Error (median) | CCC |
|----------|-------|------------------------|-----|
| Sacrum | 0.5 m/s | 1.04mm | >0.999 |
| Sacrum | 2.0 m/s | 1.24mm | >0.999 |
| Foot | 0.5 m/s | 1.85mm | >0.98 |
| Foot | 2.0 m/s | 2.81mm | >0.98 |

For full methodology and results, refer to the paper.

---

## Important Caveat — Headless Mode

> **!!! More validation needed !!!**

The above study used SteamVR with an active VIVE XR Elite HMD present in the
session. The VT Headless SDK runs SteamVR without a headset
(VRApplication_Background mode).

Whether tracking accuracy differs in headless mode versus HMD-present mode has
**not yet been independently validated**. The noise-floor figures below
characterise stationary jitter in headless mode, but full movement-accuracy
validation in headless mode remains outstanding.

---

## Constant Calibration Offset

The above study notes a constant offset error inherent in the SteamVR-based
calibration, which the authors corrected using a Kabsch/SVD alignment to their
Vicon reference (see the paper, Figure 3 and Section 2.4). They highlight the
need for practical procedures to correct this offset in applied settings.

This SDK provides two such procedures: ******Hybrid Tracking & Calibration needs to be tested and verfied further****** 

- **Lighthouse anchor calibration** — a brief slow-movement calibration
  aligns VUT to the Lighthouse coordinate frame; a fixed Vive Tracker 3.0
  then serves as a continuous reference to correct offset and drift.
  
- **Printed sheet calibration** — corrects the offset against trackers placed
  at known printed positions, for VUT-only setups. *(In development.)*

Acknowledgement: this limitation and the correction approaches were identified
and suggested by the NeuRA / UNSW Sydney team (He et al., 2026).

---

## Noise Floor (measured via VT Headless SDK)

The SDK includes a noise-floor tool (Measurement page → "Noise Floor") to
characterise your own environment.

Reference measurement — single tracker, rigid stationary surface, headless:

| Axis | Std Dev | Peak Range |
|------|---------|-----------|
| X | 0.17mm | 0.90mm |
| Y | 0.16mm | 0.90mm |
| Z | 0.20mm | 1.00mm |
| **3D RMS** | **0.30mm** | — |

Repeat measurements in good environments are consistent (3D RMS
0.24-0.36mm). This is the stationary noise floor only — it excludes the
calibration offset and movement-induced error.

---

## Environmental Factors

VUT uses SLAM, so accuracy depends on the environment:

- **Feature richness** — featureless surfaces degrade tracking; varied
  textures and patterns improve it.
- **Lighting** — consistent diffuse lighting is best; darkness causes SLAM to
  fail (use Lighthouse trackers for dark environments).
- **Map quality** — a thorough VIVE Hub room scan lowers jitter.

Characterise your environment with the noise-floor tool before collecting
research data.

---

## Vive Tracker 3.0 + Base Station (Lighthouse)

| Metric | Tracker 3.0 (LH) | VUT (SLAM) |
|--------|-----------------|------------|
| Position accuracy | <1mm | ~1-3mm |
| Constant offset error | None | Several cm (correctable) |
| Dark environments | ✓ | ✗ |
| Featureless rooms | ✓ | ✗ |
| Session persistence | ✓ Stable | Standard: drift |

Source: Valve published specifications. Headless SDK validation not yet
available.

---

## Hybrid Space Calibration ******Hybrid Tracking & Calibration needs to be tested and verfied further****** 

The SDK aligns VUT and Lighthouse into one coordinate space using a Kabsch
transform from a slow-movement capture. Measured residual: ~3mm (slow
capture) to 5-15mm (typical hand-held). The limit is VUT's own SLAM noise, not
the algorithm — slow movement during calibration is essential.

Inspired by the community OpenVR Space Calibrator project, but operates at the
SDK level with no SteamVR driver modification.

> Mixed-mode (VUT + Lighthouse simultaneously) is not yet broadly validated.
> Treat hybrid figures as preliminary.

---

## Citation

If you use VT Headless SDK in research, please cite the hardware validation
study:

He, Y. et al. (2026). Validation of the HTC VIVE Ultimate Trackers Compared
with the Vicon Motion Capture System at Slow, Moderate and Fast Gait Speeds.
Research Square. https://doi.org/10.21203/rs.3.rs-6989733/v1

And reference this SDK:
Abeynayake, N. (2026). VT Headless SDK. GitHub.
https://github.com/nandunabey/VT-Headless-SDK
