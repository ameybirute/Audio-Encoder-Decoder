import numpy as np
from scipy.io import wavfile

fs, original = wavfile.read('SampleOne.wav')
_, stego_lsb = wavfile.read('stego_lsb.wav')
_, stego_echo = wavfile.read('stego_echo.wav')

original = original.astype(np.float64)
stego_lsb = stego_lsb.astype(np.float64)
stego_echo = stego_echo.astype(np.float64)

min_len = min(len(original), len(stego_lsb), len(stego_echo))
original = original[:min_len]
stego_lsb = stego_lsb[:min_len]
stego_echo = stego_echo[:min_len]

def calculate_snr(original, stego):
    signal_power = np.sum(original ** 2)
    noise_power = np.sum((original - stego) ** 2)
    
    if noise_power == 0:
        return float('inf')
    
    return 10 * np.log10(signal_power / noise_power)

snr_lsb = calculate_snr(original, stego_lsb)
snr_echo = calculate_snr(original, stego_echo)

print(f"LSB Steganography SNR: {snr_lsb:.2f} dB")
print(f"Echo Hiding SNR: {snr_echo:.2f} dB")
