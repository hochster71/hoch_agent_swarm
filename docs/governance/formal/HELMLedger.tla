--------------------------------- MODULE HELMLedger ---------------------------------
EXTENDS Integers, Sequences, FiniteSets, TLC

CONSTANTS GenesisHash, MaxSequence

VARIABLES ledger, currentSequence, lastHash, validationStatus

vars == <<ledger, currentSequence, lastHash, validationStatus>>

ValidLedger(l) ==
    /\ isSequence(l)
    /\ \A k \in 1..Len(l) : l[k].seq = k
    /\ \A k \in 2..Len(l) : l[k].prevHash = l[k-1].recordHash

Init ==
    /\ ledger = << >>
    /\ currentSequence = 0
    /\ lastHash = GenesisHash
    /\ validationStatus = "VALIDATED"

AppendRecord(recordHash) ==
    /\ validationStatus = "VALIDATED"
    /\ currentSequence < MaxSequence
    /\ currentSequence' = currentSequence + 1
    /\ lastHash' = recordHash
    /\ ledger' = Append(ledger, [seq |-> currentSequence', prevHash |-> lastHash, recordHash |-> recordHash])
    /\ UNCHANGED << validationStatus >>

(* Adversarial Actions *)

MutateRecord(index) ==
    /\ validationStatus = "VALIDATED"
    /\ Len(ledger) >= index /\ index >= 1
    /\ ledger' = [ledger EXCEPT ![index].recordHash = "CORRUPTED_HASH"]
    /\ UNCHANGED << currentSequence, lastHash, validationStatus >>

DeleteRecord(index) ==
    /\ validationStatus = "VALIDATED"
    /\ Len(ledger) >= index /\ index >= 1
    /\ ledger' = SubSeq(ledger, 1, index - 1)
    /\ UNCHANGED << currentSequence, lastHash, validationStatus >>

ReorderRecords ==
    /\ validationStatus = "VALIDATED"
    /\ Len(ledger) >= 2
    /\ ledger' = [ledger EXCEPT ![1] = ledger[2], ![2] = ledger[1]]
    /\ UNCHANGED << currentSequence, lastHash, validationStatus >>

ValidateLedger ==
    /\ validationStatus' = IF ValidLedger(ledger) THEN "VALIDATED" ELSE "CORRUPTED"
    /\ UNCHANGED << ledger, currentSequence, lastHash >>

Next ==
    \/ \E h \in {"hash1", "hash2", "hash3"}: AppendRecord(h)
    \/ \E idx \in 1..MaxSequence: MutateRecord(idx)
    \/ \E idx \in 1..MaxSequence: DeleteRecord(idx)
    \/ ReorderRecords
    \/ ValidateLedger

Spec == Init /\ [][Next]_vars

-------------------------------------------------------------------------------------
(* Safety Invariants *)

TypeInvariant ==
    /\ currentSequence \in 0..MaxSequence
    /\ isSequence(ledger)

SequencePositionInvariant ==
    validationStatus = "VALIDATED" =>
        \A k \in 1..Len(ledger) : ledger[k].seq = k

HashLinkInvariant ==
    validationStatus = "VALIDATED" =>
        \A k \in 2..Len(ledger) : ledger[k].prevHash = ledger[k-1].recordHash

TamperingDetected ==
    (~ValidLedger(ledger)) => (validationStatus' /= "VALIDATED")

=====================================================================================
