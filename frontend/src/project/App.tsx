"use client";

import { useMemo, useState } from "react";
import { WelcomeScreen } from "./components/WelcomeScreen";
import { InstructionsScreen } from "./components/InstructionsScreen";
import { CompanyUploadScreen } from "./components/CompanyUploadScreen";
import { LoadingScreen } from "./components/LoadingScreen";
import { ResultsScreen } from "./components/ResultsScreen";
import { ComparisonUploadScreen } from "./components/ComparisonUploadScreen";
import { ComparisonLoadingScreen } from "./components/ComparisonLoadingScreen";
import { ComparisonResultsScreen } from "./components/ComparisonResultsScreen";
import { optimizeLayout } from "./lib/optimizerClient";
import { OptimizerRun, RunMode } from "./types";

type Screen = 
  | "welcome" 
  | "instructions" 
  | "companyUpload"
  | "loading" 
  | "results" 
  | "comparisonUpload" 
  | "comparisonLoading" 
  | "comparisonResults";

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>("welcome");
  const [companies, setCompanies] = useState<string[]>([]);
  const [layoutFile, setLayoutFile] = useState<File | null>(null);
  const [layoutImageUrl, setLayoutImageUrl] = useState<string | null>(null);
  const [runs, setRuns] = useState<OptimizerRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingMessage, setLoadingMessage] = useState<string>("Optimizing layout…");
  const [uploadMode, setUploadMode] = useState<RunMode>("comparison");
  const [comparisonPair, setComparisonPair] = useState<OptimizerRun[]>([]);
  const [pendingRoomLabel, setPendingRoomLabel] = useState<string | undefined>(undefined);

  const placementRuns = runs.filter((r) => r.mode !== "comparison");
  const comparisonRuns = runs.filter((r) => r.mode === "comparison");

  const remainingCompanies = useMemo(() => {
    const placed = new Set<string>();
    placementRuns.forEach((run) => {
      run.assignments.forEach((assignment) => placed.add(assignment.company));
    });
    return companies.filter((c) => !placed.has(c));
  }, [companies, placementRuns]);

  const pickRoomLabel = (index: number) => {
    const labels = ["Room A", "Room B", "Room C", "Room D"];
    return labels[index] ?? `Room ${index + 1}`;
  };

  const selectComparisonPair = (list: OptimizerRun[]) => {
    const sorted = [...list].sort((a, b) => b.score - a.score);
    return sorted.slice(0, 2);
  };

  const handleWelcomeNext = () => {
    setCurrentScreen("instructions");
  };

  const handleInstructionsNext = (file: File) => {
    if (layoutImageUrl?.startsWith("blob:")) {
      URL.revokeObjectURL(layoutImageUrl);
    }
    const url = URL.createObjectURL(file);
    setLayoutImageUrl(url);
    setLayoutFile(file);
    setCurrentScreen("companyUpload");
  };

  const startOptimization = async (mode: RunMode, file: File, companyList: string[], roomLabel?: string) => {
    setError(null);
    setLoadingMessage(mode === "comparison" ? "Comparing layouts..." : "Optimizing layout...");
    setCurrentScreen(mode === "comparison" ? "comparisonLoading" : "loading");
    try {
      const run = await optimizeLayout({ layoutFile: file, companies: companyList, mode, roomLabel });
      setRuns((prev) => {
        const placements = prev.filter((r) => r.mode !== "comparison");
        const inferredLabel =
          roomLabel ?? (mode === "comparison" ? "Comparison" : pickRoomLabel(placements.length));
        const nextRun: OptimizerRun = { ...run, mode, roomLabel: inferredLabel };
        const updated = [...prev, nextRun];
        setComparisonPair(selectComparisonPair(updated));
        return updated;
      });
      setCurrentScreen(mode === "comparison" ? "comparisonResults" : "results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Optimization failed.");
      setCurrentScreen("results");
    }
  };

  const handleCompanyUploadNext = (companyList: string[]) => {
    if (!layoutFile) {
      setError("Upload a layout before continuing.");
      setCurrentScreen("instructions");
      return;
    }
    setCompanies(companyList);
    startOptimization("primary", layoutFile, companyList, pickRoomLabel(0));
  };

  const handleResultsBack = () => {
    setCompanies([]);
    setRuns([]);
    if (layoutImageUrl?.startsWith("blob:")) {
      URL.revokeObjectURL(layoutImageUrl);
    }
    setLayoutImageUrl(null);
    setLayoutFile(null);
    setError(null);
    setCurrentScreen("welcome");
  };

  const handleResultsCompare = () => {
    setUploadMode("comparison");
    setPendingRoomLabel(undefined);
    setCurrentScreen("comparisonUpload");
  };

  const handleComparisonUploadNext = (file: File) => {
    const companyPool = uploadMode === "overflow" ? remainingCompanies : companies;
    if (companyPool.length === 0) {
      setError("No companies left to place.");
      setCurrentScreen("results");
      return;
    }
    startOptimization(uploadMode, file, companyPool, pendingRoomLabel);
  };

  const handleComparisonUploadBack = () => {
    setCurrentScreen("results");
  };

  const handleComparisonResultsBack = () => {
    setCurrentScreen("results");
  };

  const handleUploadMoreBooths = () => {
    setUploadMode("overflow");
    setPendingRoomLabel(pickRoomLabel(placementRuns.length));
    setCurrentScreen("comparisonUpload");
  };

  return (
    <>
      {currentScreen === "welcome" && (
        <WelcomeScreen onNext={handleWelcomeNext} />
      )}
      {currentScreen === "instructions" && (
        <InstructionsScreen onNext={handleInstructionsNext} />
      )}
      {currentScreen === "companyUpload" && (
        <CompanyUploadScreen
          onNext={handleCompanyUploadNext}
          onBack={() => setCurrentScreen("instructions")}
        />
      )}
      {currentScreen === "loading" && (
        <LoadingScreen message={loadingMessage} subtext="Finding the best spacing between booths..." />
      )}
      {currentScreen === "results" && (
        <ResultsScreen 
          onBack={handleResultsBack} 
          onCompare={handleResultsCompare}
          onUploadMoreBooths={handleUploadMoreBooths}
          primaryRun={placementRuns[0]}
          overflowRuns={placementRuns.slice(1)}
          comparisonRuns={comparisonRuns}
          remainingCompanies={remainingCompanies}
          totalCompanies={companies.length}
          layoutImageUrl={layoutImageUrl ?? undefined}
          error={error}
        />
      )}
      {currentScreen === "comparisonUpload" && (
        <ComparisonUploadScreen 
          remainingCount={uploadMode === "overflow" ? remainingCompanies.length : undefined}
          mode={uploadMode === "overflow" ? "overflow" : "comparison"}
          onNext={handleComparisonUploadNext}
          onBack={handleComparisonUploadBack}
          title={uploadMode === "overflow" ? "Upload layout for second room" : undefined}
          description={
            uploadMode === "overflow"
              ? "Use this to place companies that did not fit in the first room."
              : undefined
          }
        />
      )}
      {currentScreen === "comparisonLoading" && (
        <ComparisonLoadingScreen message={loadingMessage} />
      )}
      {currentScreen === "comparisonResults" && (
        <ComparisonResultsScreen runs={comparisonPair} onBack={handleComparisonResultsBack} />
      )}
    </>
  );
}
