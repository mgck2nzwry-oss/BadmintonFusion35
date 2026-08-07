# Four-camera demonstration trial

This package documents four views of action A10, repeat 10 (`A10-R10`), performed by one
consenting author-participant. The videos are attached to the GitHub `v0.1.1` release
rather than committed to Git history:

- [cam01.mp4](https://github.com/mgck2nzwry-oss/Court35/releases/download/v0.1.1/cam01.mp4)
- [cam02.mp4](https://github.com/mgck2nzwry-oss/Court35/releases/download/v0.1.1/cam02.mp4)
- [cam03.mp4](https://github.com/mgck2nzwry-oss/Court35/releases/download/v0.1.1/cam03.mp4)
- [cam04.mp4](https://github.com/mgck2nzwry-oss/Court35/releases/download/v0.1.1/cam04.mp4)

## Scope

- same participant, venue and study-owner-designated trial;
- H.264 video at 60 frames/s;
- existing pose and privacy overlays retained;
- audio streams removed;
- source creation-time metadata removed;
- video bitstreams copied without image re-encoding.

The files were independently trimmed. Their unequal durations and frame counts mean
that this release demonstrates four-view coverage and processed output, not measured
frame-level synchronization accuracy. The study owner subsequently identified the
supplied clips as `A10-R10`; this is owner-provided provenance, not an inference from
the video content.

The corresponding compact synchronized 2D, filtered 3D and aligned IMU evidence is in
[`examples/a10_r10`](../a10_r10/README.md). The released clips remain independently
trimmed and are not used to claim frame-level video synchronization accuracy.

See `metadata.json` for stream properties and `checksums.sha256` for integrity checks.
The media terms are stated in the repository-level `MEDIA_NOTICE.md`.
