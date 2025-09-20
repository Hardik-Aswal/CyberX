# Labeling guidelines — Fraudulent vs Non-fraudulent

## Goal
Label each message as `1` (fraudulent) if it promotes or solicits illegal/financial scam/prostitution/advance-fee schemes or clearly malicious activity. Otherwise label `0`.

## Positive examples (label=1)
- "Win ₹10,000 daily — click http://scam.example and send KYC"
- "Book private services in Goa contact +91-XXXXXXXXXX"
- "Pay ₹500 upfront to get loan — send bank details"

## Negative examples (label=0)
- "Beautiful sunset at Goa beach"
- "Can anyone recommend a good cafe?"
- "Here are travel photos from last week"

## Tips
- If message is ambiguous, prefer `0` (non-fraud) and mark for review.
- Mark messages with external payment requests, KYC requests, promises of guaranteed earnings, or explicit escort/prostitution solicitations as fraud.
- Keep a comment field when labeling to explain edge cases.
