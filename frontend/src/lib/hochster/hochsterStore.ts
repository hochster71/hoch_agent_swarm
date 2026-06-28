import { create } from "zustand";

type HochsterStore = {
  selectedRequestId: string | null;
  selectedSolutionId: string | null;
  selectRequest: (requestId: string) => void;
  selectSolution: (solutionId: string) => void;
};

export const useHochsterStore = create<HochsterStore>((set) => ({
  selectedRequestId: null,
  selectedSolutionId: null,
  selectRequest: (requestId) => set({ selectedRequestId: requestId }),
  selectSolution: (solutionId) => set({ selectedSolutionId: solutionId }),
}));
