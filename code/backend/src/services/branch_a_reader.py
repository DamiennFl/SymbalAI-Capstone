import os
import tempfile
from faster_whisper import WhisperModel

from ML.read_score_branch_a import score_file

# Load Whisper once when the server boots
MODEL = WhisperModel("small.en", compute_type="auto")

def analyze_audio_branch_a(upload_file):
  """_summary_
  Takes UploadFile, saves to temp file, runs Branch A reading detection.
  Returns normalized dict: { score, labels, metadata }
  Args:
      upload_file (_type_): _description_
  """
  
  # Save to temp file
  with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
    tmp.write(upload_file.file.read())
    tmp_path = tmp.name
  
  # Run Branch A algorithm
  result = score_file(MODEL, tmp_path)
  
  # Cleanup temp file
  os.remove(tmp_path)
  
  # Convert to API schema
  score = float(result.get("reading_likelihood", 0.0))
  subscores = result.get("subscores", {})
  features = result.get("features", {})
  
  return {
    "score": score,
    "labels": {
      "reading_likelihood": score
    },
    "metadata": {
      "features": features,
      "subscores": subscores,
      "branch": "A",
      "note": result.get("note", "")
    }
  }