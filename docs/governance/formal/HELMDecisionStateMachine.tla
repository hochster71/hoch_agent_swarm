--------------------------- MODULE HELMDecisionStateMachine ---------------------------
EXTENDS Integers, Sequences, TLC

CONSTANTS MinBurnInDays

VARIABLES elapsedTimeDays, missingIntervals, replayDivergenceCount, qualificationStatus

Init ==
    /\ elapsedTimeDays = 0
    /\ missingIntervals = 0
    /\ replayDivergenceCount = 0
    /\ qualificationStatus = "BURNIN_HARNESS_BOOTSTRAP_IMPLEMENTED"

AdvanceTime(days) ==
    /\ elapsedTimeDays' = elapsedTimeDays + days
    /\ UNCHANGED << missingIntervals, replayDivergenceCount >>
    /\ IF elapsedTimeDays' >= MinBurnInDays /\ missingIntervals = 0 /\ replayDivergenceCount = 0
       THEN qualificationStatus' = "QUALIFIED_30DAY_BURNIN"
       ELSE qualificationStatus' = qualificationStatus

Next ==
    AdvanceTime(1)

-------------------------------------------------------------------------------------
(* Safety Invariants *)

NoEarlyQualification ==
    qualificationStatus = "QUALIFIED_30DAY_BURNIN" => elapsedTimeDays >= MinBurnInDays

NoQualificationWithGaps ==
    qualificationStatus = "QUALIFIED_30DAY_BURNIN" => missingIntervals = 0

NoQualificationWithReplayDivergence ==
    qualificationStatus = "QUALIFIED_30DAY_BURNIN" => replayDivergenceCount = 0

=====================================================================================
