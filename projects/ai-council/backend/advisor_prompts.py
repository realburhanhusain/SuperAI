"""Prompt templates for the LLM Advisors debate system."""

CONSENSUS_TAG_INSTRUCTION = (
    "\n\nIMPORTANT: End your response with a Consensus Signal section and then, on its own final line, "
    "write exactly CONSENSUS_SCORE: N, replacing N with a single number from 1 to 5. Use 1 if you strongly disagree with the emerging group "
    "position, 3 if you are neutral or undecided, and 5 if you fully agree and are ready to converge. "
    "The score line must be the last line."
)

ADVISOR_ROUND1_PROMPT = (
    "{search_context_block}"
    "You are participating in a structured debate as an advisor.\n\n"
    "The question being debated:\n{question}\n\n"
    "Round 1 is for your opening position. Do not rebut other advisors yet.\n\n"
    "Target response length: 150 words maximum. Follow this exact structure:\n"
    "- Position (~100 words): State your position clearly and support it with reasoning.\n"
    "- Consensus Signal (~50 words): State your CONSENSUS_SCORE (1-5) and explain it in one sentence.\n\n"
    "Be direct and concise. If you exceed 150 words, the response may be flagged with a warning."
    "{consensus_tag}"
)

ADVISOR_FOLLOWUP_PROMPT = (
    "{search_context_block}"
    "You are participating in a structured debate as an advisor.\n\n"
    "The question being debated:\n{question}\n\n"
    "This is Round {round_number}. You are responding to the debate as it has evolved, not re-answering "
    "the original question from scratch.\n\n"
    "Cross-pollination extract from Round {previous_round_number} (your primary argumentation target):\n"
    "{cross_pollination_extract}\n\n"
    "Background transcript so far (secondary context only):\n\n{transcript}\n\n"
    "You must address at least one specific claim from the cross-pollination extract. Name the advisor "
    "you are rebutting or conceding to. Do not rebut your own claims; choose a claim made by another advisor.\n\n"
    "Target response length: 250 words maximum. Follow this exact structure:\n"
    "- Position/Update (~100 words): State your current position or how it shifted since the last round.\n"
    "- Rebuttal (~100 words): Pick the single strongest peer argument and argue against it specifically. "
    "Name the advisor you're rebutting.\n"
    "- Consensus Signal (~50 words): State your CONSENSUS_SCORE (1-5) and explain it in one sentence.\n\n"
    "If you exceed 250 words, the response may be flagged with a warning. Do not skip the rebuttal."
    "{consensus_tag}"
)

ADVISOR_CROSS_POLLINATION_PROMPT = (
    "You are preparing a cross-pollination extract for a structured advisor debate.\n\n"
    "Original question:\n{question}\n\n"
    "Round {round_number} transcript:\n{round_transcript}\n\n"
    "Return a brief structured extract. For each advisor, include:\n"
    "- Overall position: one line\n"
    "- Strongest claims: 2-3 bullets containing reasoned points, not vague assertions\n\n"
    "Keep it lightweight. Do not write essays. Use the advisor names from the transcript."
)

ADVISOR_VERDICT_PROMPT = (
    "You are a neutral analyst reviewing a structured debate between advisors.\n\n"
    "The original question:\n{question}\n\n"
    "Debate arc signal:\n{debate_arc}\n\n"
    "Full debate transcript:\n{transcript}\n\n"
    "Produce a structured verdict in the following exact format. Use markdown formatting.\n\n"
    "## Summary\n"
    "2-3 sentences capturing the key insight from this debate.\n\n"
    "## Consensus Points\n"
    "Bulleted list of points where all advisors agreed.\n\n"
    "## Disagreements\n"
    "For each disagreement, create a row with: the point of contention, each side's position, "
    "and which argument had stronger evidence. Use a markdown table with columns: "
    "Point | Position A | Position B | Stronger Argument.\n\n"
    "## Verdict\n"
    "State which overall position was strongest and why, naming the advisor(s) who made "
    "the most compelling case. If the debate reached consensus, say so.\n\n"
    "## Recommended Next Steps\n"
    "3-5 concrete, actionable next steps based on the debate outcome.\n\n"
    "## Open Uncertainties\n"
    "Bulleted list of questions that remain unresolved after the debate."
)

ADVISOR_TIEBREAKER_PROMPT = (
    "You are a neutral tiebreaker called in because the advisors could not reach agreement.\n\n"
    "The original question:\n{question}\n\n"
    "Full debate transcript:\n{transcript}\n\n"
    "The advisors' positions are evenly split. Your job is to:\n"
    "1. Identify the strongest arguments from each side\n"
    "2. Weigh the evidence and reasoning\n"
    "3. Deliver a clear decision — which position should prevail and why\n"
    "4. If appropriate, propose a synthesis that takes the best from both sides\n\n"
    "Be decisive. Do not equivocate."
)
