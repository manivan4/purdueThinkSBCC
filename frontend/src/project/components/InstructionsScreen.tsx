import { Button } from "./ui/button";
import { ArrowRight, Upload } from "lucide-react";
import { useRef, useState } from "react";

interface InstructionsScreenProps {
  onNext: (file: File) => void;
}

export function InstructionsScreen({ onNext }: InstructionsScreenProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const instructions = [
    "Include booth numbers in your layout.",
    "Draw lines between booths that are competing.",
    "Save and upload your layout file."
  ];

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleContinue = () => {
    if (selectedFile) {
      onNext(selectedFile);
    }
  };

  return (
    <div className="min-h-screen bg-[#1E1E1E] flex items-center justify-center p-6">
      <div className="max-w-2xl w-full">
        {/* Card Container */}
        <div className="bg-[#2B2B2B] rounded-xl p-6 space-y-8">
          {/* Title */}
          <h1 className="text-white text-center">
            Before You Upload
          </h1>

          {/* Numbered List */}
          <div className="space-y-6">
            {instructions.map((instruction, index) => (
              <div key={index} className="flex items-start gap-4">
                {/* Number Circle */}
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[#3B82F6] flex items-center justify-center">
                  <span className="text-white">{index + 1}</span>
                </div>
                {/* Instruction Text */}
                <p className="text-white text-lg pt-1.5">
                  {instruction}
                </p>
              </div>
            ))}
          </div>

          {/* Upload Section */}
          <div className="flex flex-col items-center gap-4 pt-4">
            <input
              ref={fileInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.xlsx"
              onChange={handleFileChange}
              className="hidden"
            />
            
            {!selectedFile ? (
              <Button 
                onClick={handleFileClick}
                className="bg-[#3B82F6] hover:bg-[#2563EB] text-white px-8 py-6 rounded-xl text-lg"
                size="lg"
              >
                <Upload className="mr-2 h-5 w-5" />
                Upload Layout
              </Button>
            ) : (
              <div className="space-y-4 w-full">
                {/* Selected File Display */}
                <div className="bg-[#1E1E1E] rounded-lg p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Upload className="h-5 w-5 text-[#3B82F6]" />
                    <span className="text-white">{selectedFile.name}</span>
                  </div>
                  <Button
                    onClick={handleFileClick}
                    variant="ghost"
                    className="text-[#3B82F6] hover:text-[#2563EB] hover:bg-[#2B2B2B]"
                    size="sm"
                  >
                    Change
                  </Button>
                </div>
                
                {/* Continue Button */}
                <Button 
                  onClick={handleContinue}
                  className="bg-[#3B82F6] hover:bg-[#2563EB] text-white px-8 py-6 rounded-xl text-lg w-full"
                  size="lg"
                >
                  Continue to Analysis
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </div>
            )}
            
            {/* Accepted Formats */}
            <p className="text-[#6B7280] text-sm">
              Accepted formats: .jpg / .png / .xlsx
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
