import streamlit as st
import wave
import numpy as np
import io
from scipy.fftpack import fft, ifft


def read_wav_bytes(audio_bytes):
    """Read WAV file from bytes and return samples and parameters"""
    with wave.open(io.BytesIO(audio_bytes), "rb") as audio:
        params = audio.getparams()
        frames = audio.readframes(audio.getnframes())
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    return samples, params


def write_wav_bytes(samples, params):
    """Write samples to WAV format bytes"""
    samples = np.clip(samples, -32768, 32767)
    samples = np.int16(samples)

    out = io.BytesIO()
    with wave.open(out, "wb") as audio:
        audio.setparams(params)
        audio.writeframes(samples.tobytes())

    out.seek(0)
    return out


def encode_lsb(audio_bytes, message):
    """Encode message using LSB technique"""
    samples, params = read_wav_bytes(audio_bytes)
    samples = samples.astype(np.int16)

    message += "###"
    bits = "".join(format(ord(c), "08b") for c in message)

    flat = samples.view(np.uint16)

    if len(bits) > len(flat):
        return None

    for i, b in enumerate(bits):
        flat[i] = (flat[i] & 0xFFFE) | int(b)

    return write_wav_bytes(flat.view(np.int16), params)


def decode_lsb(stego_bytes):
    """Decode message using LSB technique"""
    samples, _ = read_wav_bytes(stego_bytes)
    samples = samples.astype(np.int16).view(np.uint16)

    bits = [str(s & 1) for s in samples]
    chars = []

    for i in range(0, len(bits), 8):
        byte = bits[i : i + 8]
        if len(byte) < 8:
            break

        char_val = int("".join(byte), 2)

        if char_val == 0:
            break

        chars.append(chr(char_val))

        if "".join(chars).endswith("###"):
            return "".join(chars)[:-3]

    return "No hidden message found"


def encode_echo_simple(audio_bytes, message, d0=200, d1=400, alpha=0.5):
    """
    Proper echo hiding: adds delayed attenuated copies
    Requires original audio for decoding
    """
    samples, params = read_wav_bytes(audio_bytes)

    message += "###"
    bits = "".join(format(ord(c), "08b") for c in message)

    chunk_size = 8192
    max_delay = max(d0, d1)

    if len(bits) * chunk_size + max_delay > len(samples):
        return None

    out = samples.copy()

    for i, bit in enumerate(bits):
        start = i * chunk_size
        end = min(start + chunk_size, len(samples) - max_delay)

        if end <= start:
            break

        delay = d1 if bit == "1" else d0

        chunk = samples[start:end]
        echo_start = start + delay
        echo_end = echo_start + len(chunk)

        if echo_end <= len(out):
            out[echo_start:echo_end] += alpha * chunk

    return write_wav_bytes(out, params)


def decode_echo_simple(original_bytes, stego_bytes, d0=200, d1=400):
    """
    Decode using difference between original and stego
    Much more reliable with original audio
    """
    original, _ = read_wav_bytes(original_bytes)
    stego, _ = read_wav_bytes(stego_bytes)

    chunk_size = 8192
    max_delay = max(d0, d1)
    num_chunks = (min(len(original), len(stego)) - max_delay) // chunk_size

    bits = []
    debug_info = []

    for i in range(num_chunks):
        start = i * chunk_size
        end = start + chunk_size

        if end + max_delay > min(len(original), len(stego)):
            break

        echo = stego[start : end + max_delay] - original[start : end + max_delay]
        orig_chunk = original[start:end]

        echo_d0 = echo[d0 : d0 + len(orig_chunk)]
        echo_d1 = echo[d1 : d1 + len(orig_chunk)]

        corr_d0 = np.abs(np.sum(orig_chunk * echo_d0))
        corr_d1 = np.abs(np.sum(orig_chunk * echo_d1))

        bit = "1" if corr_d1 > corr_d0 else "0"
        bits.append(bit)

        debug_info.append(
            f"Chunk {i}: corr_d0={corr_d0:.2f}, corr_d1={corr_d1:.2f}, bit={bit}"
        )

    chars = []

    for i in range(0, len(bits), 8):
        byte = bits[i : i + 8]

        if len(byte) < 8:
            break

        char_val = int("".join(byte), 2)

        if char_val == 0 or char_val > 127:
            break

        try:
            chars.append(chr(char_val))

            if "".join(chars).endswith("###"):
                return "".join(chars)[:-3], debug_info, bits
        except:
            continue

    return "No hidden message found", debug_info, bits


