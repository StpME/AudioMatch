import os
import librosa
from audio_processor import AudioLoader, FeatureExtractor
from scipy.spatial.distance import cosine
from fastdtw import fastdtw
import numpy as np

# Will need to tweak confidence for precision and also change color intervals (90-95 would be green/good)
class AudioComparator:
    def __init__(self, threshold=0.35):
        self.reference_features = {}
        self.threshold = threshold

    def compare(self, query_path):
        """
        Compare the query audio to the reference features.

        Args:
            query_path (str): The path to the query audio file.

        Returns:
            tuple: A tuple containing the best match and
            a dictionary of the results.
        """
        try:
            y_query, sr_query = AudioLoader.load_audio(query_path)
            query_duration = AudioLoader.get_full_duration(query_path)
            query_features = FeatureExtractor.extract_features(y_query, sr_query)
            
            # Explicit memory cleanup
            del y_query
        except Exception as e:
            return None, str(e)

        results = []
        for ref_name, ref_data in self.reference_features.items():
            try:
                similarity = self._safe_similarity(query_features, ref_data['features'])
                results.append({
                    'reference': ref_name,
                    'similarity': similarity,
                    'orig_duration': ref_data['full_duration']
            })
            except Exception as e:
                print(f"Comparison error: {str(e)}")
                continue

        # Cleanup query features
        del query_features
        
        if not results:
            return None, "No valid comparisons"
            
        results.sort(key=lambda x: x['similarity'], reverse=True)
        best = results[0] if results[0]['similarity'] >= self.threshold else None
        return (best, 
        {
            'results': results,
            'query_duration': query_duration
        }
    )

    def _safe_similarity(self, query, ref):
        """
        Thread-safe similarity calculation.

        Returns:
            float: The similarity score between the query and reference features.
        """
        scores = []
        
        # Chroma comparison with size validation
        if 'chroma' in query and 'chroma' in ref:
            try:
                min_frames = min(query['chroma'].shape[1], ref['chroma'].shape[1])
                q_chroma = query['chroma'][:, :min_frames]
                r_chroma = ref['chroma'][:, :min_frames]
                # no div by 0 with epsilon
                d, _ = fastdtw(q_chroma.T, r_chroma.T, dist=lambda x, y: cosine(x, y) + 1e-9)
                scores.append(1 / (1 + d/100))
            except Exception as e:
                print(f"Chroma error: {str(e)}")

        # MFCC comparison
        if 'mfcc' in query and 'mfcc' in ref:
            try:
                q_mfcc = np.mean(query['mfcc'], axis=1)
                r_mfcc = np.mean(ref['mfcc'], axis=1)
                #no div by 0
                similarity = 1 - cosine(q_mfcc + 1e-9, r_mfcc + 1e-9)
                scores.append(max(min(similarity, 1.0), 0.0))
            except Exception as e:
                print(f"MFCC error: {str(e)}")

        return np.mean(scores) if scores else 0.0