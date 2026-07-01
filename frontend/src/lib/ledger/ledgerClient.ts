import { create } from "zustand";
import type { LedgerBlock, LedgerVerificationResult } from "./ledgerTypes";

type LedgerStore = {
  blocks: LedgerBlock[];
  verification: LedgerVerificationResult | null;
  isLoading: boolean;
  syncing: boolean;
  
  fetchBlocks: () => Promise<void>;
  verifyLedger: () => Promise<void>;
};

export const useLedgerStore = create<LedgerStore>((set) => ({
  blocks: [],
  verification: null,
  isLoading: false,
  syncing: false,

  fetchBlocks: async () => {
    set({ isLoading: true });
    try {
      const response = await fetch("/api/ledger/blocks");
      if (!response.ok) throw new Error("Failed to load ledger blocks");
      const blocks = await response.json();
      set({ blocks });
    } catch (error) {
      console.error("Error loading ledger blocks:", error);
    } finally {
      set({ isLoading: false });
    }
  },

  verifyLedger: async () => {
    set({ syncing: true });
    try {
      const response = await fetch("/api/ledger/verify");
      if (!response.ok) throw new Error("Failed to verify ledger on backend");
      const verification = await response.json();
      set({ verification });
    } catch (error) {
      console.error("Error verifying ledger:", error);
    } finally {
      set({ syncing: false });
    }
  }
}));
