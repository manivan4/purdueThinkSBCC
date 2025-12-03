import { Progress } from "./ui/progress";
import { Loader2 } from "lucide-react";

interface ComparisonLoadingScreenProps {
  message?: string;
  subtext?: string;
}

export function ComparisonLoadingScreen({ message, subtext }: ComparisonLoadingScreenProps) {
  return (
    <div className="min-h-screen bg-[#1E1E1E] relative flex items-center justify-center p-6">
      {/* Dim Background Overlay */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm"></div>

      {/* Loading Content */}
      <div className="relative z-10 max-w-xl w-full space-y-8">
        {/* Spinner */}
        <div className="flex justify-center">
          <Loader2 className="h-16 w-16 text-[#3B82F6] animate-spin" />
        </div>

        {/* Message */}
        <div className="text-center space-y-4">
          <h2 className="text-white text-2xl">
            {message ?? "Analyzing and comparing both layouts…"}
          </h2>
          {subtext && (
            <p className="text-[#9CA3AF] text-sm">
              {subtext}
            </p>
          )}
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <Progress value={75} className="h-2" />
          <p className="text-[#9CA3AF] text-sm text-center">
            {subtext ?? "Computing optimization differences..."}
          </p>
        </div>
      </div>
    </div>
  );
}
