"""Generate audio files in the formats browsers and WhatsApp produce, using PyAV only
(no system ffmpeg). Used by tests; there is no recorded speech in this repository."""
import av
import numpy as np

FORMATS = {   # extension: (container format, codec, sample rate)
    "wav": ("wav", "pcm_s16le", 16000),
    "webm": ("webm", "libopus", 48000),     # Chrome / Firefox MediaRecorder
    "ogg": ("ogg", "libopus", 48000),       # WhatsApp voice note (OGG/Opus)
    "m4a": ("ipod", "aac", 44100),
    "mp4": ("mp4", "aac", 44100),           # Safari MediaRecorder
    "mp3": ("mp3", "libmp3lame", 44100),
}


def tone(seconds, freq=440.0, sr=16000, amp=0.3):
    t = np.arange(int(seconds * sr)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def silence(seconds, sr=16000):
    return np.zeros(int(seconds * sr), dtype=np.float32)


def write(path, samples, sr=16000):
    ext = str(path).rsplit(".", 1)[-1]
    fmt, codec, out_sr = FORMATS[ext]
    with av.open(str(path), "w", format=fmt) as c:
        st = c.add_stream(codec, rate=out_sr)
        st.layout = "mono"
        frame_fmt = st.codec_context.format.name if st.codec_context.format else "s16"
        res = av.AudioResampler(format=frame_fmt, layout="mono", rate=out_sr)
        pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16).reshape(1, -1)
        for i in range(0, pcm.shape[1], 1024):
            fr = av.AudioFrame.from_ndarray(np.ascontiguousarray(pcm[:, i:i + 1024]), format="s16", layout="mono")
            fr.sample_rate = sr
            for f in res.resample(fr):
                for p in st.encode(f):
                    c.mux(p)
        for f in res.resample(None):
            for p in st.encode(f):
                c.mux(p)
        for p in st.encode(None):
            c.mux(p)
    return path
