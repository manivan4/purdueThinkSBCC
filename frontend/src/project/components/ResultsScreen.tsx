import layoutImage from "@/project/assets/layout-preview.png";
import Image from "next/image";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { ScrollArea } from "./ui/scroll-area";
import { ArrowLeft, GitCompare, Upload } from "lucide-react";
import { OptimizerRun } from "../types";

interface ResultsScreenProps {
  onBack: () => void;
  onCompare: () => void;
  onUploadMoreBooths: () => void;
  primaryRun?: OptimizerRun;
  overflowRuns: OptimizerRun[];
  comparisonRuns: OptimizerRun[];
  remainingCompanies: string[];
  totalCompanies: number;
  layoutImageUrl?: string;
  error?: string | null;
}

function scoreBadge(score: number) {
  if (score >= 0.8) return { color: "🟢", label: "Great", bg: "bg-green-500/20", text: "text-green-400" };
  if (score >= 0.6) return { color: "🟡", label: "Good", bg: "bg-yellow-500/20", text: "text-yellow-400" };
  return { color: "🔴", label: "Needs work", bg: "bg-red-500/20", text: "text-red-400" };
}

export function ResultsScreen({
  onBack,
  onCompare,
  onUploadMoreBooths,
  primaryRun,
  overflowRuns,
  comparisonRuns,
  remainingCompanies,
  totalCompanies,
  layoutImageUrl,
  error,
}: ResultsScreenProps) {
  const imageSource = primaryRun?.plotUrl ?? layoutImageUrl ?? layoutImage;
  const assignedCompanies = (primaryRun?.assignments ?? []).slice().sort((a, b) => a.booth - b.booth);
  const scoreInfo = scoreBadge(primaryRun?.score ?? 0);
  const placedCount = primaryRun?.placedCount ?? 0;
  const boothCount = primaryRun?.boothCount ?? 0;

  return (
    <div className="min-h-screen bg-[#1E1E1E] p-6">
      <div className="max-w-7xl mx-auto mb-8">
        <Button
          onClick={onBack}
          variant="ghost"
          className="text-[#9CA3AF] hover:text-white mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Start
        </Button>
        <h1 className="text-white">
          Optimized Layout Results
        </h1>
        {error && (
          <p className="text-red-400 text-sm mt-2">
            {error}
          </p>
        )}
      </div>

      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-4">
            <div className="bg-[#2B2B2B] rounded-xl p-6">
              <div className="bg-white rounded-lg p-4 relative overflow-hidden">
                <div className="relative">
                  {typeof imageSource === "string" ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={imageSource as string}
                      alt="Career Fair Layout"
                      className="w-full h-auto"
                    />
                  ) : (
                    <Image
                      src={imageSource}
                      alt="Career Fair Layout"
                      className="w-full h-auto"
                      sizes="(min-width: 1024px) 640px, 100vw"
                      priority
                      unoptimized={true}
                    />
                  )}
                </div>
              </div>
              <p className="text-[#9CA3AF] text-sm mt-4 text-center">
                {primaryRun?.roomLabel ?? "Primary layout"} {primaryRun?.layoutName ? `(${primaryRun.layoutName})` : ""}
              </p>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-[#2B2B2B] rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-white">
                  Assigned Companies
                </h2>
                <p className="text-sm text-[#9CA3AF]">
                  {placedCount} placed / {boothCount} booths
                </p>
              </div>
              <ScrollArea className="h-[340px] pr-2">
                <div className="space-y-3">
                  {assignedCompanies.map((item) => (
                    <div
                      key={`${item.booth}-${item.company}`}
                      className="flex items-center justify-between p-3 bg-[#1E1E1E]/80 rounded-lg"
                    >
                      <span className="text-[#3B82F6]">
                        Booth {item.booth}
                      </span>
                      <span className="text-white">
                        {item.company}
                      </span>
                    </div>
                  ))}
                  {assignedCompanies.length === 0 && (
                    <p className="text-[#9CA3AF] text-sm">
                      No companies placed yet. Upload your layout and company list to continue.
                    </p>
                  )}
                </div>
              </ScrollArea>
              {remainingCompanies.length > 0 && (
                <p className="text-[#9CA3AF] text-sm mt-4">
                  {remainingCompanies.length} companies still need booths.
                </p>
              )}
            </div>

            <div className="bg-[#2B2B2B] rounded-xl p-6">
              <h2 className="text-white mb-4">
                Spacing Metrics
              </h2>
              <div className="flex items-center justify-between">
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <span className="text-white text-4xl">
                      {(primaryRun?.score ?? 0).toFixed(2)}
                    </span>
                    <Badge className={`${scoreInfo.bg} ${scoreInfo.text} border-0`}>
                      {scoreInfo.color} {scoreInfo.label}
                    </Badge>
                  </div>
                  <p className="text-[#9CA3AF] text-sm">
                    Based on minimum booth spacing ({(primaryRun?.minDistance ?? 0).toFixed(2)} units)
                  </p>
                </div>
                <div className="text-right text-sm text-[#9CA3AF] space-y-1">
                  <p>Total companies: <span className="text-white">{totalCompanies}</span></p>
                  <p>Placed here: <span className="text-white">{placedCount}</span></p>
                  <p>Open booths: <span className="text-white">{Math.max(boothCount - placedCount, 0)}</span></p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {overflowRuns.length > 0 && (
          <div className="mt-10 space-y-4">
            <h2 className="text-white text-xl">Additional Rooms</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {overflowRuns.map((run) => {
                const badge = scoreBadge(run.score);
                return (
                  <div key={run.id} className="bg-[#2B2B2B] rounded-xl p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-white">{run.roomLabel ?? "Additional room"}</p>
                        <p className="text-[#6B7280] text-sm">{run.layoutName}</p>
                      </div>
                      <Badge className={`${badge.bg} ${badge.text} border-0`}>
                        {badge.color} {badge.label}
                      </Badge>
                    </div>
                    <p className="text-[#9CA3AF] text-sm">Placed {run.placedCount} of {run.boothCount} booths</p>
                    <p className="text-[#9CA3AF] text-sm">Min spacing: <span className="text-white">{run.minDistance.toFixed(2)}</span></p>
                    {run.plotUrl && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={run.plotUrl} alt={run.layoutName} className="rounded-lg border border-[#111827]" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {comparisonRuns.length > 0 && (
          <div className="mt-10 space-y-4">
            <h2 className="text-white text-xl">Saved Comparisons</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {comparisonRuns.map((run) => {
                const badge = scoreBadge(run.score);
                return (
                  <div key={run.id} className="bg-[#2B2B2B] rounded-xl p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-white truncate">{run.layoutName}</p>
                      <Badge className={`${badge.bg} ${badge.text} border-0`}>
                        {badge.color} {badge.label}
                      </Badge>
                    </div>
                    <p className="text-[#9CA3AF] text-sm">Score: <span className="text-white">{run.score.toFixed(2)}</span></p>
                    <p className="text-[#9CA3AF] text-sm">Placed: <span className="text-white">{run.placedCount}</span></p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="flex flex-col gap-4 items-center pt-8">
          {remainingCompanies.length > 0 && (
            <div className="bg-[#2B2B2B] rounded-xl p-5 flex flex-col gap-3 w-full max-w-4xl">
              <div className="flex items-center justify-between">
                <p className="text-white text-lg">
                  {remainingCompanies.length} companies still need booths
                </p>
                <Badge className="bg-yellow-500/20 text-yellow-300 border-0">
                  Capacity exceeded
                </Badge>
              </div>
              <p className="text-[#9CA3AF] text-sm">
                Upload another layout with more booths to place the remaining companies.
              </p>
              <div className="flex flex-wrap gap-2">
                {remainingCompanies.slice(0, 6).map((company) => (
                  <Badge key={company} variant="secondary">
                    {company}
                  </Badge>
                ))}
                {remainingCompanies.length > 6 && (
                  <span className="text-[#9CA3AF] text-sm">
                    +{remainingCompanies.length - 6} more
                  </span>
                )}
              </div>
              <div className="flex gap-3">
                <Button
                  onClick={onUploadMoreBooths}
                  className="bg-[#3B82F6] hover:bg-[#2563EB] text-white"
                >
                  <Upload className="mr-2 h-4 w-4" />
                  Upload another room layout
                </Button>
                <Button
                  onClick={onCompare}
                  variant="outline"
                  className="text-[#9CA3AF] border-[#444444] hover:bg-[#2B2B2B] hover:text-white"
                >
                  <GitCompare className="mr-2 h-4 w-4" />
                  Compare layouts
                </Button>
              </div>
            </div>
          )}

          {remainingCompanies.length === 0 && (
            <Button
              onClick={onCompare}
              className="bg-[#3B82F6] hover:bg-[#2563EB] text-white px-8 py-6 rounded-xl text-lg"
              size="lg"
            >
              <GitCompare className="mr-2 h-5 w-5" />
              Compare Another Layout
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
