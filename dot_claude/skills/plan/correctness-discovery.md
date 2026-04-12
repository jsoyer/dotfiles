# Correctness Discovery Framework

Answer these six questions before writing any PRD. They establish the correctness contract and reveal hidden assumptions.

## The Six Questions

### 1. Audience

**Question:** Who uses this output and what decision will they make based on it?
**Why it matters:** Different audiences need different things. An API consumed by a mobile app needs stability; an internal tool for developers can iterate faster.
**Example:** "End users viewing the pricing page need to see accurate prices to make a purchase decision."

### 2. Failure Definition

**Question:** What would make this output useless?
**Why it matters:** Knowing what "useless" looks like sets the minimum quality bar.
**Example:** "If the pricing page shows stale prices or broken formatting, users can't compare plans."

### 3. Danger Definition

**Question:** What would make this output actively harmful?
**Why it matters:** Some failures are worse than useless — they cause damage. Identify these upfront.
**Example:** "If the pricing page shows wrong prices that are lower than actual, we commit to pricing we can't honor."

### 4. Uncertainty Policy

**Question:** What should the AI do when uncertain? (Guess / Flag / Stop)
**Why it matters:** Different tasks have different tolerance for uncertainty.
**Options:**

- **Guess:** Acceptable for low-risk tasks (CSS, copy). Make your best judgment and move on.
- **Flag:** Document the assumption and continue. Reviewer catches it later.
- **Stop:** High-risk areas (auth, data, billing). Ask before proceeding.

### 5. Risk Tolerance

**Question:** What is worse — a confident wrong answer or a refusal to answer?
**Why it matters:** Some domains prefer false negatives (security: "block if unsure"), others prefer false positives (UX: "show something rather than nothing").
**Example:** "For billing: a wrong charge is worse than showing an error. Prefer refusal over wrong answer."

### 6. Verification

**Question:** How would you check if the output is correct?
**Why it matters:** If you can't describe verification, the spec is incomplete.
**Example:** "Run E2E test that loads pricing page, verifies all 4 plan cards render with correct prices from the pricing config."
