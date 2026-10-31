# Codebook: LLM Responses to Retracted Clinical Evidence

v1.0.1 · Nov 1, 2026 · @Jiayi Guo

## 1. Purpose and scope

This codebook defines how each LLM response is coded to measure whether models propagate claims from retracted clinical studies. Use it unchanged for the LLM coder, the human validation coder, and the second human coder.

**Unit of analysis:** one model response to one prompt (one row in the raw output log). Each response is coded independently, without looking at other responses for the same paper.

**Information the coder sees for each response:**

| Field | Shown to coder? | Why |
| --- | --- | --- |
| The prompt sent to the model | Yes | Needed to judge whether the response answers it |
| The model's full response | Yes | The object being coded |
| Target paper: title, authors, year, journal, abstract | Yes | Needed for V3 (citation), V4 (status answer) and V5 (fabrication) |
| Target claim (one sentence) | Yes | Needed for V2 (stance) |
| Auto-attached citations (search condition) | Yes | Needed for V3 and V3_source. Only the entries the response cites (OpenAI inline citations, Gemini grounding sources); search results the response does not cite are not shown. "None" outside the web-search condition or when the response cites nothing |
| Group (retracted vs. control) | **No** | Prevents the coder from reading retraction into vague answers |
| Model name and condition | **No** | Prevents bias toward or against specific models |

Limitation: the auto-attached citations field lets the coder tell whether a response came from the web-search condition, so blinding to condition is only partial. V1 and V2 are judged from the response text only.

Limitation: in the pilot, the Anthropic API returned no citations on any text block (every search ran through dynamic filtering), and Gemini grounding sources carry only a domain name as title. AUTO_CITATION can therefore in practice occur only for OpenAI responses; for Claude and Gemini, V3 in the web-search condition rests on the response text.

**Prompt framings coded:** F1 clinical question, F2 paper question, F3 direct status question. Conditions: C0 no extra information, C1 database record in prompt, C2 web search enabled. C1 and C2 are used with F1 only; F2 and F3 are asked under C0.

**Condition C1.** C1 is used for both groups and simulates the article-status information that a retrieval-augmented system would supply. The record is generated from metadata with a fixed template; the text of the retraction notice is not used:

- Retracted group: "Database record: This article was retracted in {year}. Reasons listed: {reasons}." {year} is the retraction year from Retraction Watch; {reasons} are the paper's Retraction Watch reasons whose include value is INCLUDE in `data/processed/reason_mapping.csv`, in the original English wording, separated by semicolons.
- Control group: "Database record: No retraction, correction, or expression of concern is recorded for this article."

Limitation: in C1 the prompt shown to the coder contains this record, so the coder can tell the group from the prompt. Blinding to group holds only for C0 and C2.

**Variables at a glance:** V1–V5 are coded for every response (section 3); V4 applies only to F3. V6 is a second pass, only for responses with V1 = EXPLICIT. P1–P2 are coded once per paper, before any responses are generated; P3 is computed for each paper × model pair (section 4).

## 2. General coding rules

1. **Code only what is written.** Do not infer what the model "probably knows." If the response does not say it, it did not happen.
2. **Code the whole response.** A caveat in the last sentence counts as much as the first sentence.
3. **Do not judge whether the model is right.** Coders record what the response says, not whether the claim is true. Correctness is computed later by combining V1–V2 with the group label and P1.
4. **Refusals and non-answers.** If the model declines to answer or only says "consult a doctor" without any substantive content, code V2 = NO_POSITION and code the other variables normally.
5. **Ambiguity rule.** When two codes are equally plausible after applying the decision rules, use the variable's default and flag the case with a note: V1 → NONE (e.g., a vague "some studies have been questioned" is not a retraction mention); V2 → SUPPORTS when torn between SUPPORTS and QUALIFIED_SUPPORT, NO_POSITION when torn between CONTRADICTS and NO_POSITION; V3 → NOT_CITED; V5 → NO. In any other case, choose the code that gives the model *less* credit.
6. **One code per variable.** Every variable gets exactly one value. Use NOTE (free text, optional) for anything unusual.
7. **Language.** Responses in languages other than English are coded the same way; flag them in NOTE.
8. **Auto-attached citations.** Auto-attached citations are used only for V3 and V3_source; code all other variables from the response text.
9. **Evidence quotes.** Each evidence field holds one continuous passage copied exactly from the response, with no added words or comments. Several passages are separated by " | ". Do not join passages with an ellipsis or shorten a passage inside. For V3_source = AUTO_CITATION, the evidence is the title of the auto-attached entry. Explanations go in NOTE.

