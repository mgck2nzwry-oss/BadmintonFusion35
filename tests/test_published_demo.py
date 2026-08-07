from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "a10_r10"


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class PublishedA10R10Tests(unittest.TestCase):
    def test_checksums_and_locked_scope(self) -> None:
        for line in (DEMO / "checksums.sha256").read_text(encoding="utf-8").splitlines():
            expected, relative = line.split("  ", 1)
            self.assertEqual(file_hash(DEMO / relative), expected, relative)

        metadata = json.loads((DEMO / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["trial_id"], "A10-R10")
        self.assertEqual(metadata["visual"]["frames"], 203)
        self.assertEqual(metadata["visual"]["two_dimensional"]["rows"], 4 * 203 * 26)
        self.assertEqual(metadata["visual"]["three_dimensional"]["rows"], 203 * 22)
        self.assertEqual(metadata["imu"]["rows"], 4 * 169)
        self.assertTrue(
            metadata["visual"]["two_dimensional"][
                "offset_mapping_verified_by_exact_file_content"
            ]
        )

    def test_public_imu_metrics_match_published_samples(self) -> None:
        imu = pd.read_csv(DEMO / "imu" / "imu_50hz_filtered.csv")
        metrics = pd.read_csv(DEMO / "imu" / "repetition_metrics.csv").set_index("Device")
        for device, group in imu.groupby("device"):
            valid = group.loc[group["valid"]]
            self.assertEqual(len(valid), int(metrics.loc[device, "ValidSamples"]))
            self.assertAlmostEqual(
                valid["gyro_magnitude_deg_s"].max(),
                metrics.loc[device, "GyroMagnitudePeak_deg_s"],
                places=9,
            )
            self.assertAlmostEqual(
                valid["dynamic_acceleration_proxy_g"].max(),
                metrics.loc[device, "DynamicAccelerationPeak_g"],
                places=9,
            )


if __name__ == "__main__":
    unittest.main()
