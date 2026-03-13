import librosa
import numpy as np
import logging

logger = logging.getLogger(__name__)

def analyze_audio_fluency_sync(audio_path: str, word_count: int) -> dict | None:
    """
    Synchronously analyze audio using librosa to extract fluency metrics.
    Note: This is CPU-intensive and should be run in a thread pool (e.g. asyncio.to_thread).
    """
    try:
        # Load audio (downsample to 16kHz for speed, convert to mono)
        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        
        if len(y) == 0:
            return None

        total_duration = librosa.get_duration(y=y, sr=sr)
        
        # Split audio into non-silent intervals. top_db=30 means anything 30dB below max is silence.
        # This is a basic Voice Activity Detection (VAD).
        intervals = librosa.effects.split(y, top_db=30)
        
        speaking_duration = 0.0
        for start_i, end_i in intervals:
            speaking_duration += (end_i - start_i) / sr
            
        silence_duration = total_duration - speaking_duration
        
        # Calculate pauses
        pause_count = 0
        long_pause_count = 0
        long_pause_threshold = 1.0  # seconds
        
        for i in range(1, len(intervals)):
            prev_end = intervals[i-1][1]
            curr_start = intervals[i][0]
            pause_dur = (curr_start - prev_end) / sr
            
            if pause_dur >= 0.3:  # 300ms is a typical noticeable pause
                pause_count += 1
            if pause_dur >= long_pause_threshold:
                long_pause_count += 1
                
        # Calculate Words Per Minute (WPM)
        wpm = round((word_count / total_duration) * 60) if total_duration > 0 and word_count > 0 else 0
        
        # Speaking vs Silence Ratio
        speaking_ratio = speaking_duration / total_duration if total_duration > 0 else 0
        
        return {
            "total_duration_sec": round(total_duration, 2),
            "speaking_duration_sec": round(speaking_duration, 2),
            "silence_duration_sec": round(silence_duration, 2),
            "speaking_ratio": round(speaking_ratio, 2),
            "pause_count": pause_count,
            "long_pause_count": long_pause_count,
            "wpm": wpm
        }
        
    except Exception as e:
        logger.error(f"Error in acoustic analysis: {e}")
        return None
