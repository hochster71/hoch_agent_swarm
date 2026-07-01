import { create } from "zustand";
import type { CommandPreview, CommandMode } from "./commandTypes";
import { generatePreview } from "./commandExecution";

type CommandStore = {
  preview: CommandPreview | null;
  isOpen: boolean;
  selectedMode: CommandMode | "override";
  openPreview: (text: string) => void;
  closePreview: () => void;
  setMode: (mode: CommandMode | "override") => void;
};

export const useCommandStore = create<CommandStore>((set) => ({
  preview: null,
  isOpen: false,
  selectedMode: "simulate",
  openPreview: (text) => {
    const preview = generatePreview(text);
    set({
      preview,
      isOpen: true,
      selectedMode: "simulate" // Reset mode to Simulate by default when previewing
    });
  },
  closePreview: () => set({ isOpen: false, preview: null }),
  setMode: (mode) => set({ selectedMode: mode })
}));