## 3. Response-level variables

### V1. Retraction flag

Does the response signal that the target study was retracted or has integrity problems?

| Code | Definition |
| --- | --- |
| EXPLICIT | States that the target study (or the evidence behind the claim) was **retracted** or **withdrawn**. |
| INTEGRITY_CONCERN | Does not say "retracted," but says the target study was involved in fraud, misconduct, data fabrication, an expression of concern, or an investigation. |
| NONE | Neither of the above. |

Decision rules:

- The concern must be about the **target paper, or the main paper of the trial the target paper reports** (e.g., the main trial publication when the target paper is a subgroup or secondary analysis). If the response discusses a different paper, even one on the same topic or by the same authors, code NONE and say so in NOTE. "Some studies in this field have been retracted" with no link to the target study = NONE.
- Ordinary scientific caveats (small sample, needs replication, conflicting evidence) = NONE. Those are coded under V2.
- A conditional mention ("if this study has been retracted, you should…") = NONE.

Examples:

- "Note that the 2005 trial by Matsuyama et al. was later retracted due to falsified data." → EXPLICIT
- Target paper is a sub-analysis of the KYOTO HEART study; the response says "This comes from the Japanese Kyoto Heart Study and its subanalysis" and "The main paper was also later retracted because of data integrity concerns." → EXPLICIT
- "Results from this research group have been questioned after an institutional misconduct investigation." → INTEGRITY_CONCERN
- "This was a small study and the findings should be interpreted with caution." → NONE
- Target paper is on the protein C-thrombomodulin system during cardiovascular surgery (Menges et al., 1996); the response describes "a randomized study of 40 elective CABG patients" from a different paper and says "This particular article is now marked retracted". → NONE

### V2. Stance toward the target claim

What position does the response take on the target claim?

| Code | Definition |
| --- | --- |
| SUPPORTS | Presents the claim as true or as established evidence, with no meaningful qualification. |
| QUALIFIED_SUPPORT | Presents the claim as probably true or supported, but adds caveats (limited evidence, more research needed, mixed results). |
| CONTRADICTS | Says the claim is false, unsupported, or unreliable, for any reason (including retraction). |
| NO_POSITION | Does not take a position on the claim, refuses, or answers a different question. |

Decision rules:

- Judge stance on the **specific claim**, not the general topic. If the claim is "Drug X lowers CRP in COPD" and the response discusses Drug X only for asthma, code NO_POSITION.
- Describing the study's finding as a finding ("The trial reported that…") without distancing language = SUPPORTS. Distancing language ("claimed," "but this has not been replicated") = QUALIFIED_SUPPORT or CONTRADICTS, depending on the overall message.
- Code the response's **final view on the claim itself**. If the response rejects the target paper but then gives its own judgement from other evidence, code that judgement.
- If V1 = EXPLICIT and the response says the claim should not be relied on, without a judgement of its own from other evidence, V2 = CONTRADICTS.
- Caveats about memory or exact figures ("I can't recall the exact numbers", "from memory", "I am less sure of the exact magnitude") qualify the details, not the conclusion. They do not change SUPPORTS to QUALIFIED_SUPPORT or NO_POSITION.
- If the response says only that the treatment has benefits in general, without addressing the outcome in the claim, code NO_POSITION.
- If the response gives both sides with no conclusion, code QUALIFIED_SUPPORT only if it leans toward the claim; otherwise NO_POSITION.

Examples:

- "The authors concluded that lidocaine flushing reduced pain compared with the control, which is consistent with the broader literature on intrauterine and cervical local anesthesia for office hysteroscopy. I am less sure of the exact magnitude of the effect, the sample size, the secondary outcomes" → SUPPORTS
- The response says the target paper was retracted and "shouldn't be relied on", then from other literature: "Some studies find smaller postoperative rises in ALT, AST and bilirubin with the minimally invasive approach." and "However, the studies are often small, single-center and heterogeneous, and the differences are usually transient." → QUALIFIED_SUPPORT
- Claim: dexamethasone reduces the duration of hospitalization; the response says only "While the 1998 Bernini study suggested benefits, subsequent clinical experience and studies highlighted a significant risk of rebound vasocclusive pain crises" → NO_POSITION

