"""
PESQ (Perceptual Evaluation of Speech Quality) Analysis
Compares LSB and Echo Hiding using PESQ metric only
"""

from scipy.io import wavfile
from scipy import signal
import numpy as np
from pesq import pesq

def convert_to_mono(audio):
    """Convert stereo to mono by averaging channels"""
    if len(audio.shape) == 2:
        # Stereo - average the two channels
        return audio.mean(axis=1).astype(np.int16)
    else:
        # Already mono
        return audio

def resample_audio(audio, orig_rate, target_rate=16000):
    """Resample audio to target rate for PESQ"""
    if orig_rate == target_rate:
        return audio, target_rate
    
    # Calculate number of samples for target rate
    num_samples = int(len(audio) * target_rate / orig_rate)
    
    # Resample
    resampled = signal.resample(audio, num_samples)
    
    return resampled.astype(np.int16), target_rate

# Read audio files
rate_orig, original = wavfile.read('SampleOne.wav')
rate_lsb, stego_lsb = wavfile.read('stego_lsb.wav')
rate_echo, stego_echo = wavfile.read('stego_echo.wav')

print(f"Original sample rate: {rate_orig} Hz")
print(f"Original shape: {original.shape}")

# Convert to mono if stereo
original = convert_to_mono(original)
stego_lsb = convert_to_mono(stego_lsb)
stego_echo = convert_to_mono(stego_echo)

print(f"After mono conversion: {original.shape}")

# Resample to 16000 Hz if needed
target_rate = 16000 if rate_orig != 8000 else 8000

if rate_orig not in [8000, 16000]:
    print(f"Resampling from {rate_orig} Hz to {target_rate} Hz...")
    original, rate_orig = resample_audio(original, rate_orig, target_rate)
    stego_lsb, _ = resample_audio(stego_lsb, rate_lsb, target_rate)
    stego_echo, _ = resample_audio(stego_echo, rate_echo, target_rate)

# Ensure same length
min_len = min(len(original), len(stego_lsb), len(stego_echo))
original = original[:min_len]
stego_lsb = stego_lsb[:min_len]
stego_echo = stego_echo[:min_len]

# Calculate PESQ
print("Calculating PESQ...")
mode = 'wb' if rate_orig == 16000 else 'nb'
pesq_lsb = pesq(rate_orig, original, stego_lsb, mode)
pesq_echo = pesq(rate_orig, original, stego_echo, mode)

# Display results
print("\n" + "=" * 50)
print("PESQ Results")
print("=" * 50)
print(f"LSB:          {pesq_lsb:.3f}")
print(f"Echo Hiding:  {pesq_echo:.3f}")
print()
print("PESQ Range: -0.5 to 4.5 (higher = better)")
print("  >4.0 = Excellent")
print("  3.0-4.0 = Good")
print("  <3.0 = Poor")
print("=" * 50)