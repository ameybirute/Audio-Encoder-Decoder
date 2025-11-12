import streamlit as st
import wave
import numpy as np
import io
from scipy.signal import convolve

st.set_page_config(page_title="Audio Steganography")
st.title("Audio Steganography App")
st.write("Hide and reveal secret messages inside .wav files using different techniques.")


tab1, tab2 = st.tabs(["Encode Message", "Decode Message"])


with tab1:
    st.subheader("Hide Your Secret Message")

    uploaded_file = st.file_uploader("Upload a .wav file", type=["wav"], key="encode_upload")
    st.markdown(
        """
        [Download sample audio](https://s3.amazonaws.com/citizen-dj-assets.labs.loc.gov/audio/samplepacks/loc-fma/Ice-Cream-with-you_fma-164281_001_00-00-00.wav)
        """
    )

    message = st.text_input("Enter your secret message")
    technique = st.selectbox("Select Steganography Technique", ["LSB",])
    # technique = st.selectbox("Select Steganography Technique", ["LSB", "Echo Hiding"])

    
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

    
    # def encode_echo(audio_bytes, message, delay=200, attenuation=0.6):
    #     with wave.open(io.BytesIO(audio_bytes), 'rb') as audio:
    #         params = audio.getparams()
    #         framerate = audio.getframerate()
    #         frames = np.frombuffer(audio.readframes(audio.getnframes()), dtype=np.int16)

        
    #     message_bits = ''.join([format(ord(c), '08b') for c in message + "###"])

        
    #     direct = np.zeros(delay + 1)
    #     direct[0] = 1.0
    #     echo = np.zeros(delay + 1)
    #     echo[0] = 1.0
    #     echo[-1] = attenuation

        
    #     output = np.copy(frames)
    #     for i, bit in enumerate(message_bits):
    #         start = i * delay
    #         if start + delay < len(output):
    #             if bit == '1':
    #                 segment = frames[start:start + delay + 1]
    #                 output[start:start + delay + 1] = convolve(segment, echo, mode='same')[:len(segment)]
    #             else:
    #                 segment = frames[start:start + delay + 1]
    #                 output[start:start + delay + 1] = convolve(segment, direct, mode='same')[:len(segment)]

        # output = np.int16(output)

        # stego_audio = io.BytesIO()
        # with wave.open(stego_audio, 'wb') as new_audio:
        #     new_audio.setparams(params)
        #     new_audio.writeframes(output.tobytes())
        # stego_audio.seek(0)
        # return stego_audio

    if uploaded_file and message:
        if st.button("Encode Message"):
            audio_bytes = uploaded_file.read()
            if technique == "LSB":
                stego_audio = encode_lsb(audio_bytes, message)
            # else:
            #     stego_audio = encode_echo(audio_bytes, message)

            if stego_audio:
                st.success(f"Message successfully hidden using {technique} technique!")
                st.download_button(
                    label="Download Stego Audio",
                    data=stego_audio,
                    file_name=f"stego_{technique.lower()}.wav",
                    mime="audio/wav"
                )


with tab2:
    st.subheader("Reveal Hidden Message")

    stego_file = st.file_uploader("Upload the stego .wav file to decode", type=["wav"], key="decode_upload")
    decode_tech = st.selectbox("Select Decoding Technique", ["LSB"], key="decode_tech")
    # decode_tech = st.selectbox("Select Decoding Technique", ["LSB", "Echo Hiding"], key="decode_tech")


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


    # def decode_echo_placeholder():
    #     st.info("Echo decoding is not implemented because it requires advanced signal processing (autocorrelation or cepstrum analysis) to detect embedded echo delays.")
    #     st.write("In research contexts, echo decoding involves identifying delay patterns corresponding to binary 0 and 1 values by analyzing the waveform structure.")
    #     return None


    if stego_file:
        if st.button("Decode Message"):
            if decode_tech == "LSB":
                hidden_message = decode_lsb(stego_file.read())
                st.success("Message decoded successfully!")
                st.code(hidden_message)
            # else:
            #     decode_echo_placeholder()

