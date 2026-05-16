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

### Important caveat — headless mode

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

## Noise Floor (SDK measurement)

From live session data captured via this SDK:
- Stationary tracker position variance: ~0.1mm
- Measured at 60Hz broadcast rate
- Single tracker, standard tracking mode

This represents the noise floor of the system at rest.
Movement accuracy will vary with speed — see He et al. above.

## Comparison to other systems

| System | Typical Error | Cost | Portable |
|--------|--------------|------|----------|
| Vicon / OptiTrack | <1mm | $50k-$500k | No |
| Xsens IMU suit | 5-15mm (drift) | $15k-$40k | Yes |
| VIVE Ultimate Tracker | 1-3mm | ~$300/tracker | Yes |
| MediaPipe (camera) | 50-100mm | Free | Yes |
| Microsoft Kinect | 10-30mm | Discontinued | No |

Sources: He et al. 2026, Kulozik & Jarrassé 2024, 
published literature. Costs approximate.

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