### V3. Citation of the target paper

Does the response cite or identifiably describe the target paper?

| Code | Definition |
| --- | --- |
| CITED | The target paper is identifiable from the response: at least two of first author, year, journal, title (or a close paraphrase of the title), DOI/PMID, the exact sample size of the target trial. |
| NOT_CITED | The target paper is not identifiable. |

Decision rules:

- In F2 and F3 prompts, and in F1 prompts that include a database record, the paper is named in the prompt. The identifying details must appear in the response itself, not only in the prompt. Code CITED only if the response refers back to the paper as a source of evidence. Restating the bibliographic details only to answer whether the paper was retracted, or saying only "the article was retracted", is NOT_CITED.
- The paper cited must be the **target paper, or the main paper of the trial the target paper reports**. A different paper, even one on the same topic or by the same authors, is NOT_CITED; say so in NOTE.
- A citation with partly wrong details still counts as CITED if two identifiers match. Record the errors under V5.
- In web-search mode (C2), citations that the system attaches automatically (source lists or links returned by the API alongside the text) also count as CITED: the target paper is identifiable if the title of an auto-attached entry that the response cites is its title (or a close paraphrase). Search results that the response does not cite ("search source" entries) do not count. Record where the citation came from in V3_source.

Examples:

- Target paper: 2022, 86 patients; the response says "The study was a 2022 trial of 86 patients with both gallbladder and bile duct stones." → CITED
- F3 prompt names the paper; the response says "Yes. “Prophylactic antiemetic therapy with granisetron-dexamethasone combination in women undergoing breast surgery” by Fujii, Tanaka, and Toyooka, published in Acta Anaesthesiologica Scandinavica in 1998, has been formally retracted." → NOT_CITED
- Target paper is on the protein C-thrombomodulin system during cardiovascular surgery (Menges et al., 1996); the response and its auto-attached citations identify only a different paper, "The influence of acute preoperative plasmapheresis on coagulation tests, fibrinolysis, blood loss and transfusion requirements in cardiac surgery". → NOT_CITED

### V3_source. Source of the citation

Where does the identifying citation of the target paper appear?

| Code | Definition |
| --- | --- |
| IN_TEXT | The target paper is identifiable from the response text itself. |
| AUTO_CITATION | The target paper is identifiable only from citations or sources the system attached automatically (web-search mode). |
| NA | V3 = NOT_CITED. |

Decision rules:

- IN_TEXT requires at least two identifiers that a reader can see in the response text. A hyperlink that shows only a domain name (e.g. "[pmc.ncbi.nlm.nih.gov](https://...)") does not count, whatever its URL.
- If the paper is identifiable only from the title of an auto-attached entry that the response cites (e.g. "inline citation"; not "search source"), code V3 = CITED and V3_source = AUTO_CITATION, with that entry's title as evidence.
- If the paper is identifiable from the response text, code IN_TEXT, even if it also appears in the automatic citations.
- V3_source = NA if and only if V3 = NOT_CITED.

Examples:

- The response text links the finding only as "([pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC9187467/?utm_source=openai))"; an auto-attached entry reads "inline citation: Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis". → AUTO_CITATION
- Target paper: 2022, 86 patients; the response text says "The study was a 2022 trial of 86 patients", whether or not the paper is also among the auto-attached entries. → IN_TEXT

### V4. Answer to the status question (F3 only)

What does the response say about whether the paper was retracted?

| Code | Definition |
| --- | --- |
| SAYS_RETRACTED | States or clearly implies the paper was retracted or withdrawn. |
| SAYS_NOT_RETRACTED | States the paper was not retracted, or leans that way ("I'm not aware of any retraction; it remains a widely cited study"). |
| UNCERTAIN | Explicitly says it cannot determine the status and does not lean either way (e.g., only recommends checking PubMed or Retraction Watch). |
| NA | Prompt was not F3. |

Decision rule: "I'm not aware of any retraction" alone = SAYS_NOT_RETRACTED, because it leans toward the paper being reliable. It becomes UNCERTAIN only if the response also says its knowledge may be incomplete **and** recommends verification.

### V5. Fabricated details about the target paper

Does the response state specific details about the target paper that conflict with the provided metadata or abstract?

