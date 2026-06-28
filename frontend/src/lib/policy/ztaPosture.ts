import { create } from "zustand";
import type { ZtaStatus, Environment } from "./policyTypes";

type ZtaPostureStore = {
  identity: ZtaStatus;
  device_posture: ZtaStatus;
  network_trust: ZtaStatus;
  session_integrity: ZtaStatus;
  environment: Environment;
  
  setIdentity: (status: ZtaStatus) => void;
  setDevicePosture: (status: ZtaStatus) => void;
  setNetworkTrust: (status: ZtaStatus) => void;
  setSessionIntegrity: (status: ZtaStatus) => void;
  setEnvironment: (env: Environment) => void;
  
  resetPosture: () => void;
};

export const useZtaPostureStore = create<ZtaPostureStore>((set) => ({
  identity: "verified",
  device_posture: "verified",
  network_trust: "verified",
  session_integrity: "verified",
  environment: "LOCAL",

  setIdentity: (status) => set({ identity: status }),
  setDevicePosture: (status) => set({ device_posture: status }),
  setNetworkTrust: (status) => set({ network_trust: status }),
  setSessionIntegrity: (status) => set({ session_integrity: status }),
  setEnvironment: (env) => set({ environment: env }),
  
  resetPosture: () =>
    set({
      identity: "verified",
      device_posture: "verified",
      network_trust: "verified",
      session_integrity: "verified",
      environment: "LOCAL",
    }),
}));
