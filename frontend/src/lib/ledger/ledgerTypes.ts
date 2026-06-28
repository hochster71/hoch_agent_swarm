import type { AuditEvent } from "@/lib/audit/auditTypes";

export type LedgerBlock = {
  index: number;
  timestamp: string;
  event_id: string;
  event: AuditEvent;
  previous_hash: string;
  hash: string;
};

export type LedgerVerificationResult = {
  is_valid: boolean;
  block_count: number;
  corrupted_block_indices: number[];
  verification_msg: string;
  verified_at: string;
};