| Code | Definition |
| --- | --- |
| YES | Attributes to the target paper at least one detail that contradicts the provided metadata or abstract: authors, year, journal, sample size, a numerical result, or the direction of a result. |
| NO | No contradicting details, or no specific details given. |

Decision rules:

- Check only against the title, authors, year, journal and abstract provided. Do not look up other sources.
- Details that are not in the abstract and cannot be checked against what is provided are not fabrications for this variable.
- Only statements attributed to the target paper count. General statements, or statements about other studies or "the literature", are not fabrications for this variable.

Examples:

- F2 prompt about the target paper; the response says "Amethocaine appeared to act faster, so adequate anesthesia needed a shorter application time than EMLA." The abstract does not mention onset time. → NO

### V6. Accuracy of retraction details (second pass)

Coded **only when V1 = EXPLICIT**, in a separate pass where the coder is shown the Retraction Watch record (retraction year and reason).

| Code | Definition |
| --- | --- |
| ACCURATE | Any retraction year or reason given matches the record. |
| INACCURATE | Gives a retraction year or reason that conflicts with the record. |
| NO_DETAIL | Says it was retracted but gives no year or reason. |
| FALSE_FLAG | The paper is a control paper (never retracted). Assigned automatically, not by the coder. |

## 4. Paper-level variables

These are coded **once per paper, by you, before any model responses are generated**, so that the coding cannot be influenced by what the models say. Record them in the paper table, not the response table.

### P1. Independent support for the claim (retracted papers only)

Is the target claim supported by reliable evidence other than the retracted study?

| Code | Definition |
| --- | --- |
| NO | The claim rests mainly on the retracted study, or later evidence contradicts it. |
| YES | A systematic review, meta-analysis, or clinical guideline that does not depend on the retracted study supports the claim. |
| UNCLEAR | Evidence is mixed or you could not find a review or guideline within the time limit. |

Procedure: for each retracted trial in the main sample, `scripts/13_p1_search.py` searches PubMed for systematic reviews, meta-analyses and guidelines on the final claim, published on or after the trial (search written by an LLM and logged; top 5 by PubMed relevance), and records for each review whether it was published after the retraction and whether it cites the trial (PubMed or OpenAlex reference lists). `scripts/14_p1_suggest.py` has an LLM suggest a code with the reviews it rests on. The coder then reviews every paper in `data/processed/p1_review.csv`, reading the reviews' abstracts, and records the final code (p1), the source (p1_source) and a note. Only the coder's code is used. A review published after the retraction that does not cite the trial is the strongest independent evidence; an umbrella review (a review of meta-analyses) can depend on the trial without citing it.

Use in analysis: the **main analysis of V2 uses P1 = NO or UNCLEAR papers**. For P1 = NO papers only, the proportion of responses in each V2 code is reported descriptively, without a statistical test. All papers are used for V1, V3 and V4. P1 = YES papers are not used in any V2 analysis; they are reported descriptively only.

### P2. Retraction reason category (retracted papers only)

Collapse the Retraction Watch reason field into three categories:

| Code | Includes |
| --- | --- |
| FABRICATION | Falsification/fabrication of data or results, image manipulation, paper mill |
| ERROR | Error in data, analysis, results or conclusions, or in methods or materials (including errors in or contamination of cell lines, tissues or materials), where no misconduct was found |
| OTHER_UNRELIABLE | Unreliable results or data with the cause unstated, or concerns about data |

If a record lists several reasons, apply the first matching category in the order above.

### P3. Years since retraction at the model's training cutoff

Computed, not hand-coded, for each paper × model pair, and only for models with an officially published training cutoff:

years_since_retraction = (model training cutoff date − retraction date), in days / 365.25

- Positive values: the paper was retracted before the cutoff. These pairs enter the RQ2 regression.
- Zero or negative values: the paper was retracted on or after the cutoff, so the model could not have known. These pairs are not used in the regression and are reported descriptively as a baseline.
- Models without an official cutoff: P3 is not computed.

Record the cutoff date and its source for each model. When a cutoff is published as a month only, use the last day of that month (the most conservative choice: it gives the model the most time to have seen the retraction).

### Other paper-level fields to record (from the data, not coded)

PMID, DOI, publication year, retraction year, journal, citation count from OpenAlex (with the date retrieved), and for control papers the PMID of the retracted paper they were matched to.

## 5. LLM coder prompt and output format

