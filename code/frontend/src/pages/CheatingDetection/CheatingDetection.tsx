import { useEffect, useRef, useState } from "react";
import "./CheatingDetection.css";
import AnalysisResults from "./AnalysisResults";
import RecordingCard from "../../components/RecordingCard/RecordingCard";
import { analyzeAudioFile, type AudioDetectionResult } from "../../api/Detect";

export default function CheatingDetection() {
  const [recording, setRecording] = useState(false);
  const [permissionDenied, setPermissionDenied] = useState(false);
  const [audioURL, setAudioURL] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [testExecuted, setTestExecuted] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<{
    branchA?: number;
    branchB?: number;
    combined?: number;
  } | null>(null);

  const [selectedBranch, setSelectedBranch] = useState<"a" | "b" | "combined">(
    "combined"
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [fullResult, setFullResult] = useState<AudioDetectionResult | null>(
    null
  );

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uploadedFileRef = useRef<File | null>(null);

  useEffect(() => {
    return () => {
      // cleanup
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  // Cleanup for object URLs on unmount / audioURL change
  useEffect(() => {
    return () => {
      try {
        if (audioURL) URL.revokeObjectURL(audioURL);
      } catch (error) {
        console.error(
          "Error occurs while cleaning up for object URLs on audioURL change: ",
          error
        );
      }
    };
  }, [audioURL]);

  async function startRecording() {
    setStatus(null);
    setAudioURL(null);
    setTestExecuted(false);
    setAnalysisResults(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mime = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/ogg";
      const mr = new MediaRecorder(stream, { mimeType: mime });
      mediaRecorderRef.current = mr;
      chunksRef.current = [];

      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onstart = () => {
        setRecording(true);
        setStatus("Recording in progress");
      };

      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mime });
        const url = URL.createObjectURL(blob);
        setAudioURL(url);
        setRecording(false);
        setStatus("Recording stopped — preview below");
        // stop microphone tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
        }
        mediaRecorderRef.current = null;
      };

      mr.start();
    } catch (err) {
      console.error(err);
      setPermissionDenied(true);
      setStatus("Microphone access denied");
    }
  }

  function stopRecording() {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      mediaRecorderRef.current.stop();
    } else {
      // fallback: stop tracks and set state
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
      setRecording(false);
      setStatus("Recording stopped");
    }
  }

  function downloadRecording() {
    if (!audioURL) return;
    const a = document.createElement("a");
    a.href = audioURL;
    a.download = "answer.webm";
    a.click();
  }

  function handleUploadClick() {
    fileInputRef.current?.click();
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    uploadedFileRef.current = f;
    setSelectedFile(f);
    // clear previous recorded blob URL if any
    try {
      if (audioURL) {
        URL.revokeObjectURL(audioURL);
      }
    } catch (error) {
      console.error("Error: ", error);
    }
    const url = URL.createObjectURL(f);
    setAudioURL(url);
    setStatus(`Selected file: ${f.name}`);
    setTestExecuted(false);
    setAnalysisResults(null);
  }

  async function handleTestBranch(branch: "a" | "b" | "combined") {
    setSelectedBranch(branch);
    setTestExecuted(true);

    // If we already have analysisResults from backend, just show it.
    if (analysisResults) {
      setStatus(
        branch === "a"
          ? `Showing Branch A result`
          : branch === "b"
          ? `Showing Branch B result`
          : `Showing combined result`
      );
      return;
    }

    // No results yet - need to analyze
    if (!audioURL) {
      setStatus("No audio available to analyze.");
      return;
    }

    setStatus("Sending audio to backend...");
    try {
      let fileToSend: File | null = selectedFile;
      if (!fileToSend && audioURL) {
        const r = await fetch(audioURL);
        const blob = await r.blob();
        const ext = blob.type ? blob.type.split("/")[1] : "webm";
        fileToSend = new File([blob], `recorded.${ext}`, {
          type: blob.type || "audio/webm",
        });
      }

      if (!fileToSend) {
        setStatus("No audio available to analyze.");
        return;
      }

      const res = await analyzeAudioFile(fileToSend);

      setAnalysisResults({
        branchA: res.branch_a.score,
        branchB: res.branch_b.prob,
        combined: res.combined.score,
      });

      setFullResult(res);
      setStatus(
        `Analysis complete — risk: ${res.combined.risk_label ?? res.combined.risk_label}`
      );
    } catch (err) {
      if (err instanceof Error) {
        console.error(err);
        setStatus(`Analysis failed: ${err.message}`);
      } else {
        console.error("Unknown error:", err);
        setStatus(`Analysis failed: ${String(err)}`);
      }
    }
  }

  return (
    <div className="page-wrap">
      <header className="page-header">
        <h1>Interview Cheating Detection</h1>
        <p className="subtitle">Two-branch audio analysis system</p>
      </header>

      <main className="card-wrap">
        <section className="card">
          <div className="card-title">
            <div className="icon">🎙️</div>
            <div>
              <div className="title-text">Record Your Answer</div>
              <div className="step-text">step 1 of 2</div>
            </div>
          </div>

          <hr className="divider" />

          <p className="instruction">
            Click the record button and answer any interview question. Try
            speaking naturally or reading from a script to test the system.
          </p>

          {/* NEW: grid with recording on left and upload on right */}
          <div className="record-upload-grid">
            <div className="record-section">
              <div className="controls">
                {!recording ? (
                  <button className="btn btn-primary" onClick={startRecording}>
                    <span className="mic-icon">🎤</span>
                    <span>Start Recording</span>
                  </button>
                ) : (
                  <button className="btn btn-stop" onClick={stopRecording}>
                    <span className="stop-icon">■</span>
                    <span>Stop Recording</span>
                  </button>
                )}
                <div className="hint">Your audio will be analyzed locally</div>
              </div>

              <div className="status-area">
                {status && (
                  <div
                    className={`status ${recording ? "status-recording" : ""}`}
                  >
                    {recording && <span className="red-dot" />}
                    <span>{status}</span>
                  </div>
                )}
                {permissionDenied && (
                  <div className="permission-warning">
                    Please allow microphone access in your browser.
                  </div>
                )}
              </div>
            </div>

            <div className="upload-section">
              {/* <div className="upload-title">Upload an audio file</div>
              <p className="instruction small">
                Or upload a previously recorded answer. Supported formats: wav,
                mp3, webm, ogg.
              </p> */}

              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*"
                onChange={onFileChange}
                style={{ display: "none" }}
              />

              <div className="upload-controls">
                <button className="btn btn-primary" onClick={handleUploadClick}>
                  Upload an Audio File
                </button>

                {/* <button
                  className="btn btn-primary"
                  onClick={() => {
                    // if a file is selected, mark as ready for analysis (placeholder)
                    if (selectedFile) {
                      setStatus(`Ready to analyze ${selectedFile.name}`);
                      setTestExecuted(false);
                      setAnalysisResults(null);
                    } else {
                      setStatus("No file selected");
                    }
                  }}
                >
                  Upload & Prepare
                </button> */}
              </div>

              <div className="upload-meta">
                {selectedFile ? (
                  <div className="file-info">
                    <strong>{selectedFile.name}</strong>
                    <div className="hint small">
                      Size: {(selectedFile.size / 1024).toFixed(1)} KB
                    </div>
                  </div>
                ) : (
                  <div className="hint small">No file selected</div>
                )}
              </div>
            </div>
          </div>
          {audioURL && (
            <div className="playback">
              <audio ref={audioRef} src={audioURL} controls />
              <div className="playback-actions">
                <button className="btn btn-outline" onClick={downloadRecording}>
                  Download
                </button>
                <button
                  className="btn btn-outline"
                  onClick={async () => {
                    setStatus("Sending audio to backend...");
                    try {
                      // prefer uploaded file, otherwise try to fetch blob from audioURL created earlier
                      let fileToSend: File | null = selectedFile;
                      if (!fileToSend && audioURL) {
                        // fetch the blob from the object URL
                        const r = await fetch(audioURL);
                        const blob = await r.blob();
                        // derive extension from blob type or fallback to webm
                        const ext = blob.type
                          ? blob.type.split("/")[1]
                          : "webm";
                        fileToSend = new File([blob], `recorded.${ext}`, {
                          type: blob.type || "audio/webm",
                        });
                      }

                      if (!fileToSend) {
                        setStatus("No audio available to analyze.");
                        return;
                      }

                      const res = await analyzeAudioFile(fileToSend);

                      // map backend response to the local AnalysisResults shape
                      setAnalysisResults({
                        branchA: res.branch_a.score,
                        branchB: res.branch_b.prob,
                        combined: res.combined.score,
                      });

                      // Optionally store full metadata somewhere for UI details:
                      setFullResult(res);
                      setTestExecuted(true);
                      setSelectedBranch("combined");

                      setStatus(
                        `Analysis complete — risk: ${
                          res.combined.risk_label ?? res.combined.risk_label
                        }`
                      );
                      console.log("Full result: ", res);
                    } catch (err) {
                      if (err instanceof Error) {
                        console.error(err);
                        setStatus(`Analysis failed: ${err.message}`);
                      } else {
                        // handle non-Error values just in case
                        console.error("Unknown error:", err);
                        setStatus(`Analysis failed: ${String(err)}`);
                      }
                    }
                  }}
                >
                  Analyze Audio
                </button>
              </div>
            </div>
          )}
        </section>
      </main>

      {/* Step 2: choose analysis branch — show after a recording is available */}
      {audioURL && (
        <main className="card-wrap step-two">
          <section className="card">
            <div className="card-title">
              <div className="icon">🔊</div>
              <div>
                <div className="title-text">Test Your Recording</div>
                <div className="step-text">step 2 of 2</div>
              </div>
            </div>

            <hr className="divider" />

            <p className="instruction">
              Choose an analysis method to evaluate your recording. Each branch
              uses different detection techniques.
            </p>

            <div className="branch-grid">
              <RecordingCard
                icon="📄"
                title="Branch A"
                subtitle="ASR-Drive"
                description="Analyzes timing patterns, pauses, disfluencies, and prosody to detect if you're reading from a script."
                actionLabel="Test Branch A"
                helperText="Readiness detection"
                selected={selectedBranch === "a"}
                metricLabel="read-lik"
                metricValue={analysisResults?.branchA ?? null}
                metricIsProb={true}
                metricPrecision={1}
                onAction={() => handleTestBranch("a")}
              />

              <RecordingCard
                icon="🔉"
                title="Branch B"
                subtitle="Synthetic Audio"
                description="Detects text-to-speech systems, voice conversion, replay attacks, and other synthetic audio artifacts."
                actionLabel="Test Branch B"
                helperText="Synthetic audio detection"
                selected={selectedBranch === "b"}
                metricLabel="synth"
                metricValue={analysisResults?.branchB ?? null}
                metricIsProb={true}
                metricPrecision={1}
                onAction={() => handleTestBranch("b")}
              />

              <RecordingCard
                icon="📊"
                title="Combined"
                subtitle="Recommmended"
                description="Fused score combining both branches with audio quality metrics for a comprehensive cheating risk assessment."
                actionLabel="Test Combined"
                helperText="Most accurate method"
                selected={selectedBranch === "combined"}
                metricLabel="risk"
                metricValue={analysisResults?.combined ?? null}
                metricIsProb={true}
                metricPrecision={1}
                onAction={() => handleTestBranch("combined")}
              />
            </div>
          </section>
        </main>
      )}

      {/* AnalysisResults: only show after test button is clicked */}
      {testExecuted && (
        <main className="card-wrap">
          <AnalysisResults
            results={analysisResults}
            fullResult={fullResult}
            activeTest={
              selectedBranch === "a"
                ? "branchA"
                : selectedBranch === "b"
                ? "branchB"
                : "combined"
            }
          />
        </main>
      )}
    </div>
  );
}
