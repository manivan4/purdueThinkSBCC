export type RunMode = "primary" | "overflow" | "comparison";

export type Assignment = {
  company: string;
  booth: number;
  x?: number;
  y?: number;
};

export type OptimizerRun = {
  id: string;
  mode: RunMode;
  layoutName: string;
  roomLabel?: string;
  boothCount: number;
  placedCount: number;
  minDistance: number;
  score: number;
  assignments: Assignment[];
  unplacedCompanies: string[];
  bigCompanies: string[];
  plotUrl?: string;
  stderr?: string;
  stdout?: string;
};