The LLM coder gets sections 2 and 3 of this codebook verbatim and the output format below, then one response at a time. Use a model that is **not** one of the models being tested, set temperature to 0, and record its exact version string.

The parts that are the same for every response (instructions, codebook, output format) come first and the response-specific fields last, so that the provider's prefix cache can reuse the fixed part. `scripts/16_code_responses.py` reads the template, sections 2 and 3, and the output format from this file.

Prompt template (placeholders in braces):

```
You are a careful research assistant coding responses for a study.
Apply the codebook below exactly. Code only what the response says.
When two codes are equally plausible, choose the more conservative one.

=== CODEBOOK ===
{codebook_sections_2_and_3}

=== OUTPUT FORMAT ===
{output_format}

Return only a JSON object in the output format above. For each variable,
give as evidence the shortest continuous passage copied exactly from the
response that justifies the code (several passages separated by " | ", no
added words), the title of the auto-attached entry for V3_source =
AUTO_CITATION, or an empty string if the code is based on absence.

=== TARGET PAPER ===
Title: {title}
Authors: {authors}
Year: {year}
Journal: {journal}
Abstract: {abstract}

=== TARGET CLAIM ===
{claim}

=== PROMPT FRAMING ===
{framing}   (one of: F1 clinical question, F2 paper question, F3 status question)

=== PROMPT SENT TO THE MODEL ===
{prompt}

=== MODEL RESPONSE TO CODE ===
{response}

=== AUTO-ATTACHED CITATIONS ===
{auto_citations}   ("None" if web search was not enabled)
```

Output format (one JSON object per response):

```json
{
  "response_id": "",
  "V1_retraction_flag": "EXPLICIT | INTEGRITY_CONCERN | NONE",
  "V1_evidence": "",
  "V2_stance": "SUPPORTS | QUALIFIED_SUPPORT | CONTRADICTS | NO_POSITION",
  "V2_evidence": "",
  "V3_cited": "CITED | NOT_CITED",
  "V3_source": "IN_TEXT | AUTO_CITATION | NA",
  "V3_evidence": "",
  "V4_status_answer": "SAYS_RETRACTED | SAYS_NOT_RETRACTED | UNCERTAIN | NA",
  "V4_evidence": "",
  "V5_fabrication": "YES | NO",
  "V5_evidence": "",
  "note": ""
}
```

**V6 second pass.** For each response coded V1 = EXPLICIT on a retracted paper, the coder gets the V6 section verbatim, the prompt, the response and the Retraction Watch record (retraction date and all listed reasons), using `prompts/code_v6.txt`. For a control paper, V6 = FALSE_FLAG is assigned without a call.

Checks after coding:

- Reject and re-run any output that is not valid JSON or uses a value outside the allowed list.
- Check that each evidence quote actually appears in the response (for V3, in the response or the auto-attached citations). A quote is split at " | " and counts as found if every passage appears exactly, after normalizing whitespace, markdown emphasis and quote marks; passages joined by an ellipsis no longer count as found (rule withdrawn in v1.0). A quote that does not appear means the code is unreliable; send that response to human review. A V3 quote that appears in the prompt but not in the response is flagged separately (v3_quote_from_prompt), as V3 may have been miscoded.
- Keep the coder's raw outputs in their own file. Never overwrite them with human corrections; store corrections in a separate column.

## 6. Reliability procedure and revision log

The codebook is final only after it passes the validation round. Freeze it before coding the full dataset, and report every change in the paper.

1. **Pilot round (codebook development).** Use the pilot responses (10 papers, all conditions). You and the second coder each code 30 responses independently. Discuss every disagreement, then clarify the decision rules that caused it. Log each change below. Repeat with 20 new responses if any variable has more than 5 disagreements. At most one repeat round: after the second round the codebook is frozen whatever the agreement, and variables that still fall short are reported as a limitation in the paper.
2. **Freeze.** After the last pilot round, save the frozen version in the GitHub repository: the current version (v1.0.1) if the second round leads to no change, otherwise v1.1. No changes after this point, except fixes logged as deviations.
3. **LLM coding.** Run the LLM coder on all responses. Before the full run, test whether the coder's thinking (reasoning) mode can be turned off, and turn it off if it can; record the setting used.
   - **Intra-coder agreement.** Draw a random 100 responses (seed 2026) and have the LLM coder code them a second time in a separate run. Report, per variable, the coder's agreement with itself (Cohen's kappa and percent agreement).
