import { type AudioDetectionResult } from "../../api/Detect";

type ResultsShape = {
  branchA?: number;
  branchB?: number;
  combined?: number;
} | null;

type Props = {
  results: ResultsShape;
  activeTest: "branchA" | "branchB" | "combined";
  fullResult?: AudioDetectionResult | null; // optional full API payload for details
};

function formatPct(value?: number | null) {
  if (value === undefined || value === null) return "—";
  // value is probability in [0..1]
  return `${(value * 100).toFixed(1)}%`;
}

function getRiskLevelFromPct(pct?: number | null) {
  if (pct === undefined || pct === null) return "—";
  if (pct >= 50) return "High";
  if (pct >= 30) return "Medium";
  return "Low";
}

function getRiskMessageFromPct(pct?: number | null) {
  if (pct === undefined || pct === null) return "No data available.";
  if (pct > 50)
    return "This response contains several indicators that suggest scripted or synthetic audio.";
  if (pct > 30)
    return "Some indicators detected — review the recording for possible issues.";
  return "This response appears natural and spontaneous with no significant risk indicators detected.";
}

export default function AnalysisResults({ results, activeTest }: Props) {
  // Render placeholder when no results yet
  if (!results) {
    return (
      <section className="card ar-card">
        <div className="card-title">
          <div className="icon">📊</div>
          <div>
            <div className="title-text">Analysis Results</div>
            <div className="step-text">Completed analysis</div>
          </div>
        </div>

        <hr className="divider" />

        <p className="instruction">
          Analysis will appear here after the recording has been tested. Waiting
          for Test UI to provide results.
        </p>
      </section>
    );
  }

  // convert to percent numbers for level decisions
  const branchAPct = results.branchA != null ? results.branchA * 100 : null;
  const branchBPct = results.branchB != null ? results.branchB * 100 : null;
  const combinedPct = results.combined != null ? results.combined * 100 : null;

  const branchALevel = getRiskLevelFromPct(branchAPct);
  const branchBLevel = getRiskLevelFromPct(branchBPct);
  const combinedLevel = getRiskLevelFromPct(combinedPct);

  return (
    <section className="card ar-card">
      <div className="card-title">
        <div className="icon">📊</div>
        <div>
          <div className="title-text">Analysis Results</div>
          <div className="step-text">Completed analysis</div>
        </div>
      </div>

      <hr className="divider" />

      {/* Branch A */}
      {activeTest === "branchA" && (
        <div className="ar-block">
          <div className="ar-scorebox">
            <div className="ar-score-label">Branch A Risk Score</div>
            <div className="ar-score-value">
              {formatPct(results.branchA ?? null)}
            </div>

            <div className={`ar-badge ar-badge-${branchALevel.toLowerCase()}`}>
              <span className="ar-badge-dot" />
              <span className="ar-badge-text">{branchALevel}</span>
            </div>
          </div>

          <div className="ar-divider" />

          <p className="ar-text">{getRiskMessageFromPct(branchAPct)}</p>

          <div className="ar-method">
            <div className="ar-method-title">Analysis Method</div>
            <div className="ar-method-desc">
              ASR-driven readingness detection analyzing timing patterns,
              pauses, disfluencies, and prosody indicators.
            </div>
          </div>

          <div className="ar-note">
            <div className="ar-note-icon">ℹ️</div>
            <div className="ar-note-text">
              Branch A focuses on speech patterns and delivery characteristics.
              Higher scores indicate scripted or rehearsed responses.
            </div>
          </div>
        </div>
      )}

      {/* Branch B */}
      {activeTest === "branchB" && (
        <div className="ar-block">
          <div className="ar-scorebox">
            <div className="ar-score-label">Branch B Synthetic Prob</div>
            <div className="ar-score-value">
              {formatPct(results.branchB ?? null)}
            </div>

            <div className={`ar-badge ar-badge-${branchBLevel.toLowerCase()}`}>
              <span className="ar-badge-dot" />
              <span className="ar-badge-text">{branchBLevel}</span>
            </div>
          </div>

          <div className="ar-divider" />

          <p className="ar-text">{getRiskMessageFromPct(branchBPct)}</p>

          <div className="ar-method">
            <div className="ar-method-title">Analysis Method</div>
            <div className="ar-method-desc">
              Synthetic audio detection identifying TTS systems, voice
              conversion, replay attacks, and artificial audio artifacts.
            </div>
          </div>

          <div className="ar-note">
            <div className="ar-note-icon">ℹ️</div>
            <div className="ar-note-text">
              Branch B detects synthetic or manipulated audio. Higher scores
              suggest the use of AI-generated voices or audio editing tools.
            </div>
          </div>
        </div>
      )}

      {/* Combined */}
      {activeTest === "combined" && (
        <div className="ar-block">
          <div className="ar-scorebox">
            <div className="ar-score-label">Overall Risk Score</div>
            <div className="ar-score-value">
              {formatPct(results.combined ?? null)}
            </div>

            <div className={`ar-badge ar-badge-${combinedLevel.toLowerCase()}`}>
              <span className="ar-badge-dot" />
              <span className="ar-badge-text">{combinedLevel}</span>
            </div>
          </div>

          <div className="ar-divider" />

          <p className="ar-text">{getRiskMessageFromPct(combinedPct)}</p>

          <div className="ar-breakdown">
            <h3 className="ar-breakdown-title">Detailed Breakdown</h3>

            <div className="ar-row">
              <div>
                <div className="ar-row-title">Branch A Score</div>
                <div className="ar-row-sub">Readingness detection</div>
              </div>
              <div className="ar-row-value">
                {formatPct(results.branchA ?? null)}
              </div>
            </div>

            <div className="ar-row">
              <div>
                <div className="ar-row-title">Branch B Score</div>
                <div className="ar-row-sub">Synthetic audio detection</div>
              </div>
              <div className="ar-row-value">
                {formatPct(results.branchB ?? null)}
              </div>
            </div>

            <div className="ar-row ar-row-highlight">
              <div>
                <div className="ar-row-title">Combined Score</div>
                <div className="ar-row-sub">Fused analysis result</div>
              </div>
              <div className="ar-row-value ar-row-value-combined">
                {formatPct(results.combined ?? null)}
              </div>
            </div>
          </div>

          <div className="ar-note">
            <div className="ar-note-icon">ℹ️</div>
            <div className="ar-note-text">
              Combined analysis provides the most comprehensive assessment by
              fusing both detection methods with audio quality metrics.
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
