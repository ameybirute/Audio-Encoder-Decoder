import numpy as np
from scipy.io import wavfile
from pystoi import stoi

fs, original = wavfile.read("SampleOne.wav")
fs1, stego_lsb = wavfile.read("stego_lsb.wav")
fs2, stego_echo = wavfile.read("stego_echo.wav")

if fs != fs1 or fs != fs2:
    raise ValueError("Sampling rates do not match")

original = original.astype(np.float32)
stego_lsb = stego_lsb.astype(np.float32)
stego_echo = stego_echo.astype(np.float32)

if original.ndim > 1:
    original = np.mean(original, axis=1)
if stego_lsb.ndim > 1:
    stego_lsb = np.mean(stego_lsb, axis=1)
if stego_echo.ndim > 1:
    stego_echo = np.mean(stego_echo, axis=1)

min_len = min(len(original), len(stego_lsb), len(stego_echo))
original = original[:min_len]
stego_lsb = stego_lsb[:min_len]
stego_echo = stego_echo[:min_len]

stoi_lsb = stoi(original, stego_lsb, fs, extended=False)
stoi_echo = stoi(original, stego_echo, fs, extended=False)

print("=== STOI Results ===")
print(f"LSB STOI:  {stoi_lsb:.4f}")
print(f"Echo STOI: {stoi_echo:.4f}")