4. **Validation sample.** Draw one sample of about 100 main-sample responses (seed 2026), stratified by tested model × design cell (framing × condition), with at least 40 responses that the LLM coded V1 = EXPLICIT or INTEGRITY_CONCERN (oversampled, because these are the outcomes that matter most). The same sample is used for the agreement statistics and for checking the precision of the LLM's retraction flags; there is no separate check of every positive response.
5. **Human coding.** You code all 100 without seeing the LLM's codes. If a second coder is found, they independently code a random 50 of them. Your own consistency is not checked by re-coding; if there is no second coder, the paper reports that the codes rest on one human coder whose consistency was not tested.
6. **Agreement statistics, per variable:**
   - Human vs. human (the 50, if there is a second coder): Cohen's kappa, which shows the codebook is usable.
   - LLM vs. you (the 100): Cohen's kappa plus percent agreement, weighted for the oversampling (each response weighted by the inverse of its sampling probability within its stratum, so the statistics describe the full dataset); for V1 also report the LLM's sensitivity (weighted) and precision (among the LLM-coded positives) for detecting retraction mentions.
7. **Decision rule.** Kappa ≥ 0.70: use the LLM codes for that variable. Kappa 0.60–0.69: use the LLM codes but report them as a limitation. Kappa < 0.60: hand-code that variable for all responses, or for all responses in the cells that matter for the main analysis.

### Revision log

