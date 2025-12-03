import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { OptimizerRun } from "../types";

interface ComparisonResultsScreenProps {
  runs: OptimizerRun[];
  onBack: () => void;
  highlightId?: string;
}

function statusForScore(score: number) {
  if (score >= 0.8) return { color: "🟢", label: "Great", bg: "bg-green-500/20", text: "text-green-400" };
  if (score >= 0.6) return { color: "🟡", label: "Good", bg: "bg-yellow-500/20", text: "text-yellow-400" };
  return { color: "🔴", label: "Needs work", bg: "bg-red-500/20", text: "text-red-400" };
}

export function ComparisonResultsScreen({ runs, onBack, highlightId }: ComparisonResultsScreenProps) {
  if (runs.length < 2) {
    return (
      <div className="min-h-screen bg-[#1E1E1E] flex items-center justify-center p-6">
        <div className="max-w-xl w-full text-center space-y-4">
          <h1 className="text-white">Need another layout to compare</h1>
          <p className="text-[#9CA3AF]">Upload at least two layouts to view comparison results.</p>
          <Button onClick={onBack} className="bg-[#3B82F6] hover:bg-[#2563EB] text-white">
            Back
          </Button>
        </div>
      </div>
    );
  }

  const sorted = [...runs].sort((a, b) => b.score - a.score);
  const [best, second] = sorted;
  const difference = second && second.score > 0 ? (((best.score - second.score) / second.score) * 100).toFixed(0) : "0";
  const highlighted = highlightId ? runs.find((r) => r.id === highlightId) ?? best : best;

  return (
    <div className="min-h-screen bg-[#1E1E1E] p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <Button
          onClick={onBack}
          variant="ghost"
          className="text-[#9CA3AF] hover:text-white mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <h1 className="text-white">
          Layout Comparison Results
        </h1>
      </div>

      <div className="max-w-7xl mx-auto space-y-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {[best, second].map((layout) => {
            const status = statusForScore(layout.score);
            const isWinner = layout.id === best.id;
            const isHighlighted = layout.id === highlighted.id;
            return (
              <div key={layout.id} className="space-y-4">
                <div
                  className="bg-[#2B2B2B] rounded-xl p-6 relative"
                  style={{
                    boxShadow: isWinner ? "0 0 30px rgba(34, 197, 94, 0.4)" : undefined,
                    border: isHighlighted ? "1px solid rgba(59,130,246,0.6)" : undefined,
                  }}
                >
                  {isWinner && (
                    <div className="absolute -top-3 -right-3 bg-green-500 rounded-full p-2">
                      <CheckCircle2 className="h-5 w-5 text-white" />
                    </div>
                  )}
                  <div className="bg-white rounded-lg p-4 mb-4">
                    {layout.plotUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={layout.plotUrl}
                        alt={`${layout.layoutName} plot`}
                        className="w-full h-auto"
                      />
                    ) : (
                      <div className="text-center text-sm text-[#6B7280]">Plot preview not available</div>
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="text-[#9CA3AF]">
                      <p>{layout.layoutName}</p>
                      {layout.roomLabel && <p className="text-xs text-[#6B7280]">{layout.roomLabel}</p>}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-white">Score: {layout.score.toFixed(2)}</span>
                      <Badge className={`${status.bg} ${status.text} border-0`}>
                        {status.color} {status.label}
                      </Badge>
                    </div>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-[#9CA3AF]">
                    <p>Booths: <span className="text-white">{layout.boothCount}</span></p>
                    <p>Placed: <span className="text-white">{layout.placedCount}</span></p>
                    <p>Min distance: <span className="text-white">{layout.minDistance.toFixed(2)}</span></p>
                    <p>Unplaced: <span className="text-white">{layout.unplacedCompanies.length}</span></p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="bg-[#2B2B2B] rounded-xl p-6 space-y-4">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="h-6 w-6 text-green-400 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-white text-xl mb-2">
                Best Layout: {best.layoutName} ({best.score.toFixed(2)})
              </h3>
              <p className="text-[#9CA3AF] mb-2">
                <span className="text-[#3B82F6]">Difference:</span> +{difference}% better optimization than next best.
              </p>
              <p className="text-[#9CA3AF]">
                <span className="text-[#3B82F6]">Recommendation:</span> Keep {best.layoutName} for final design.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
