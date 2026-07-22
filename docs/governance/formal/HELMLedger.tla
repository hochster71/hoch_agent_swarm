--------------------------------- MODULE HELMLedger ---------------------------------
EXTENDS Integers, Sequences, FiniteSets, TLC

CONSTANTS GenesisHash, MaxSequence

VARIABLES ledger, currentSequence, lastHash

Init ==
    /\ ledger = << >>
    /\ currentSequence = 0
    /\ lastHash = GenesisHash

AppendRecord(recordHash) ==
    /\ currentSequence < MaxSequence
    /\ currentSequence' = currentSequence + 1
    /\ lastHash' = recordHash
    /\ ledger' = Append(ledger, [seq |-> currentSequence', prevHash |-> lastHash, recordHash |-> recordHash])

Next ==
    \E h \in {"hash1", "hash2", "hash3"}: AppendRecord(h)

-------------------------------------------------------------------------------------
(* Safety Invariants *)

TypeInvariant ==
    /\ currentSequence \in 0..MaxSequence
    /\ isSequence(ledger)

AppendOnlyInvariant ==
    \A k \in 1..Len(ledger) :
        ledger[k].seq = k

SequenceMonotonicity ==
    \A k \in 1..(Len(ledger)-1) :
        ledger[k+1].seq = ledger[k].seq + 1

HashLinkInvariant ==
    \A k \in 2..Len(ledger) :
        ledger[k].prevHash = ledger[k-1].recordHash

=====================================================================================
