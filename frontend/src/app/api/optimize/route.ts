import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import os from "os";
import path from "path";
import { spawn } from "child_process";
import crypto from "crypto";
import * as XLSX from "xlsx";

export const runtime = "nodejs";

type PythonPayload = {
  layout_file: string;
  plot_path?: string | null;
  booth_count: number;
  placed_count: number;
  min_distance: number;
  typical_spacing?: number;
  assignments: Array<{ company: string; booth: number; x?: number; y?: number }>;
  unplaced_companies: string[];
  big_companies?: string[];
};

type RunMode = "primary" | "overflow" | "comparison";

function scoreFromDistance(minDistance: number, typicalSpacing?: number): number {
  const baseline = typicalSpacing && typicalSpacing > 0 ? typicalSpacing * 2.5 : 10;
  const clamped = Math.max(0, Math.min(minDistance / baseline, 1));
  return Number(clamped.toFixed(3));
}

async function saveUpload(file: File, targetPath: string) {
  const arrayBuffer = await file.arrayBuffer();
  await fs.writeFile(targetPath, Buffer.from(arrayBuffer));
}

async function runPython(
  scriptArgs: string[],
  cwd: string
): Promise<{ stdout: string; stderr: string; code: number }> {
  return new Promise((resolve, reject) => {
    const child = spawn("python3", scriptArgs, { cwd });
    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (data) => {
      stdout += data.toString();
    });
    child.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    child.on("close", (code) => {
      resolve({ stdout, stderr, code: code ?? 0 });
    });
    child.on("error", reject);
  });
}

async function buildResponsePayload(
  payload: PythonPayload,
  plotPath: string | undefined,
  mode: RunMode,
  roomLabel?: string
) {
  const plotExists = plotPath ? await fs.access(plotPath).then(() => true).catch(() => false) : false;
  const plotUrl =
    plotExists && plotPath
      ? `data:image/png;base64,${(await fs.readFile(plotPath)).toString("base64")}`
      : undefined;

  return {
    id: crypto.randomUUID(),
    mode,
    layoutName: payload.layout_file,
    roomLabel,
    boothCount: payload.booth_count,
    placedCount: payload.placed_count,
    minDistance: payload.min_distance,
    typicalSpacing: payload.typical_spacing,
    score: scoreFromDistance(payload.min_distance, payload.typical_spacing),
    assignments: payload.assignments,
    unplacedCompanies: payload.unplaced_companies,
    bigCompanies: payload.big_companies ?? [],
    plotUrl,
  };
}

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const layout = formData.get("layout");
    const companiesRaw = formData.get("companies");
    const companiesFile = formData.get("companiesFile");
    const mode = (formData.get("mode") as RunMode | null) ?? "primary";
    const roomLabel = (formData.get("roomLabel") as string | null) || undefined;

    if (!(layout instanceof File)) {
      return NextResponse.json({ error: "Layout file is required." }, { status: 400 });
    }
    let companies: string[] = [];
    if (typeof companiesRaw === "string") {
      try {
        companies = JSON.parse(companiesRaw);
      } catch {
        return NextResponse.json({ error: "Invalid companies payload." }, { status: 400 });
      }
    } else if (companiesFile instanceof File) {
      // Parse first column of Excel/CSV for company names
      const buf = Buffer.from(await companiesFile.arrayBuffer());
      const workbook = XLSX.read(buf, { type: "buffer" });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      const rows = XLSX.utils.sheet_to_json<(string | number | null)[]>(sheet, { header: 1, defval: null });
      companies = rows
        .map((r) => {
          const v = r?.[0];
          if (typeof v === "string") return v.trim();
          if (typeof v === "number") return v.toString();
          return "";
        })
        .filter((x) => x.length > 0);
    } else {
      return NextResponse.json({ error: "Company list is required (JSON or Excel file)." }, { status: 400 });
    }

    if (!Array.isArray(companies) || companies.length === 0) {
      return NextResponse.json({ error: "Company list cannot be empty." }, { status: 400 });
    }

    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "layout-opt-"));
    const layoutPath = path.join(tempDir, layout.name);
    const companiesJsonPath = path.join(tempDir, "companies.json");
    const plotPath = path.join(tempDir, "plot.png");
    const jsonOutPath = path.join(tempDir, "result.json");

    await saveUpload(layout, layoutPath);
    await fs.writeFile(companiesJsonPath, JSON.stringify(companies), "utf-8");

    const isSpreadsheet = /\.(xlsx|xls|csv)$/i.test(layout.name);
    const projectRoot = path.resolve(process.cwd(), "..");
    const scriptArgs = isSpreadsheet
      ? [
          "main.py",
          "--layout-file",
          layoutPath,
          "--companies-json",
          companiesJsonPath,
          "--max-companies",
          String(companies.length),
          "--plot-file",
          plotPath,
          "--json-out",
          jsonOutPath,
        ]
      : [
          "run_from_image.py",
          "--image",
          layoutPath,
          "--companies-json",
          companiesJsonPath,
          "--max-companies",
          String(companies.length),
          "--plot-file",
          plotPath,
          "--json-out",
          jsonOutPath,
        ];

    const { stdout, stderr, code } = await runPython(scriptArgs, projectRoot);
    if (code !== 0) {
      return NextResponse.json(
        { error: "Optimizer failed", detail: stderr || stdout, code },
        { status: 500 }
      );
    }

    const payloadRaw = await fs.readFile(jsonOutPath, "utf-8");
    const payload = JSON.parse(payloadRaw) as PythonPayload;
    const run = await buildResponsePayload(payload, plotPath, mode, roomLabel);

    return NextResponse.json({ run, stdout, stderr });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