st.set_page_config(page_title="Audio Steganography", layout="centered")
st.title("Audio Steganography System")

tab1, tab2 = st.tabs(["Encode", "Decode"])


with tab1:
    st.subheader("Encode Secret Message")

    audio_file = st.file_uploader(
        "Upload WAV Audio File", type=["wav"], key="enc_audio"
    )

    message = st.text_area(
        "Secret Message",
        placeholder="Enter your secret message here...",
    )

    technique = st.selectbox(
        "Steganography Technique",
        ["LSB", "Echo Hiding"],
        key="enc_tech",
    )

    if technique == "Echo Hiding":
        d0 = st.slider("Delay for bit 0 (samples)", 100, 500, 200, 50)
        d1 = st.slider("Delay for bit 1 (samples)", 100, 500, 400, 50)
        alpha = st.slider("Echo Strength", 0.3, 0.8, 0.5, 0.1)

    if audio_file and message:
        if st.button("Encode Message", type="primary"):
            with st.spinner("Encoding message..."):
                audio_bytes = audio_file.read()

                try:
                    if technique == "LSB":
                        stego = encode_lsb(audio_bytes, message)
                    else:
                        stego = encode_echo_simple(
                            audio_bytes, message, d0, d1, alpha
                        )

                    if stego:
                        st.success("Encoding successful")

                        st.download_button(
                            "Download Stego Audio",
                            stego,
                            file_name="stego_audio.wav",
                            mime="audio/wav",
                        )

                        if technique == "Echo Hiding":
                            st.warning(
                                "Keep your original audio file! You'll need it to decode the message."
                            )
                    else:
                        st.error("Message is too large for this audio file")

                except Exception as e:
                    st.error(f"Error during encoding: {str(e)}")


with tab2:
    st.subheader("Decode Hidden Message")

    technique = st.selectbox(
        "Steganography Technique",
        ["LSB", "Echo Hiding"],
        key="dec_tech",
    )

    if technique == "LSB":
        stego_file = st.file_uploader(
            "Upload Stego Audio", type=["wav"], key="dec_lsb"
        )

        if stego_file:
            if st.button("Decode Message", type="primary"):
                with st.spinner("Decoding message..."):
                    try:
                        result = decode_lsb(stego_file.read())

                        st.success("Decoding complete")
                        st.markdown("### Decoded Message:")
                        st.code(result, language=None)

                    except Exception as e:
                        st.error(f"Error during decoding: {str(e)}")

    else:
        col1, col2 = st.columns(2)

        with col1:
            orig_file = st.file_uploader(
                "Upload Original Audio", type=["wav"], key="dec_orig"
            )

        with col2:
            stego_file = st.file_uploader(
                "Upload Stego Audio", type=["wav"], key="dec_stego"
            )

        d0_dec = st.slider(
            "Delay for bit 0 (samples)",
            100,
            500,
            200,
            50,
            key="dec_d0",
        )

        d1_dec = st.slider(
            "Delay for bit 1 (samples)",
            100,
            500,
            400,
            50,
            key="dec_d1",
        )

        if orig_file and stego_file:
            if st.button("Decode Message", type="primary"):
                with st.spinner("Decoding message..."):
                    try:
                        result, debug_info, bits = decode_echo_simple(
                            orig_file.read(),
                            stego_file.read(),
                            d0_dec,
                            d1_dec,
                        )

                        st.success("Decoding complete")
                        st.markdown("### Decoded Message:")
                        st.code(result, language=None)

                    except Exception as e:
                        st.error(f"Error during decoding: {str(e)}")
