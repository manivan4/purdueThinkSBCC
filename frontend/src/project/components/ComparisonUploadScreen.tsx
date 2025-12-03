import { Button } from "./ui/button";
import { Upload } from "lucide-react";
import { useRef, useState } from "react";

interface ComparisonUploadScreenProps {
  onNext: (file: File) => void;
  onBack: () => void;
  mode?: "comparison" | "overflow";
  title?: string;
  description?: string;
  remainingCount?: number;
}

export function ComparisonUploadScreen({
  onNext,
  onBack,
  mode = "comparison",
  title,
  description,
  remainingCount,
}: ComparisonUploadScreenProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleContinue = () => {
    if (!selectedFile) {
      setError("Please choose a layout file to continue.");
      return;
    }
    onNext(selectedFile);
  };

  const displayTitle =
    title ||
    (mode === "overflow" ? "Add Another Room Layout" : "Compare Another Layout");
  const displayDescription =
    description ||
    (mode === "overflow"
      ? "Upload a second room (gym) layout to place any remaining companies."
      : "Upload a second layout to compare performance and overlap.");

  return (
    <div className="min-h-screen bg-[#1E1E1E] flex items-center justify-center p-6">
      <div className="max-w-2xl w-full text-center space-y-8">
        {/* Title */}
        <div className="space-y-4">
          <h1 className="text-white">
            {displayTitle}
          </h1>
          <p className="text-[#9CA3AF] text-xl">
            {displayDescription}
          </p>
          {typeof remainingCount === "number" && remainingCount > 0 && (
            <p className="text-[#FACC15] text-sm">
              {remainingCount} companies still need booths. Add a layout with more booths to place them.
            </p>
          )}
        </div>

        {/* Upload Button */}
        <div className="flex flex-col items-center gap-4">
          <input
            ref={fileInputRef}
            type="file"
            accept=".jpg,.jpeg,.png,.xlsx"
            onChange={handleFileChange}
            className="hidden"
          />
          
          <Button 
            onClick={handleFileClick}
            className="bg-[#3B82F6] hover:bg-[#2563EB] text-white px-8 py-6 rounded-xl text-lg"
            size="lg"
          >
            <Upload className="mr-2 h-5 w-5" />
            Upload Second Layout
          </Button>

          {selectedFile && (
            <p className="text-[#9CA3AF] text-sm">
              Selected: {selectedFile.name}
            </p>
          )}
          
          {/* Accepted Formats */}
          <p className="text-[#6B7280] text-sm">
            Accepted formats: .jpg / .png / .xlsx
          </p>

          {error && (
            <p className="text-red-400 text-sm">
              {error}
            </p>
          )}
        </div>

        {/* Back Button */}
        <div className="pt-4 flex items-center justify-center gap-3">
          <Button
            onClick={onBack}
            variant="outline"
            className="text-[#9CA3AF] border-[#444444] hover:bg-[#2B2B2B] hover:text-white"
          >
            Back to Results
          </Button>
          <Button
            onClick={handleContinue}
            className="bg-[#10B981] hover:bg-[#059669] text-white px-6"
          >
            Continue
          </Button>
        </div>
      </div>
    </div>
  );
}
