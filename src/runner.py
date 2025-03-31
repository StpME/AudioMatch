from PyQt5.QtCore import QThread, pyqtSignal, QMutex
import traceback
import os
import librosa
import numpy as np
import gc
from audio_processor import AudioLoader, FeatureExtractor

file_mutex = QMutex()

class Runner(QThread):
    progress_updated = pyqtSignal(int, str)
    matches_found = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, original_files, remastered_files, batch_size=5):
        super().__init__()
        self.original_files = original_files
        self.remastered_files = remastered_files
        self.batch_size = batch_size
        self.keep_running = True
        self.comparator = None
    
    def run(self):
        try:
            from comparator import AudioComparator
            self.comparator = AudioComparator()
            
            # Process reference files in batches
            self.progress_updated.emit(0, "Loading reference files in batches...")
            self._load_references()
            
            if not self.comparator.reference_features:
                self.error_occurred.emit("No valid reference files loaded")
                return
                
            # Process remastered files in batches
            self.progress_updated.emit(50, "Processing remastered files in batches...")
            results = self._process_remastered()
            
            self.matches_found.emit(results)
            
        except Exception as e:
            error_msg = f"Critical error:\n{str(e)}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)
    
    def _load_references(self):
        """
        Load reference files in smaller batches to manage memory.
        """
        total_loaded = 0
        
        for i in range(0, len(self.original_files), self.batch_size):
            if not self.keep_running:
                return
                
            batch = self.original_files[i:i+self.batch_size]
            loaded_in_batch = 0
            
            for path in batch:
                if not self.keep_running:
                    return
                    
                try:
                    full_duration = AudioLoader.get_full_duration(path)
                    y, sr = AudioLoader.load_audio(path)
                    features = FeatureExtractor.extract_features(y, sr)
                    self.comparator.reference_features[os.path.basename(path)] = {
                        'features': features,
                        'full_duration': full_duration,
                        'path': path
                    }
                    loaded_in_batch += 1
                    total_loaded += 1
                except Exception as e:
                    self.error_occurred.emit(f"Skipping {os.path.basename(path)}: {str(e)}")
                
                # Force garbage collection between each file
                self._clear_memory()
                
                # Update progress
                progress = int((total_loaded / len(self.original_files)) * 50)  # First half of progress -> then remastered
                self.progress_updated.emit(progress, f"Loaded {total_loaded}/{len(self.original_files)} references")
            
            # Clear memory between batches
            self._clear_memory()
    
    def _process_remastered(self):
        """
        Process remastered files in batches.
        Once process is finished, append them to the list of columns.

        Returns: 
            results: List of file details.

        """
        results = []
        total_processed = 0
        
        for i in range(0, len(self.remastered_files), self.batch_size):
            if not self.keep_running:
                break
                
            batch = self.remastered_files[i:i+self.batch_size]
            
            for path in batch:
                if not self.keep_running:
                    break
                    
                try:
                    full_duration = AudioLoader.get_full_duration(path)
                    match, details = self.comparator.compare(path)

                    orig_path = ''
                    if match:
                        ref_data = self.comparator.reference_features.get(match['reference'], {})
                        orig_path = ref_data.get('path', '')

                    orig_duration = self.comparator.reference_features.get(
                        match['reference'], {}
                    ).get('full_duration', 0) if match else 0
                    results.append({
                        'remastered': os.path.basename(path),
                        'match': match['reference'] if match else "No match",
                        'confidence': match['similarity'] if match else 0.0,
                        'orig_path': orig_path,
                        'path': path, 
                        'rem_duration': full_duration,  # Add duration
                        'orig_duration': orig_duration,  # Add og duration
                        'display_name': os.path.basename(path)
                    })
                except Exception as e:
                    self.error_occurred.emit(f"Error processing {os.path.basename(path)}: {str(e)}")
                
                total_processed += 1
                
                self._clear_memory()
                
                # Update progress (second half)
                progress = 50 + int((total_processed / len(self.remastered_files)) * 50)
                self.progress_updated.emit(progress, f"Processed {total_processed}/{len(self.remastered_files)} remastered")
            
            # Clear memory between batches
            self._clear_memory()
        
        return results
    
    def _clear_memory(self):
        """
        Aggressive memory cleanup between batches.
        Garbage collection so memory isnt used up during intensive audio processing.
        """
        gc.collect()
    
    def load_reference(self, path):
        """test method for compatibility"""
        try:
            y, sr = AudioLoader.load_audio(path)
            features = FeatureExtractor.extract_features(y, sr)
            return os.path.basename(path), features, sr
        except Exception as e:
            self.error_occurred.emit(f"Skipping {path}: {str(e)}")
            return None

    def process_file(self, comparator, path):
        """test method for compatibility"""
        try:
            match, _ = comparator.compare(path)
            return {
                'remastered': os.path.basename(path),
                'match': match.get('reference', "No match") if match else "No match",
                'confidence': match['similarity'] if match else 0.0,
                'path': path
            }
        except Exception as e:
            error_msg = f"Error processing {path}: {str(e)}"
            self.error_occurred.emit(error_msg)
            return None

    def _update_progress(self, current, total, message):
        """test method for compatibility"""
        progress = int((current / total) * 100)
        self.progress_updated.emit(progress, message)









    def stop(self):
        """
        Stops the processing.
        """
        self.keep_running = False
        self.wait(1000)  # Wait 1 sec for last thread to finish