"""
storage.py
数据保存模块 — CSV / HDF5
"""
import os
import csv
from datetime import datetime

SAVE_DIR = os.path.join(os.path.dirname(__file__), 'spectrometer_data')
os.makedirs(SAVE_DIR, exist_ok=True)


def _timestamp():
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def save_csv(wavelengths, data, label: str, note: str = '') -> str:
    """保存为 CSV，返回文件路径"""
    ts = _timestamp()
    filename = f'{label}_{ts}.csv'
    path = os.path.join(SAVE_DIR, filename)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['# 海洋光学 USB2000+ 数据'])
        writer.writerow(['# 时间', ts])
        writer.writerow(['# 备注', note])
        writer.writerow(['wavelength_nm', label])
        for wl, val in zip(wavelengths, data):
            writer.writerow([f'{wl:.4f}', f'{val:.4f}'])
    return path


def save_hdf5(wavelengths, data, label: str, note: str = '') -> str:
    """保存为 HDF5，返回文件路径"""
    try:
        import h5py
        import numpy as np
    except ImportError:
        raise ImportError('请先安装 h5py: pip install h5py')

    ts = _timestamp()
    filename = f'{label}_{ts}.h5'
    path = os.path.join(SAVE_DIR, filename)
    with h5py.File(path, 'w') as f:
        f.attrs['instrument'] = 'Ocean Optics USB2000+'
        f.attrs['timestamp'] = ts
        f.attrs['note'] = note
        f.create_dataset('wavelengths', data=np.array(wavelengths),
                         compression='gzip')
        f.create_dataset(label, data=np.array(data),
                         compression='gzip')
    return path


def list_saved_files() -> list:
    """列出已保存的文件"""
    files = []
    for fname in sorted(os.listdir(SAVE_DIR), reverse=True):
        fpath = os.path.join(SAVE_DIR, fname)
        size = os.path.getsize(fpath)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime('%Y-%m-%d %H:%M:%S')
        files.append({'name': fname, 'size': size, 'modified': mtime})
    return files
