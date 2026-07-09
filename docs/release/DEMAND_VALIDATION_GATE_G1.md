# G1: Demand Validation Gate Checklist

This document defines the fail-closed check requirements for the G1 Demand Validation Gate. 

> [!IMPORTANT]
> **FAIL-CLOSED POLICY**: At least one verified commercial demand signal (willingness-to-pay) must be recorded and signed off by the founder before the product build phase is unlocked.

## Willingness-to-Pay (WTP) Signals

Verify presence of at least one checked item below:

*   `[x]` **Stripe Checkout Intent**: A customer has clicked a "Purchase" button and initiated a checkout session (captured in Stripe Sandbox logging).
*   `[x]` **Waitlist Sign-up**: A prospective user has signed up for the early access waitlist with email verification.
*   `[ ]` **TestFlight / Google Play Beta Request**: A target user has requested access to the closed pre-release build.
*   `[x]` **Direct Customer Quote**: A target customer has written a testimonial confirming they would pay the target price (e.g. $9/mo) for the proposed solution.
*   `[ ]` **Letter of Intent (LOI) / Written Commitment**: A written corporate or individual agreement to buy the software upon release.
*   `[x]` **Target User Interview Price Check**: An interview transcript with a qualified user confirming that the proposed solution fits their budget and solves a critical pain point.

## Verification Checklist

1.  `[x]` Define target customer profile and primary problem statement.
2.  `[x]` Establish target price point ($9/mo SaaS companion model).
3.  `[x]` Gather evidence files and place them under `docs/evidence/demand/`.
4.  `[x]` Founder (Michael) signs off to close the gate.
