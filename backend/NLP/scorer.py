CATEGORIES = {
    "urgency": [
        "right now", "immediately", "act fast", "urgent",
        "your account will be blocked", "time sensitive", "before it's too late"
    ],
    "secrecy": [
        "don't tell anyone", "don't hang up", "keep this confidential",
        "don't tell your family", "between us", "do not disconnect"
    ],
    "otp_request": [
        "share the otp", "what's your pin", "verification code",
        "one-time password", "the code you just received", "read me the code"
    ],
    "transfer": [
        "transfer money", "send to this account", "urgent payment",
        "pay immediately", "process a refund", "send the amount"
    ],
    "authority_impersonation": [
        "this is your bank", "calling from rbi", "police department",
        "income tax department", "government official", "cyber cell"
    ]
}

CATEGORY_WEIGHT = 20


def score_transcript(text):
    text = text.lower()
    evidence_tags = []

    for category, phrases in CATEGORIES.items():
        for phrase in phrases:
            if phrase in text:
                evidence_tags.append(category)
                break

    score = min(len(evidence_tags) * CATEGORY_WEIGHT, 100)

    if len(evidence_tags) >= 2:
        confidence = "high"
    elif len(evidence_tags) == 1:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "score": score,
        "confidence": confidence,
        "evidence_tags": evidence_tags
    }

if __name__ == "__main__":
    from fixtures import TEST_TRANSCRIPTS
    for i, t in enumerate(TEST_TRANSCRIPTS, 1):
        print(f"Transcript {i}: {score_transcript(t)}")