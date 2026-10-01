export type AudioDetectionResult = {
  branch_a: { score: number; metadata: Record<string, unknown> };
  branch_b: { prob: number; wins: number[]; duration_sec: number };
  combined: {
    score: number;
    synthetic_prob: number;
    reading_likelihood: number;
    risk_label: string;
  };
};

function getBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_URL;
  return (envUrl && String(envUrl).replace(/\/$/, "")) || "http://localhost:8000";
}

export async function analyzeAudioFile(file: File): Promise<AudioDetectionResult> {
  const base = getBaseUrl();
  const url = `${base}/detect/audio`;

  const fd = new FormData();
  fd.append("file", file, file.name);

  const resp = await fetch(url, {
    method: "POST",
    body: fd,
  });

  if (!resp.ok) {
    const txt = await resp.text().catch(() => "");
    throw new Error(`Server error ${resp.status}: ${txt}`);
  }

  const json = (await resp.json()) as AudioDetectionResult;
  return json;
}