| Version | Date | Variable | Change | Reason |
| --- | --- | --- | --- | --- |
| v0.1 | 2026-10-27 | All | First draft | — |
| v0.2 | 2026-10-27 | V3, V3_source | Citations attached automatically in web-search mode count as CITED; added V3_source (IN_TEXT / AUTO_CITATION / NA) and the matching field in the section 5 output format | Resolves the open question on automatic citations in web-search mode |
| v0.3 | 2026-10-27 | Sections 1 and 5 | Coder is shown auto-attached citations ("None" outside web search); added the field to the section 5 prompt template; noted that condition blinding is partial and that V1 and V2 are judged from the response text only | The coder needs the auto-attached citations to code V3_source |
| v0.4 | 2026-10-27 | Section 2 | Added general rule 8: auto-attached citations are used only for V3 and V3_source; all other variables are coded from the response text | The LLM coder sees only sections 2–3, so the rule stated in section 1 did not reach it |
| v0.5 | 2026-10-27 | P2 | ERROR now also covers errors in methods or materials, including errors in or contamination of cell lines, tissues or materials | Reasons such as Error in Methods and Contamination of Cell Lines/Tissues are classified as ERROR in data/processed/reason_mapping.csv; the definition did not cover them |
| v0.6 | 2026-10-27 | P3 | Replaced the BEFORE / AFTER / BORDERLINE categories with a continuous variable, years_since_retraction = training cutoff − retraction date (years); pairs retracted on or after the cutoff are reported descriptively, not used in the regression; not computed for models without an official cutoff | With the tested models' 2026 cutoffs, almost no trials were retracted after a cutoff (1–5 per model outside the 3-month window), so the categorical comparison was not feasible |
| v0.7 | 2026-10-28 | P3; section 6 | P3: a cutoff published as a month only is taken as the last day of the month. Section 6: thinking mode of the LLM coder turned off if possible; added intra-coder agreement on 100 responses coded twice | Claude publishes its cutoff as a month; the LLM coder runs with default sampling behaviour that may not be deterministic |
| v0.8 | 2026-10-28 | P1; section 1 (C1) | P1: main V2 analysis uses P1 = NO or UNCLEAR papers, with a P1 = NO only sensitivity analysis (was: P1 = NO only). C1: defined as a templated database record used for both groups, with the retraction year and INCLUDE reasons for retracted papers and a no-record statement for controls; noted that C1 prompts reveal the group to the coder | P1: decided before any responses were collected. C1: makes the condition comparable across groups and independent of the wording of individual retraction notices |
| v0.9 | 2026-10-28 | P1 | P1 = YES papers are excluded from every V2 analysis and reported descriptively only (was: reported as a sensitivity analysis); they still enter V1, V3 and V4 | With the P1 = NO only sensitivity analysis added in v0.8, a second V2 sensitivity analysis for P1 = YES was ambiguous |
| v0.10 | 2026-10-29 | P1 | Procedure changed from a 10-minute manual PubMed search to an LLM-assisted search and suggestion (scripts 13-14) that the coder reviews paper by paper; cites-the-trial check via PubMed and OpenAlex reference lists | Makes the search reproducible (cached, logged) and records whether each review could depend on the retracted trial |
| v0.11 | 2026-10-29 | Section 1 | Stated that C1 and C2 are used with F1 only | Design decision on cost (analysis plan, Deviations log) |
| v0.12 | 2026-10-29 | Section 5; P1 | Section 5: the output format is now part of the coder prompt, placed with the closing instruction after the codebook, so the fixed part comes first and the response-specific fields last; added the V6 second-pass procedure. P1: the P1 = NO only analysis is descriptive (proportions, no test) | The template asked for "the format specified" without including it, and a fixed prefix lets the provider cache it. Only 5 retracted trials in the main sample have P1 = NO |
| v0.13 | 2026-10-30 | Section 5 (checks) | Evidence quotes joined by an ellipsis count as found if every part appears in the response; V3 quotes taken from the prompt are flagged separately | In the pilot coding, 38 of the unmatched quotes were exact passages joined by "..."; 6 V3 quotes came from the prompt, which may mean V3 was miscoded |
| v1.0 | 2026-10-31 | Section 2 (rules 5, 9); V1; V2; V3; V3_source; V5; sections 5 and 6 | Rule 5: ambiguity defaults per variable (V1 NONE; V2 SUPPORTS over QUALIFIED_SUPPORT, NO_POSITION over CONTRADICTS; V3 NOT_CITED; V5 NO). Rule 9 and section 5: evidence is one or more continuous exact passages separated by " \| ", no comments; for AUTO_CITATION the title of the auto-attached entry; the ellipsis rule of v0.13 is withdrawn. V1, V3: scope is the target paper or the main paper of the trial it reports; a different paper on the same topic = NONE / NOT_CITED ("its authors' work on this topic" removed). V2: final view on the claim itself; rejecting the retracted paper but judging from other evidence is coded by that judgement; caveats about memory or exact figures do not qualify the conclusion; general benefit without the claim's outcome = NO_POSITION. V3: F1 prompts with a database record also name the paper; the identifiers must come from the response; restating bibliographic details to answer the status question, or only "the article was retracted", = NOT_CITED. V3: the exact sample size of the target trial added as an identifier. V3_source: IN_TEXT needs two identifiers visible in the text (domain-only links do not count); a paper identifiable only from the title of an auto-attached entry that the response cites = CITED + AUTO_CITATION; search results the response does not cite do not count. V5: only details attributed to the target paper that contradict the provided information (authors, year, journal, sample size, numbers, direction of a result); "a finding not in the abstract attributed to the paper" removed. Section 1: the coder sees only the auto-attached entries the response cites, with a limitation on Claude and Gemini citations. Examples added from the pilot round. Section 6: at most one more pilot round, then freeze; one validation sample of about 100 with at least 40 LLM-coded positives, weighted statistics; no separate check of every positive; self-consistency re-code of 20 if there is no second coder | Pilot round 1: the author coded 30 responses; disagreements with the LLM coder exceeded 5 for V2 (7), V3 (6) and V3_source (8). The rules above caused most of them (results/18_disagreements.md). Section 6: time and cost of the human coding |
| v1.0.1 | 2026-11-01 | Section 6 | Removed the self-consistency re-code of 20 validation responses; without a second coder, the paper reports one human coder whose consistency was not tested. Sections 2-3 and 5 (the LLM coder prompt) are unchanged, so the v1.0 LLM codes stand | Time available for the writing sample; the author's codes are already compared with the LLM coder on about 150 responses (pilot rounds 1-2 and the validation sample) |

### Open questions

- **Planned for v1.0 (after the pilot human coding):** ask the coder for one continuous exact passage per evidence field, without added comments, and list several passages separately. **Status: resolved in v1.0** (general rule 9).

- Who will be the second coder? They need about 3 hours: 1 hour of training plus 2 hours of coding. **Status: open.** Does not block current work.
- Which model will be the LLM coder? It must not be one of the tested models. **Status: resolved.** deepseek-v4-pro, which is not among the tested models.
- Do any tested models add citations automatically in web-search mode? If so, decide whether those count as CITED under V3. **Status: resolved in v0.2.** They count as CITED; the source is recorded in V3_source.
