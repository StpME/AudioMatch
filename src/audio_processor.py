import os
import librosa
import soundfile as sf
import numpy as np
import gc

class AudioProcessor:
    """
    High-level wrapper for audio processing.
    Maxing memory-efficient batch processing to improve stability (and crash debug).
    """
    
    @staticmethod
    def process_batch(file_paths, batch_size=5, callback=None):
        """
        Process audio files in batches to manage memory usage.
        
        Args:
            file_paths: List of audio file paths
            batch_size: Number of files to process at once
            callback: Function to call with progress updates
            
        Returns:
            results: Dictionary mapping filenames to tghe features
        """
        results = {}
        
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i+batch_size]
            
            for idx, path in enumerate(batch):
                try:
                    # Load and extract features
                    y, sr = AudioLoader.load_audio(path)
                    features = FeatureExtractor.extract_features(y, sr)
                    
                    # Store results
                    filename = os.path.basename(path)
                    results[filename] = {
                        'features': features,
                        'duration': librosa.get_duration(y=y, sr=sr),
                        'path': path
                    }
                    
                    # Report progress
                    if callback:
                        progress = (i + idx + 1) / len(file_paths)
                        callback(progress, f"Processed {i + idx + 1}/{len(file_paths)}: {filename}")
                        
                except Exception as e:
                    print(f"Error processing {path}: {str(e)}")
                
                # Clear memory after each file
                gc.collect()
            
            # More aggressive cleanup between batches
            gc.collect()
            
        return results

    @staticmethod
    def get_audio_duration(file_path):
        """
        Get audio duration without loading full file. 

        Args:
            file_path (str): The path to the audio file.

        Returns:
            float: The duration of the audio file in seconds.   
        """
        try:
            # Use tiny duration clip to grab metadata for duration (maybe others?)
            y, sr = librosa.load(file_path, sr=22050, duration=0.1)
            duration = librosa.get_duration(path=file_path)
            return duration
        except Exception as e:
            print(f"Could not get duration for {file_path}: {str(e)}")
            return 0

class AudioLoader:

    @staticmethod
    def load_audio(file_path):
        """
        Load and preprocess audio with memory optimization.
        Reduces file size with lower sample rate/duration and trimming silence.

        Args:
            file_path (str): The path to the audio file.

        Returns:
            tuple: A tuple of the audio data and sample rate.
        """
        try:
            # Lower sample rate and duration for memory efficiency (MAY NEED TO INCREASE SAMPLE DURATION FOR ACCURACY LATER)
            y, sr = librosa.load(file_path, sr=16000, mono=True, duration=60)  # 1 minute, 16kHz
            
            # Trim silence to reduce data size
            y_trimmed, _ = librosa.effects.trim(y, top_db=25)
            
            # Normalize then return trimmed
            return librosa.util.normalize(y_trimmed), sr
        except Exception as e:
            raise RuntimeError(f"Failed to load {file_path}: {str(e)}")
        finally:  # Guarantee memory cleanup
            gc.collect()
    
    @staticmethod
    def get_full_duration(file_path):
        """
        Get total file duration with better error handling.

        Args:
            file_path (str): The path to the audio file.

        Returns:
            float: The duration of the audio file in seconds.
        """
        try:
            # Use soundfile for more reliable duration calculation (length was being calced wrong for some)
            with sf.SoundFile(file_path) as f:
                return f.frames / f.samplerate
        except Exception as e:
            print(f"Duration error {file_path}: {str(e)}")
            try:
                # Fallback to librosa
                return librosa.get_duration(path=file_path)
            except:
                return 0

class FeatureExtractor:
    @staticmethod
    def extract_features(y, sr):
        """
        Memory-optimized feature extraction.
        Focus on essential features for comparison to minimize memory usage.

        Args:
            y (np.ndarray): The audio data.
            sr (int): The sample rate of the audio data.

        Returns:
            dict: A dictionary of features.
        """
        if y.size == 0:
            raise ValueError("Empty audio data")
            
        features = {}
        
        # params
        hop_length = 1024  # increase hop length to reduce feature size (or vice ver)
        n_fft = 2048
        
        try:
            # Chroma features
            features['chroma'] = librosa.feature.chroma_cqt(
                y=y, sr=sr, 
                hop_length=hop_length,
                n_chroma=12,
                bins_per_octave=24
            )
            
            # MFCC with minimal coefficients
            features['mfcc'] = np.nan_to_num(librosa.feature.mfcc(
                y=y, sr=sr, 
                n_mfcc=8,  # Reduced from 13
                hop_length=hop_length,
                n_fft=n_fft
            ))
            
            # tempogram
            # uncomment when wanting to visualize (more intensive processing)
            # add a toggle option before running comparison?
            # https://librosa.org/doc/main/generated/librosa.feature.tempogram.html
            """
            onset_env = librosa.onset.onset_strength(
                y=y, sr=sr,
                hop_length=hop_length
            )
            features['tempogram'] = librosa.feature.tempogram(
                onset_envelope=onset_env, 
                sr=sr,
                win_length=32
            )
            """
            
            return features
        except Exception as e:
            raise RuntimeError(f"Feature extraction failed: {str(e)}")
        finally:  # Guarantee memory cleanup
            y = None
            gc.collect()

    @staticmethod
    def extract_minimal_features(y, sr):
        """
        Lightweight feature extraction for very large datasets.
        Used this when processing many files or when memory is severely constrained.
        (testing on large folder with ~200 files)

        Args:
            y (np.ndarray): The audio data.
            sr (int): The sample rate of the audio data.

        Returns:
            dict: A dictionary of features.
        """
        features = {}
        
        # Use very large hop length for tiny feature matrices
        hop_length = 2048
        
        try:
            # Just use MFCCs for lightweight comparison
            mfccs = librosa.feature.mfcc(
                y=y, sr=sr, 
                n_mfcc=8,
                hop_length=hop_length
            )
            
            # Take mean across time for a single val per file
            features['mfcc_mean'] = np.mean(mfccs, axis=1)
            
            # Add basic spectral features
            features['spectral_centroid'] = np.mean(librosa.feature.spectral_centroid(
                y=y, sr=sr, hop_length=hop_length
            ))
            
            return features
        except Exception as e:
            raise RuntimeError(f"Minimal feature extraction failed: {str(e)}")
        finally:
            gc.collect()

