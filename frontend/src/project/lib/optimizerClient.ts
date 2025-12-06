import { OptimizerRun, RunMode } from "../types";

export type OptimizeRequest = {
  layoutFile: File;
  companies: string[];
  mode: RunMode;
  roomLabel?: string;
};

export async function optimizeLayout(request: OptimizeRequest): Promise<OptimizerRun> {
  const { layoutFile, companies, mode, roomLabel } = request;
  const apiBase = process.env.NEXT_PUBLIC_OPTIMIZER_API?.trim().replace(/\/+$/, "") || "";
  const endpoint = `${apiBase}/api/optimize`;
  const formData = new FormData();
  formData.append("layout", layoutFile);
  formData.append("companies", JSON.stringify(companies));
  formData.append("mode", mode);
  if (roomLabel) {
    formData.append("roomLabel", roomLabel);
  }

  const res = await fetch(endpoint, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    const reason = detail?.error || `Optimizer request failed with status ${res.status}`;
    throw new Error(reason);
  }

  const body = await res.json();
  return body.run as OptimizerRun;
}
