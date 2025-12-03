import { useRef, useState } from "react";
import * as XLSX from "xlsx";
import { Button } from "./ui/button";
import { Upload } from "lucide-react";

interface CompanyUploadScreenProps {
  onNext: (companies: string[]) => void;
  onBack: () => void;
}

export function CompanyUploadScreen({ onNext, onBack }: CompanyUploadScreenProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [companies, setCompanies] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isParsing, setIsParsing] = useState(false);

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const parseCompaniesFromFile = async (file: File) => {
    setIsParsing(true);
    setError(null);
    try {
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: "array" });
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
      if (!firstSheet) {
        throw new Error("No sheets found in the Excel file.");
      }

      const rows = XLSX.utils.sheet_to_json<(string | number | null)[]>(firstSheet, {
        header: 1,
        defval: null,
      });

      const names = rows
        .map((row) => {
          const value = row?.[0];
          if (typeof value === "string") return value.trim();
          if (typeof value === "number") return value.toString();
          return "";
        })
        .filter((name) => name.length > 0);

      const uniqueNames = Array.from(new Set(names));

      if (uniqueNames.length === 0) {
        throw new Error("No company names detected in the first column.");
      }

      setCompanies(uniqueNames);
      onNext(uniqueNames);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Unable to read the Excel file.";
      setError(message);
      setCompanies([]);
    } finally {
      setIsParsing(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      parseCompaniesFromFile(file);
    }
  };

  return (
    <div className="min-h-screen bg-[#1E1E1E] flex items-center justify-center p-6">
      <div className="max-w-2xl w-full text-center space-y-8">
        <div className="space-y-3">
          <h1 className="text-white">Upload Company List</h1>
          <p className="text-[#9CA3AF] text-lg">
            Provide an Excel file (.xlsx) with company names in the first column. One
            company will be placed per booth.
          </p>
        </div>

        <div className="flex flex-col items-center gap-4">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx"
            onChange={handleFileChange}
            className="hidden"
          />

          <Button
            onClick={handleFileClick}
            className="bg-[#3B82F6] hover:bg-[#2563EB] text-white px-8 py-6 rounded-xl text-lg"
            size="lg"
            disabled={isParsing}
          >
            <Upload className="mr-2 h-5 w-5" />
            {selectedFile ? "Replace Excel File" : "Upload Excel File"}
          </Button>

          {selectedFile && (
            <div className="bg-[#2B2B2B] w-full rounded-lg p-4 text-left space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-white">{selectedFile.name}</span>
                <span className="text-[#9CA3AF] text-sm">
                  {companies.length > 0 ? `${companies.length} companies detected` : "Parsing..."}
                </span>
              </div>
              <p className="text-[#6B7280] text-sm">
                Make sure company names are in the first column of the sheet.
              </p>
            </div>
          )}

          {error && (
            <p className="text-red-400 text-sm">
              {error}
            </p>
          )}
        </div>

        <div className="flex justify-between">
          <Button
            onClick={onBack}
            variant="outline"
            className="text-[#9CA3AF] border-[#444444] hover:bg-[#2B2B2B] hover:text-white"
          >
            Back
          </Button>
          <Button
            onClick={() => companies.length > 0 && onNext(companies)}
            className="bg-[#10B981] hover:bg-[#059669] text-white px-8"
            disabled={companies.length === 0 || isParsing}
          >
            Continue to Analysis
          </Button>
        </div>
      </div>
    </div>
  );
}
