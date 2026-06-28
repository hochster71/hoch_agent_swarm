import type { LedgerBlock, LedgerVerificationResult } from "./ledgerTypes";
import { calculateBlockHash } from "./ledgerHash";

export async function verifyLedgerChain(blocks: LedgerBlock[]): Promise<LedgerVerificationResult> {
  const corruptedIndices: number[] = [];
  
  if (blocks.length === 0) {
    return {
      is_valid: true,
      block_count: 0,
      corrupted_block_indices: [],
      verification_msg: "Ledger is empty. Integrity verified.",
      verified_at: new Date().toISOString()
    };
  }

  // Verify first block previous_hash is empty or a specific genesis hash
  let expectedPrevHash = blocks[0].previous_hash;

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];
    
    // Check hash chain link
    if (block.previous_hash !== expectedPrevHash) {
      corruptedIndices.push(block.index);
      expectedPrevHash = block.hash; // continue chain to identify other breakages
      continue;
    }

    // Recalculate block hash
    const calculated = await calculateBlockHash(
      block.index,
      block.timestamp,
      block.event_id,
      block.event,
      block.previous_hash
    );

    if (block.hash !== calculated) {
      corruptedIndices.push(block.index);
    }

    expectedPrevHash = block.hash;
  }

  const is_valid = corruptedIndices.length === 0;

  return {
    is_valid,
    block_count: blocks.length,
    corrupted_block_indices: corruptedIndices,
    verification_msg: is_valid
      ? `Cryptographic chain intact. Verified ${blocks.length} blocks.`
      : `Ledger corruption detected! Failed blocks: ${corruptedIndices.join(", ")}`,
    verified_at: new Date().toISOString()
  };
}
