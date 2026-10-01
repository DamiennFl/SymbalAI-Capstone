import React from "react";
import "./RecordingCard.css";

export interface RecordingCardProps {
  icon?: React.ReactNode;
  title: string;
  subtitle?: string;
  badgeLabel?: string;
  pillLabel?: string;
  description: string;
  actionLabel: string;
  helperText: string;
  selected?: boolean;

  metricLabel?: string; // label shown next to metric (e.g. "score", "prob")
  metricValue?: number | null; // numeric value to display
  metricIsProb?: boolean; // if true, render as percent
  metricPrecision?: number; // decimals to show (default 3)

  onAction?: () => void;
}

export default function RecordingCard({
  icon = "🔊",
  title,
  subtitle,
  badgeLabel,
  pillLabel,
  description,
  actionLabel,
  helperText,
  selected = false,

  metricLabel,
  metricValue = null,
  metricIsProb = false,
  metricPrecision = 3,

  onAction,
}: RecordingCardProps) {
  // format metric for display
  const renderMetric = () => {
    if (metricValue === null || metricValue === undefined) return null;
    const p = Math.max(0, metricPrecision);
    if (metricIsProb) {
      const pct = Number(metricValue) * 100;
      return (
        <div className="recording-card__metric recording-card__metric--prob">
          <div className="recording-card__metric-value">{pct.toFixed(1)}%</div>
          {metricLabel && (
            <div className="recording-card__metric-label">{metricLabel}</div>
          )}
        </div>
      );
    }
    return (
      <div className="recording-card__metric">
        <div className="recording-card__metric-value">
          {Number(metricValue).toFixed(p)}
        </div>
        {metricLabel && (
          <div className="recording-card__metric-label">{metricLabel}</div>
        )}
      </div>
    );
  };

  return (
    <div
      className={`recording-card${selected ? " recording-card--selected" : ""}`}
    >
      <div className="recording-card__header">
        <div className="recording-card__icon">{icon}</div>
        <div>
          <p className="recording-card__title">{title}</p>
          {subtitle && <p className="recording-card__subtitle">{subtitle}</p>}
        </div>

        {/* { changed code } show metric on the right if available */}
        <div style={{ marginLeft: "auto" }}>{renderMetric()}</div>

        {badgeLabel && (
          <span className="recording-card__badge">{badgeLabel}</span>
        )}
      </div>

      {pillLabel && <span className="recording-card__pill">{pillLabel}</span>}

      <p className="recording-card__description">{description}</p>

      <button
        type="button"
        className={`recording-card__action${
          selected ? " recording-card__action--primary" : ""
        }`}
        onClick={onAction}
      >
        {actionLabel}
      </button>

      <p className="recording-card__helper">{helperText}</p>
    </div>
  );
}
