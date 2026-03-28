# %%
import numpy as np
import matplotlib.pyplot as plt
import scipy.io
from scipy import signal
import os

def read_loc_file(filepath):
    """
    手动解析 .loc 文件提取通道名称
    .loc 文件每行有四列：序号、角度、半径、通道标签
    """
    ch_names = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 4:
                # 提取第 4 列（索引为 3）作为通道名称
                ch_names.append(parts[3])
    return np.array(ch_names)

def load_rsvp_data(data_path, montage_path):
    """
    加载指定受试者的 RSVP 原始数据及通道信息
    """
    mat_file = data_path
    print(f"Loading data from: {mat_file}")
    
    # 1. 加载 MAT 文件
    eeg_mat = scipy.io.loadmat(mat_file)
    eeg_data1 = eeg_mat['EEGdata1']          # Block 1 的连续脑电数据
    class_labels = eeg_mat['class_labels']   # 类别标签 (1: 目标, 2: 非目标)
    triggers = eeg_mat['trigger_positions']  # 刺激发生的采样点位置
    
    # 2. 手动读取通道名称
    ch_names = read_loc_file(montage_path)
    
    return eeg_data1, class_labels, triggers, ch_names

def preprocess_and_epoch(raw_data, labels, triggers, sfreq, tmin=-0.1, tmax=1.0):
    """
    对连续脑电进行滤波、分段提取目标 ERP
    """
    # 1. 带通滤波 (0.1Hz - 15Hz, 4阶 Butterworth 零相位滤波)
    order = 4
    lowcut, highcut = 0.1, 15.0
    sos = signal.butter(order, [lowcut, highcut], btype='bandpass', fs=sfreq, output='sos')
    filtered_data = signal.sosfiltfilt(sos, raw_data)
    print("Filtering completed.")

    # 2. 分段 (Epoching) 准备
    pre_samples = int(abs(tmin) * sfreq)
    post_samples = int(tmax * sfreq)
    epoch_len = pre_samples + post_samples
    
    # 仅提取 Block 1 (第 0 行) 的目标触发点 (标签为 1)
    target_idx = triggers[0, labels[0, :] == 1]
    
    epochs = []
    # 3. 截取数据片段
    for s in target_idx:
        # 确保截取窗口不超出数据边界
        if s - pre_samples >= 0 and s + post_samples <= filtered_data.shape[1]:
            epochs.append(filtered_data[:, s - pre_samples : s + post_samples])
            
    epochs = np.array(epochs)
    print(f"Extracted {len(epochs)} target epochs.")
    return epochs, pre_samples

def apply_reference_and_baseline(epochs, ch_names, ref_chans, pre_samples):
    """
    应用自定义重参考及基线校正
    """
    # 1. 重参考 (Re-referencing)
    ref_idx = [i for i, name in enumerate(ch_names) if name in ref_chans]
    ref_mean = epochs[:, ref_idx, :].mean(axis=1, keepdims=True)
    epochs_ref = epochs - ref_mean
    
    # 2. 去基线 (Baseline Correction)
    baseline_mean = epochs_ref[:, :, 0:pre_samples].mean(axis=-1, keepdims=True)
    epochs_final = epochs_ref - baseline_mean
    
    print("Re-referencing and baseline correction completed.")
    return epochs_final

# ==========================================
# 主程序执行逻辑
# ==========================================
if __name__ == "__main__":
    # --- 1. 参数设置 ---
    # 请同学们修改为自己电脑上的实际路径
    DATA_DIR = r".\sub7A.mat"
    MONTAGE_FILE = r".\64-channels.loc"
    SFREQ = 250.0  # 数据采样率
    
    # --- 2. 加载数据 ---
    eeg_data, labels, triggers, ch_names = load_rsvp_data(DATA_DIR, MONTAGE_FILE)
    
    # --- 3. 滤波与分段 ---
    epochs, pre_samples = preprocess_and_epoch(eeg_data, labels, triggers, sfreq=SFREQ, tmin=-0.1, tmax=1.0)
    
    # --- 4. 重参考与去基线 ---
    epochs_processed = apply_reference_and_baseline(epochs, ch_names, ref_chans=['TP7', 'TP8'], pre_samples=pre_samples)
    
    # --- 5. 结果可视化：绘制叠加平均后的 Fz 导联 ERP 波形 ---
    mean_erp = epochs_processed.mean(axis=0) 
    time_axis = np.linspace(-0.1, 1.0, mean_erp.shape[1], endpoint=False)
    
    plt.figure(figsize=(10, 6))
    
    # 定位 Fz 导联
    fz_idx = np.where(ch_names == 'FZ')[0][0]
    
    # 绘制 Fz 通道
    plt.plot(time_axis, mean_erp[fz_idx, :], 'b', label='Fz Channel', linewidth=2)
        
    plt.title('Grand Average ERP for Target Images at Fz (Subject 7, Block 1)')
    plt.xlabel('Time (s) relative to stimulus onset')
    plt.ylabel('Amplitude (μV)')
    
    plt.axvline(0, color='gray', linestyle='--', alpha=0.7)
    plt.axhline(0, color='gray', linestyle='--', alpha=0.7)
    
    plt.legend()
    plt.grid(True)
    plt.show()
#%%