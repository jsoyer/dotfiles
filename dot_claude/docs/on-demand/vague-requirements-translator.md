# Vague Requirements Translator

When a requirement uses vague language, translate it into measurable, testable criteria before proceeding.

## Translation Table

| Vague Requirement          | Questions to Ask                                                     | Measurable Translation                                                                                             |
| -------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| "Make it fast"             | Fast compared to what? What's the current speed? Where is it slow?   | "Page load under 2s (LCP). API response under 200ms (p95)."                                                        |
| "Make it secure"           | Against what threats? What data is sensitive? What compliance?       | "OWASP Top 10 addressed. No PII in logs. CSP headers configured."                                                  |
| "Make it scalable"         | Scale to what? Users? Data? Requests? Timeline?                      | "Handle 10K concurrent users. Response time degrades <20% at 5x load."                                             |
| "Make it user-friendly"    | Friendly for whom? What tasks? What's unfriendly now?                | "Core task completable in <3 clicks. No error messages without recovery actions."                                  |
| "Make it robust"           | Robust against what? Network failures? Bad input? Crashes?           | "Graceful degradation on network loss. Input validation on all forms. Error boundaries prevent full-page crashes." |
| "Make it maintainable"     | Maintainable by whom? What changes are expected?                     | "New developer can add a feature in area X within 1 day. All modules have <500 lines."                             |
| "Improve the design"       | What's wrong with current design? Who complained? What goals?        | "Increase conversion rate by X%. Match brand guidelines v2. Fix mobile navigation issues."                         |
| "Clean up the code"        | What's messy? Performance issue? Readability? Bugs?                  | "Remove dead code (X files). Extract shared logic into Y utility. Add types to Z module."                          |
| "Add error handling"       | Which errors? User-facing? Internal? What should happen?             | "All API calls wrapped in try/catch. User sees friendly error message. Errors logged with context."                |
| "Make it responsive"       | Which breakpoints? Which devices? What breaks currently?             | "Renders correctly at 375px, 768px, 1024px, 1440px. No horizontal scroll. Touch targets >=44px."                   |
| "Add tests"                | Unit? Integration? E2E? What coverage target? Critical paths?        | "Unit tests for business logic (>80% coverage). E2E for critical user flows (sign up, purchase)."                  |
| "Optimize performance"     | Which metric? Where is it slow? What's the budget?                   | "Reduce bundle size from X to Y. LCP from Xs to Ys. Eliminate layout shifts (CLS < 0.1)."                          |
| "Make it production-ready" | What's missing? Monitoring? Error handling? Docs?                    | "Add health check endpoint. Configure alerting. Document deployment. Add rate limiting."                           |
| "Fix the UX"               | What's broken? What do users struggle with? What's the desired flow? | "Reduce checkout steps from 5 to 3. Add progress indicator. Fix form validation feedback timing."                  |
| "Add logging"              | What to log? Where? What format? What's the retention?               | "Log all API requests (method, path, status, duration). Structured JSON to CloudWatch. 30-day retention."          |

## How to Use This Table

1. When you encounter a vague requirement, find the closest match in the left column
2. Ask the questions in the middle column (or answer them from context if possible)
3. Propose a measurable translation from the right column (adapted to the specific situation)
4. Get user confirmation before proceeding

## The Anti-Pattern

**Never** accept a vague requirement as-is. The #1 cause of wasted AI work is building the wrong thing because the requirement was ambiguous. 5 minutes of clarification saves hours of rework.

## When You Can't Clarify

If the user is unavailable and you must proceed:

1. State your interpretation explicitly in the PRD
2. Choose the most conservative interpretation
3. Flag it with MEDIUM confidence
4. Note: "Assumed [X interpretation]. If [Y interpretation] was intended, [what would change]."
