import { Button } from "./ui/button";
import { Upload } from "lucide-react";

interface WelcomeScreenProps {
  onNext: () => void;
}

export function WelcomeScreen({ onNext }: WelcomeScreenProps) {
  return (
    <div className="min-h-screen bg-[#1E1E1E] flex items-center justify-center p-6">
      <div className="max-w-2xl w-full text-center space-y-8">
        {/* Title */}
        <div className="space-y-4">
          <h1 className="text-white">
            Career Fair Layout Optimizer
          </h1>
          <p className="text-[#9CA3AF] text-xl">
            Upload your layout to start optimization
          </p>
        </div>

        {/* Upload Button */}
        <div className="flex flex-col items-center gap-4">
          <Button 
            onClick={onNext}
            className="bg-[#3B82F6] hover:bg-[#2563EB] text-white px-8 py-6 rounded-xl text-lg"
            size="lg"
          >
            <Upload className="mr-2 h-5 w-5" />
            Upload Layout File
          </Button>
          
          {/* Accepted Formats */}
          <p className="text-[#6B7280] text-sm">
            Accepted formats: .jpg, .png, .xlsx
          </p>
        </div>
      </div>
    </div>
  );
}
