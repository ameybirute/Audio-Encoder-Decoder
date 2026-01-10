import streamlit as st
import wave
import numpy as np
import io
from scipy.signal import convolve
from pystoi.stoi import stoi


# =========================
# Helper Functions
# =========================

def wav_bytes_to_signal(audio_bytes):
    with wave.open(io.BytesIO(audio_bytes), 'rb') as audio:
        framerate = audio.getframerate()
        frames = audio.readframes(audio.getnframes())
        signal = np.frombuffer(frames, dtype=np.int16)

        # Normalize to [-1, 1]
        signal = signal.astype(np.float32) / 32768.0

    return signal, framerate


def compute_snr(original, stego):
    min_len = min(len(original), len(stego))
    original = original[:min_len]
    stego = stego[:min_len]

    noise = original - stego
    signal_power = np.sum(original ** 2)
    noise_power = np.sum(noise ** 2)

    if noise_power == 0:
        return float('inf')

    return 10 * np.log10(signal_power / noise_power)


def calculate_stoi(original_bytes, stego_bytes):
    orig_signal, fs1 = wav_bytes_to_signal(original_bytes)
    stego_signal, fs2 = wav_bytes_to_signal(stego_bytes)

    if fs1 != fs2:
        st.error("Sample rates do not match.")
        return None

    min_len = min(len(orig_signal), len(stego_signal))
    orig_signal = orig_signal[:min_len]
    stego_signal = stego_signal[:min_len]

    return stoi(orig_signal, stego_signal, fs1, extended=False)


def encode_lsb(audio_bytes, message):
    with wave.open(io.BytesIO(audio_bytes), mode='rb') as audio:
        frame_bytes = bytearray(list(audio.readframes(audio.getnframes())))

    message += "###"
    message_bits = ''.join([format(ord(c), '08b') for c in message])

    if len(message_bits) > len(frame_bytes):
        st.error("Message too large to hide in this audio file!")
        return None

    for i in range(len(message_bits)):
        frame_bytes[i] = (frame_bytes[i] & 254) | int(message_bits[i])

    stego_audio = io.BytesIO()
    with wave.open(stego_audio, 'wb') as new_audio:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as original:
            new_audio.setparams(original.getparams())
            new_audio.writeframes(frame_bytes)

    stego_audio.seek(0)
    return stego_audio


def encode_echo(audio_bytes, message, delay=200, attenuation=0.6):
    with wave.open(io.BytesIO(audio_bytes), 'rb') as audio:
        params = audio.getparams()
        frames = np.frombuffer(audio.readframes(audio.getnframes()), dtype=np.int16)

    message_bits = ''.join([format(ord(c), '08b') for c in message + "###"])

    direct = np.zeros(delay + 1)
    direct[0] = 1.0

    echo = np.zeros(delay + 1)
    echo[0] = 1.0
    echo[-1] = attenuation

    output = np.copy(frames)

    for i, bit in enumerate(message_bits):
        start = i * delay
        if start + delay < len(output):
            segment = frames[start:start + delay + 1]
            kernel = echo if bit == '1' else direct
            output[start:start + delay + 1] = convolve(
                segment, kernel, mode='same'
            )[:len(segment)]

    output = np.int16(output)

    stego_audio = io.BytesIO()
    with wave.open(stego_audio, 'wb') as new_audio:
        new_audio.setparams(params)
        new_audio.writeframes(output.tobytes())

    stego_audio.seek(0)
    return stego_audio


def decode_lsb(stego_bytes):
    with wave.open(io.BytesIO(stego_bytes), mode='rb') as audio:
        frame_bytes = bytearray(list(audio.readframes(audio.getnframes())))

    extracted_bits = [str(frame_bytes[i] & 1) for i in range(len(frame_bytes))]
    bits_joined = ''.join(extracted_bits)

    chars = [bits_joined[i:i+8] for i in range(0, len(bits_joined), 8)]
    decoded_message = ""

    for c in chars:
        decoded_message += chr(int(c, 2))
        if decoded_message.endswith("###"):
            return decoded_message[:-3]

    return "No hidden message found."


# =========================
# Streamlit UI
# =========================

st.set_page_config(page_title="Audio Steganography")
st.title("Audio Steganography App")
st.write("Hide and reveal secret messages inside .wav files using different techniques.")

tab1, tab2, tab3 = st.tabs(
    ["Encode Message", "Decode Message", "Results & Evaluation"]
)


# =========================
# Encode Tab
# =========================

with tab1:
    st.subheader("Hide Your Secret Message")

    uploaded_file = st.file_uploader("Upload a .wav file", type=["wav"])
    st.markdown(
        "[Download sample audio](https://s3.amazonaws.com/citizen-dj-assets.labs.loc.gov/audio/samplepacks/loc-fma/Ice-Cream-with-you_fma-164281_001_00-00-00.wav)"
    )

    message = st.text_input("Enter your secret message")
    technique = st.selectbox("Select Steganography Technique", ["LSB", "Echo Hiding"])

    if uploaded_file and message:
        if st.button("Encode Message"):
            audio_bytes = uploaded_file.read()

            stego_audio = (
                encode_lsb(audio_bytes, message)
                if technique == "LSB"
                else encode_echo(audio_bytes, message)
            )

            if stego_audio:
                st.session_state["original_audio"] = audio_bytes
                st.session_state["stego_audio"] = stego_audio.getvalue()

                st.success(f"Message successfully hidden using {technique} technique!")
                st.download_button(
                    "Download Stego Audio",
                    stego_audio,
                    file_name=f"stego_{technique.lower()}.wav",
                    mime="audio/wav"
                )


# =========================
# Decode Tab
# =========================

with tab2:
    st.subheader("Reveal Hidden Message")

    stego_file = st.file_uploader("Upload the stego .wav file to decode", type=["wav"])

    if stego_file:
        if st.button("Decode Message"):
            hidden_message = decode_lsb(stego_file.read())
            st.success("Message decoded successfully!")
            st.code(hidden_message)


# =========================
# Results Tab
# =========================

with tab3:
    st.subheader("Audio Quality Evaluation")

    metric = st.selectbox("Select Evaluation Metric", ["SNR", "STOI"])

    if "original_audio" in st.session_state and "stego_audio" in st.session_state:
        original = st.session_state["original_audio"]
        stego = st.session_state["stego_audio"]

        st.write("### Original Audio")
        st.audio(original)

        st.write("### Stego Audio")
        st.audio(stego)

        if st.button("Evaluate"):
            if metric == "SNR":
                snr_value = compute_snr(
                    *wav_bytes_to_signal(original)[0:1],
                )
                snr_value = compute_snr(
                    wav_bytes_to_signal(original)[0],
                    wav_bytes_to_signal(stego)[0]
                )
                st.metric("SNR (dB)", f"{snr_value:.2f}")

            elif metric == "STOI":
                stoi_value = calculate_stoi(original, stego)
                st.metric("STOI Score", f"{stoi_value:.3f}")
    else:
        st.info("Please encode an audio message first.")
