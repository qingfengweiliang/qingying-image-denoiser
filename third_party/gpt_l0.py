"""CPU L0 gradient smoothing adapted from CXP-2024/gpt-anime-denoise (MIT).

See licenses/gpt-anime-denoise-LICENSE.txt for the upstream copyright.
Uses the upstream float64 NumPy algorithm; no torch or model download required.
"""
import numpy as np


def smooth(image, lam, stop=None):
    if not np.isfinite(lam) or lam <= 0:
        raise ValueError('L0 强度必须大于 0。')
    source = np.asarray(image, dtype=np.float64) / 255.0
    height, width, _ = source.shape
    # Periodic forward differences, including one-pixel-wide images.
    fx = np.zeros((height, width))
    fy = np.zeros((height, width))
    if width > 1:
        fx[0, 0], fx[0, -1] = -1, 1
    if height > 1:
        fy[0, 0], fy[-1, 0] = -1, 1
    otf = np.abs(np.fft.fft2(fx)) ** 2 + np.abs(np.fft.fft2(fy)) ** 2
    numerator = np.fft.fft2(source, axes=(0, 1))
    value = source.copy()
    beta = 2 * lam
    while beta < 1e5:
        if stop is not None and stop():
            raise RuntimeError('处理已取消。')
        horizontal = np.roll(value, -1, 1) - value
        vertical = np.roll(value, -1, 0) - value
        mask = (horizontal ** 2 + vertical ** 2).sum(2) < lam / beta
        horizontal[mask] = 0
        vertical[mask] = 0
        divergence = (np.roll(horizontal, 1, 1) - horizontal) + (np.roll(vertical, 1, 0) - vertical)
        value = np.fft.ifft2(
            (numerator + beta * np.fft.fft2(divergence, axes=(0, 1))) /
            (1 + beta * otf)[..., None], axes=(0, 1)).real
        beta *= 2
    return (value.clip(0, 1) * 255 + 0.5).astype(np.uint8)
