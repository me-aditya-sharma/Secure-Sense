"""Deterministic, explainable English rules. Scores are not fraud probabilities."""
import re
from datetime import datetime, timezone
from uuid import uuid4

VERSION = "consumer-rules-2.0.0"

def redact(text: str) -> str:
    # Conservative: remove all digit sequences of 4+ digits (including separators),
    # email addresses and explicit password/PIN values before returning or storing.
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[email removed]", text)
    text = re.sub(r"(?i)\b(password|passcode|pin|otp)\s*(?:is|:|=)\s*\S+", r"\1 [secret removed]", text)
    return re.sub(r"(?<!\w)(?:\+?\d[\s-]?){4,}(?!\w)", "[number removed]", text)

# Rules are evaluated per clause. Advice is suppressed only in its own clause.
RULES = [
 ("credentials", "A request for private credentials", 55,
  r"\b(?:share|tell|send|give|read|provide|confirm|enter|reveal|need|what(?:'s| is))\b.{0,65}\b(?:otp|pin|password|passcode|verification code|one.time password|security code|code you (?:just )?received)\b|\b(?:otp|pin|password|verification code)\b.{0,25}\b(?:please|required|needed)\b",
  "A request to disclose or enter a private code can enable account access or an unauthorized payment.", "Do not disclose credentials. Verify the request through the service's official app or website."),
 ("refund_payment", "Payment requested to release a refund", 55,
  r"\b(?:pay|send|transfer|deposit|fee|upi pin|scan.{0,10}qr)\b.{0,90}\b(?:refund|receive|release|unlock|prize)\b|\b(?:refund|prize)\b.{0,90}\b(?:pay|fee|deposit|transfer|upi pin|qr)\b",
  "The message links receiving money to making a payment or authorizing one.", "Pause the payment. Check the refund in your original merchant or bank account."),
 ("remote_access", "Remote access or screen sharing requested", 50,
  r"\b(?:install|download|open|enable|allow|start|share)\b.{0,55}\b(?:anydesk|teamviewer|remote access|screen.?shar\w*|your screen|access to your (?:phone|computer))\b",
  "Remote-control or screen-sharing tools can expose personal information and account activity.", "Do not grant remote access to an unsolicited caller."),
 ("payment", "A direct payment request", 25,
  r"\b(?:transfer money|send (?:money|the amount)|pay (?:immediately|now|to)|send to this account|advance payment|upfront payment)\b",
  "The communication asks for a payment. A payment request alone does not establish fraud.", "Independently confirm the recipient, purpose and payment details."),
 ("urgency", "Pressure to act quickly", 15,
  r"\b(?:immediately|right now|act fast|urgent(?:ly)?|within \d+ minutes|last chance|before it.s too late)\b",
  "Time pressure can reduce the opportunity to verify a request.", "Take time to verify. A deadline is not proof that the caller is legitimate."),
 ("threat", "A threat or account-blocking claim", 30,
  r"\b(?:arrest(?:ed)?|account (?:will be|gets?|is being) (?:blocked|frozen|closed)|legal action|police will|disconnect your (?:power|electricity))\b",
  "The message invokes a serious consequence to influence your decision; the claim is unverified.", "Verify directly with the relevant organization using a contact you find independently."),
 ("isolation", "Independent verification discouraged", 30,
  r"\b(?:don.t tell (?:anyone|your family)|do not tell|don.t hang up|do not disconnect|don.t contact|do not contact|keep (?:this|it) (?:secret|confidential))\b",
  "Discouraging you from checking with someone else is a warning sign.", "End the interaction if needed and seek an independent trusted contact."),
 ("identity_claim", "An institutional identity claim", 10,
  r"\b(?:this is your bank|calling from (?:rbi|your bank|the bank|amazon|flipkart)|(?:i am|we are) (?:from|with) (?:the police|your bank|customer support)|government official|cyber cell)\b",
  "The speaker claims an official or business identity. The claim has not been independently verified.", "Look up the organization's official contact yourself and confirm the request."),
 ("link", "A link in the communication", 10,
  r"(?:https?://|www\.)[^\s]+",
  "A link is present. SecureSense has not visited or checked its destination; its presence alone does not mean it is malicious.", "Use the official app or type a known official address instead of following an unsolicited link."),
]

ADVICE = re.compile(r"\b(?:(?:never|do not|don.t|must not|should not|shouldn.t|avoid|no need to)\s+(?:ever\s+)?(?:share|send|give|provide|reveal|enter|pay|transfer|install|download|open|allow|disclose|read)|beware of|won.t ask|will not ask)\b", re.I)

def analyze(text: str, context: str = "unknown", provenance: str = "pasted_text") -> dict:
    safe = redact(text.strip())
    findings = []
    seen = set()
    # Split contrastive clauses so 'never share it, but send me your OTP' is detected.
    for match in re.finditer(r"[^.!?;\n]+(?:[.!?;]|$)", safe):
        for part in re.finditer(r"[^,]+", match.group()):
            raw = part.group()
            for clause in re.split(r"\b(?:but|however|instead)\b", raw, flags=re.I):
                clause = clause.strip()
                if not clause or ADVICE.search(clause):
                    continue
                for code, title, weight, pattern, reason, action in RULES:
                    if code not in seen and re.search(pattern, clause, re.I):
                        # Locate in redacted transcript, never expose original secrets.
                        start = safe.find(clause, match.start())
                        findings.append(dict(id=code,title=title,weight=weight,excerpt=clause,
                                             start=start,end=start+len(clause),explanation=reason,action=action))
                        seen.add(code)
    score = min(100, sum(f['weight'] for f in findings))
    # Scope is English. Unsupported scripts and very short inputs are inconclusive.
    words = re.findall(r"[A-Za-z]+", safe)
    letters = [c for c in safe if c.isalpha()]
    sufficient = len(words) >= 4 and (not letters or sum(c.isascii() for c in letters)/len(letters) > .7)
    level = "high" if score >= 50 else "moderate" if score >= 20 else "low" if sufficient else "insufficient"
    if not sufficient and not findings:
        score = None
    summary = {
      "high":"Pause before you act. This communication contains significant warning signs.",
      "moderate":"Some details need a closer look. Verify the request independently.",
      "low":"Few warning signs were detected in this text. That does not verify the sender or guarantee safety.",
      "insufficient":"There is not enough supported conversation content to assess this interaction. Add more detail or an English transcript."
    }[level]
    return dict(id=str(uuid4()),created_at=datetime.now(timezone.utc).isoformat(),transcript=safe,
        provenance=provenance,context=context,policy_version=VERSION,level=level,score=score,summary=summary,
        evidence=findings,actions=list(dict.fromkeys(f['action'] for f in findings)) or ["Verify the sender through an official channel before sharing information or making a payment."],
        rights=["information","choice","redressal"],
        voice={"synthetic_speech":"unavailable","speaker_verification":"unavailable"},
        limitations=["English rule-based assessment; not a probability of fraud or a legal finding.","No sender identity, phone number or link destination has been verified.","Voice authenticity and speaker verification are not available."],saved=False)
