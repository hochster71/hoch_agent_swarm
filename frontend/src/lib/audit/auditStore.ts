import { create } from "zustand";
import type { AuditEvent } from "./auditTypes";

type AuditStore = {
  events: AuditEvent[];
  isDrawerOpen: boolean;
  addEvent: (event: AuditEvent) => void;
  addEvents: (events: AuditEvent[]) => void;
  clearEvents: () => void;
  openDrawer: () => void;
  closeDrawer: () => void;
  toggleDrawer: () => void;
};

export const useAuditStore = create<AuditStore>((set) => ({
  events: [],
  isDrawerOpen: false,
  addEvent: (event) =>
    set((state) => ({
      events: [event, ...state.events],
    })),
  addEvents: (events) =>
    set((state) => ({
      events: [...events, ...state.events],
    })),
  clearEvents: () => set({ events: [] }),
  openDrawer: () => set({ isDrawerOpen: true }),
  closeDrawer: () => set({ isDrawerOpen: false }),
  toggleDrawer: () =>
    set((state) => ({
      isDrawerOpen: !state.isDrawerOpen,
    })),
}));
