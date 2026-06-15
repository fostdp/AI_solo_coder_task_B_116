from __future__ import annotations

import math
from typing import List, Tuple


class WaveletDenoiser:
    """Daubechies-4 (db4) 小波软阈值去噪器，用于消除视觉检测信号噪声"""

    DB4_DECOMPOSE = [0.4829629131445341, 0.8365163037378079, 0.2241438680420134, -0.1294095225512604]
    DB4_RECONSTRUCT = [-0.1294095225512604, -0.2241438680420134, 0.8365163037378079, -0.4829629131445341]

    @staticmethod
    def _next_pow2(n: int) -> int:
        return 1 if n == 0 else 2 ** math.ceil(math.log2(n))

    @classmethod
    def dwt(cls, signal: List[float]) -> Tuple[List[float], List[float]]:
        """一维离散小波分解（db4），返回近似系数cA和细节系数cD"""
        n = len(signal)
        padded = signal + [0.0] * (cls._next_pow2(n) - n) if n & (n - 1) else list(signal)
        L = len(padded)
        cA, cD = [0.0] * (L // 2), [0.0] * (L // 2)
        h0, h1, h2, h3 = cls.DB4_DECOMPOSE
        for i in range(L // 2):
            j = 2 * i
            cA[i] = h0 * padded[j] + h1 * padded[(j + 1) % L] + h2 * padded[(j + 2) % L] + h3 * padded[(j + 3) % L]
            cD[i] = h3 * padded[j] - h2 * padded[(j + 1) % L] + h1 * padded[(j + 2) % L] - h0 * padded[(j + 3) % L]
        return cA, cD

    @classmethod
    def idwt(cls, cA: List[float], cD: List[float], original_len: int) -> List[float]:
        """一维离散小波重构（Mallat算法的上采样+卷积合成）"""
        n = len(cA)
        L = n * 2
        padded = [0.0] * L
        h0, h1, h2, h3 = cls.DB4_DECOMPOSE
        g0, g1, g2, g3 = h3, -h2, h1, -h0
        for i in range(n):
            k = 2 * i
            padded[k] += g0 * cA[i] + g3 * cD[i]
            if k + 1 < L:
                padded[k + 1] += g1 * cA[i] + g2 * cD[i]
            if k + 2 < L:
                padded[k + 2] += g2 * cA[i] - g1 * cD[i]
            if k + 3 < L:
                padded[k + 3] += g3 * cA[i] - g0 * cD[i]
        return padded[:original_len] if original_len <= len(padded) else padded

    @classmethod
    def universal_threshold(cls, detail_coeffs: List[float], n: int) -> float:
        """Donoho-Johnstone通用阈值 σ·√(2·ln n)"""
        if len(detail_coeffs) == 0:
            return 0.0
        mean_val = sum(detail_coeffs) / len(detail_coeffs)
        deviations = [abs(x - mean_val) for x in detail_coeffs]
        deviations.sort()
        median = deviations[len(deviations) // 2]
        sigma = 1.4826 * median
        return sigma * math.sqrt(2 * math.log(max(n, 2)))

    @staticmethod
    def soft_threshold(x: float, threshold: float) -> float:
        """软阈值函数：sign(x)·max(|x|-T, 0)"""
        if x > threshold:
            return x - threshold
        elif x < -threshold:
            return x + threshold
        return 0.0

    @classmethod
    def denoise_signal(cls, signal: List[float], levels: int = 3) -> List[float]:
        """
        多层小波分解+软阈值+重构完成去噪
        :param signal: 含噪信号序列
        :param levels: 分解层数（1-4）
        :return: 去噪后的信号
        """
        if not signal:
            return []
        if len(signal) < 4:
            return list(signal)
        levels = max(1, min(levels, 4))
        n = len(signal)
        coeffs_stack = []
        current = list(signal)
        for _ in range(levels):
            if len(current) < 4:
                break
            cA, cD = cls.dwt(current)
            coeffs_stack.append(cD)
            current = cA
        for i, cD in enumerate(reversed(coeffs_stack)):
            thr = cls.universal_threshold(cD, n)
            cD_thr = [cls.soft_threshold(v, thr) for v in cD]
            current = cls.idwt(current, cD_thr, len(current) * 2)
        return current[:n]

    @classmethod
    def denoise_single_value(cls, buffer: List[float], new_value: float, window: int = 32, levels: int = 3) -> float:
        """
        滑动窗口的单值去噪：维护时间窗口，返回当前时刻去噪估计
        :param buffer: 历史信号缓冲（会被in-place更新）
        :param new_value: 当前新观测值
        :param window: 窗口长度
        :param levels: 小波分解层数
        :return: 去噪后的当前值
        """
        buffer.append(new_value)
        if len(buffer) > window:
            buffer.pop(0)
        if len(buffer) < 8:
            return new_value
        denoised = cls.denoise_signal(buffer, levels)
        return denoised[-1]
