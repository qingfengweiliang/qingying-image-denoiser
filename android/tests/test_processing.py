"""Run with a host Python containing numpy, scipy, Pillow and OpenCV."""
import sys
import tempfile
from pathlib import Path
import unittest
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app/src/main/python'))
import processing

class ProcessingTests(unittest.TestCase):
    def test_stage_reporting_does_not_change_pixels(self):
        class Listener:
            def __init__(self):
                self.stages = []

            def onPythonStage(self, stage):
                self.stages.append(stage)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGBA', (19, 17), (96, 144, 192, 128)).save(root / 'in.png')
            for mode in range(2, 6):
                listener = Listener()
                processing.process(str(root / 'in.png'), str(root / 'reported.png'), mode, 2, listener)
                processing.process(str(root / 'in.png'), str(root / 'plain.png'), mode, 2)
                self.assertEqual(len(listener.stages), 4)
                self.assertEqual([s.split(' · ')[0] for s in listener.stages],
                                 [f'步骤 {n}/4' for n in range(1, 5)])
                self.assertEqual((root / 'reported.png').read_bytes(), (root / 'plain.png').read_bytes())

    def test_denoising_alpha_and_exports(self):
        rng = np.random.default_rng(7)
        rgba = np.empty((48, 64, 4), np.uint8)
        rgba[:, :, :3] = np.clip(128 + rng.normal(0, 8, (48, 64, 3)), 0, 255)
        rgba[:, :, 3] = np.arange(64, dtype=np.uint8)[None, :] * 4
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.fromarray(rgba).save(root / 'in.png')
            processing.prepare(str(root / 'in.png'), str(root / 'prepared.png'))
            for mode in range(2, 6):
                for strength in ([1, 2, 3] if mode == 2 else [1, 10, 30]):
                    processing.process(str(root / 'prepared.png'), str(root / 'out.png'), mode, strength)
                    with Image.open(root / 'out.png') as image:
                        result = np.array(image)
                    self.assertEqual(result.shape, rgba.shape)
                    np.testing.assert_array_equal(result[:, :, 3], rgba[:, :, 3])
                    if mode != 3 or strength >= 10:
                        self.assertLess(result[:, :, :3].std(), rgba[:, :, :3].std())
            for fmt in ('PNG', 'JPEG', 'WEBP'):
                processing.export(str(root / 'out.png'), str(root / 'export'), fmt)
                with Image.open(root / 'export') as image:
                    self.assertEqual(image.size, (64, 48))
            processing.export(str(root / 'out.png'), str(root / 'export'), 'JPEG')
            with Image.open(root / 'export') as image:
                self.assertGreater(min(image.getpixel((0, 20))), 240)

if __name__ == '__main__':
    unittest.main()
