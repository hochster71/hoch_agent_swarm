--------------------------- MODULE HELMDecisionStateMachine ---------------------------
EXTENDS Integers, Sequences, TLC

CONSTANTS MinBurnInDays

VARIABLES elapsedTimeDays, missingIntervals, replayDivergenceCount, qualificationStatus

Init ==
    /\ elapsedTimeDays = 0
    /\ missingIntervals = 0
    /\ replayDivergenceCount = 0
    /\ qualificationStatus = "BURNIN_IN_PROGRESS"

AdvanceTime(days) ==
    /\ elapsedTimeDays' = elapsedTimeDays + days
    /\ UNCHANGED << missingIntervals, replayDivergenceCount >>
    /\ IF elapsedTimeDays' >= MinBurnInDays /\ missingIntervals = 0 /\ replayDivergenceCount = 0
       THEN qualificationStatus' = "FOUNDER_AUTHORIZATION_REQUIRED"
       ELSE qualificationStatus' = qualificationStatus

RecordGap ==
    /\ missingIntervals' = missingIntervals + 1
    /\ qualificationStatus' = "WITHHELD"
    /\ UNCHANGED << elapsedTimeDays, replayDivergenceCount >>

RecordReplayDivergence ==
    /\ replayDivergenceCount' = replayDivergenceCount + 1
    /\ qualificationStatus' = "WITHHELD"
    /\ UNCHANGED << elapsedTimeDays, missingIntervals >>

RequestFounderAuthorization ==
    /\ elapsedTimeDays >= MinBurnInDays
    /\ missingIntervals = 0
    /\ replayDivergenceCount = 0
    /\ qualificationStatus' = "FOUNDER_AUTHORIZATION_REQUIRED"
    /\ UNCHANGED << elapsedTimeDays, missingIntervals, replayDivergenceCount >>

GrantFounderAuthorization ==
    /\ qualificationStatus = "FOUNDER_AUTHORIZATION_REQUIRED"
    /\ qualificationStatus' = "QUALIFIED_30DAY_BURNIN"
    /\ UNCHANGED << elapsedTimeDays, missingIntervals, replayDivergenceCount >>

Next ==
    \/ AdvanceTime(1)
    \/ RecordGap
    \/ RecordReplayDivergence
    \/ RequestFounderAuthorization
    \/ GrantFounderAuthorization

-------------------------------------------------------------------------------------
(* Safety Invariants *)

NoEarlyQualification ==
    qualificationStatus = "QUALIFIED_30DAY_BURNIN" => elapsedTimeDays >= MinBurnInDays

NoQualificationWithGaps ==
    qualificationStatus = "QUALIFIED_30DAY_BURNIN" => missingIntervals = 0

NoQualificationWithReplayDivergence ==
    qualificationStatus = "QUALIFIED_30DAY_BURNIN" => replayDivergenceCount = 0

=====================================================================================
