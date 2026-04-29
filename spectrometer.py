"""
spectrometer.py
设备驱动封装 — 海洋光学 USB2000+
"""
import threading
import numpy as np

try:
    import seabreeze
    seabreeze.use('cseabreeze')
    from seabreeze.spectrometers import Spectrometer
    SEABREEZE_AVAILABLE = True
except ImportError:
    SEABREEZE_AVAILABLE = False


class MockSpectrometer:
    """模拟设备，用于无硬件时测试"""
    def __init__(self):
        self._wl = np.linspace(340, 1000, 2048)
        self._int_time = 100000
        self.model = 'USB2000+ (模拟模式)'

    def integration_time_micros(self, us):
        self._int_time = us

    def wavelengths(self):
        return self._wl

    def intensities(self):
        t = self._int_time / 100000
        noise = np.random.normal(0, 50, len(self._wl))
        peak1 = 15000 * t * np.exp(-((self._wl - 550) ** 2) / (2 * 30 ** 2))
        peak2 = 8000  * t * np.exp(-((self._wl - 650) ** 2) / (2 * 20 ** 2))
        base  = 500   * t + noise
        return np.clip(peak1 + peak2 + base, 0, 65535)


class SpectrometerController:
    """统一封装 USB2000+ 操作"""

    # USB2000+ 硬件限制
    INT_TIME_MIN_US = 1000       # 1 ms
    INT_TIME_MAX_US = 65000000   # 65 s

    def __init__(self):
        self.spec = None
        self.lock = threading.Lock()
        self.dark = None
        self.reference = None
        self.integration_time_us = 100000  # 默认 100 ms
        self.connected = False

    def connect(self, mock=False):
        """连接设备，mock=True 时使用模拟器"""
        if mock or not SEABREEZE_AVAILABLE:
            self.spec = MockSpectrometer()
        else:
            self.spec = Spectrometer.from_first_available()
        self.spec.integration_time_micros(self.integration_time_us)
        self.connected = True
        return self.spec.model

    def set_integration_time(self, ms: float):
        """设置积分时间 (毫秒)"""
        us = int(ms * 1000)
        us = max(self.INT_TIME_MIN_US, min(us, self.INT_TIME_MAX_US))
        self.integration_time_us = us
        with self.lock:
            if self.spec:
                self.spec.integration_time_micros(us)
        return us / 1000  # 返回实际 ms

    def get_spectrum(self, scans_to_average: int = 1):
        """采集光谱，返回 (wavelengths_list, intensities_list)"""
        if not self.connected:
            raise RuntimeError('设备未连接')
        with self.lock:
            wavelengths = self.spec.wavelengths()
            if scans_to_average > 1:
                stacked = [self.spec.intensities() for _ in range(scans_to_average)]
                intensities = np.mean(stacked, axis=0)
            else:
                intensities = self.spec.intensities()
        return wavelengths.tolist(), intensities.tolist()

    def capture_dark(self, scans: int = 3):
        """采集暗背景"""
        _, self.dark = self.get_spectrum(scans)
        return '暗背景采集完成'

    def capture_reference(self, scans: int = 3):
        """采集参考白板"""
        _, self.reference = self.get_spectrum(scans)
        return '参考白板采集完成'

    def get_reflectance(self, scans: int = 1):
        """
        计算反射率
        R(%) = (样品 - 暗) / (参考 - 暗) × 100
        """
        if self.dark is None:
            raise ValueError('请先点击「采集暗背景」')
        if self.reference is None:
            raise ValueError('请先点击「采集参考白板」')

        wl, sample = self.get_spectrum(scans)
        dark = np.array(self.dark)
        ref  = np.array(self.reference)
        smp  = np.array(sample)

        denom = ref - dark
        denom[np.abs(denom) < 1e-9] = 1e-9  # 防除零

        reflectance = np.clip((smp - dark) / denom * 100, 0, 200)
        return wl, reflectance.tolist()

    def get_status(self):
        return {
            'connected': self.connected,
            'model': self.spec.model if self.spec else None,
            'integration_time_ms': self.integration_time_us / 1000,
            'has_dark': self.dark is not None,
            'has_reference': self.reference is not None,
        }
