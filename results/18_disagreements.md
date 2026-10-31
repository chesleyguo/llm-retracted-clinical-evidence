# Pilot coding: author vs. LLM coder, disagreements

Group, tested model and condition are not shown. Marks: **quote_not_found** = the LLM's evidence quote for that variable was not found in the response; **v3_quote_from_prompt** = the LLM's V3 quote is in the prompt, not the response.

| Variable | n | Disagreements |
| --- | --- | --- |
| V1_retraction_flag | 30 | 2 |
| V2_stance | 30 | 7 (more than 5) |
| V3_cited | 30 | 6 (more than 5) |
| V3_source | 30 | 8 (more than 5) |
| V4_status_answer | 6 | 0 |
| V5_fabrication | 30 | 2 |

## Item 1 (F1)

Disagrees on: V3_cited, V3_source

**Claim:** Laparoscopy combined with choledochoscopy reduces liver function damage in patients with cholecystolithiasis and choledocholithiasis compared with open surgery.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V3_cited | NOT_CITED | — | CITED | the article addressing this specific question |
| V3_source | NA | — | IN_TEXT | the article addressing this specific question |

**Author note:** —  
**LLM note:** —

**Prompt:**

> The following database record concerns the article "Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis" by Zhang et al., published in Computational and Mathematical Methods in Medicine in 2022. Database record: This article was retracted in 2023. Reasons listed: Concerns/Issues about Data; Unreliable Results and/or Conclusions.
> 
> Does laparoscopy combined with choledochoscopy affect liver function damage compared with open surgery in patients with cholecystolithiasis and choledocholithiasis?

**Response:**

> Based on the provided database record, the article addressing this specific question was **retracted in 2023** due to serious concerns regarding data integrity, unreliable results, and questionable conclusions. 
> 
> Because the scientific validity of the study has been compromised and the paper formally retracted, **its findings cannot be considered reliable or used as valid evidence** to determine whether laparoscopy combined with choledochoscopy affects liver function damage compared to open surgery. 
> 
> To answer your clinical question safely and accurately, one would need to consult peer-reviewed, non-retracted studies or systematic reviews that have not been invalidated by data concerns.

## Item 2 (F2)

Disagrees on: V2_stance, V5_fabrication

**Claim:** Ametop reduces pain of intravenous cannulation in adult volunteers compared with EMLA.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V2_stance | NO_POSITION | I can't reliably recall the exact numbers from this paper | SUPPORTS | Amethocaine gel gave better analgesia than EMLA, with lower pain scores and fewer patients reporting significant pain on cannulation. |
| V5_fabrication | NO | — | YES | Amethocaine appeared to act faster, so adequate anesthesia needed a shorter application time than EMLA. |

**Author note:** —  
**LLM note:** The response states a finding (faster action) not present in the provided abstract. Also, the response says 'patients' but the abstract says 'volunteers'.

**Prompt:**

> What are the main findings of the study "Topical amethocaine (Ametop) is superior to EMLA for intravenous cannulation. Eutectic mixture of local anesthetics" by Browne et al., published in Canadian Journal of Anaesthesia in 1999?

**Response:**

> I can't reliably recall the exact numbers from this paper, so I'll describe its main conclusions in general terms and you can check the details against the abstract.
> 
> **Design:** A randomized comparison of two topical anesthetics for pain on peripheral intravenous cannulation. One was 4% amethocaine gel (Ametop), the other EMLA cream (lidocaine/prilocaine eutectic mixture). Patients rated the pain of cannulation, and local skin effects were also recorded.
> 
> **Main findings (as I recall them):**
> - Amethocaine gel gave better analgesia than EMLA, with lower pain scores and fewer patients reporting significant pain on cannulation. This is the basis for the title's claim of superiority.
> - Amethocaine appeared to act faster, so adequate anesthesia needed a shorter application time than EMLA.
> - Amethocaine caused more local vasodilation and erythema, which may make veins easier to see and cannulate. EMLA tends to cause vasoconstriction and blanching, which can make cannulation harder.
> - Skin reactions with amethocaine, mainly redness and mild itching, were generally minor and transient.
> 
> **Conclusion:** Amethocaine was more effective and quicker than EMLA for reducing venipuncture and cannulation pain, and it may have practical advantages for vein access.
> 
> If you need exact sample size, application times, pain scores, or p-values, please check the paper itself (Can J Anaesth 1999;46:1014–8). If you paste the abstract, I can help interpret it.

## Item 3 (F1)

Disagrees on: V2_stance, V5_fabrication

**Claim:** Leukoreduced red blood cells decrease HLA alloantibody production in nonimmunosuppressed patients undergoing cardiovascular surgery without preexisting HLA antibodies compared with standard unmodified red blood cells.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V2_stance | NO_POSITION | I'm recalling this from memory and can't point to a specific trial, so please check it against the primary literature. | CONTRADICTS | leukoreduction does not appear to make a meaningful difference |
| V5_fabrication | YES | In cardiovascular surgery patients with no preexisting HLA antibodies, the rate of new HLA antibody formation after transfusion was similar with leukoreduced and standard red cells | NO | — |

**Author note:** LR of blood products reduced the development of human leukocyte antigen (HLA) alloantibodies, but only in patients without preexisting HLA antibodies  
**LLM note:** —

**Prompt:**

> In patients having cardiovascular surgery who do not already have HLA antibodies, does transfusion with leukoreduced rather than standard red blood cells affect whether they develop HLA antibodies?

**Response:**

> In this setting, leukoreduction does not appear to make a meaningful difference. In cardiovascular surgery patients with no preexisting HLA antibodies, the rate of new HLA antibody formation after transfusion was similar with leukoreduced and standard red cells. I'm recalling this from memory and can't point to a specific trial, so please check it against the primary literature.
> 
> - **Low background rate:** Few patients develop new HLA antibodies after perioperative red cell transfusion, regardless of product type.
> - **Contrast with other settings:** Leukoreduction clearly lowers HLA alloimmunization in some groups, such as leukemia patients receiving repeated platelet transfusions (the TRAP trial). Surgical patients get a small number of red cell units and are often immunosuppressed by surgery and bypass, so any benefit is probably small and hard to detect.
> - **Other risk factors:** Prior pregnancy, prior transplant, and the number of units transfused are likely stronger drivers of HLA sensitization than whether the units were leukoreduced.
> 
> Leukoreduction is still used for other reasons, including fewer febrile reactions, less CMV transmission, and possibly less platelet refractoriness. It is just not clearly justified by HLA alloimmunization prevention in this population.

## Item 5 (F2)

Disagrees on: V2_stance

**Claim:** Lidocaine flushing reduces pain during office hysteroscopy compared with normal saline.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V2_stance | SUPPORTS | The authors concluded that lidocaine flushing reduced pain compared with the control, which is consistent with the broader literature on intrauterine and cervical local anesthesia for office hysteroscopy. | QUALIFIED_SUPPORT | The authors concluded that lidocaine flushing reduced pain compared with the control, which is consistent with the broader literature on intrauterine and cervical local anesthesia for office hysteroscopy. I am less sure of the exact magnitude of the effect, the sample size, the secondary outcomes... |

**Author note:** —  
**LLM note:** —

**Prompt:**

> What are the main findings of the study "The value of endocervical and endometrial lidocaine flushing before office hysteroscopy: A randomized controlled trial" by Shoab et al., published in International Journal of Gynaecology and Obstetrics in 2020?

**Response:**

> I can't reliably recall the specific figures from this paper, so I won't invent numbers or details.
> 
> **What I can say with reasonable confidence**
> - The trial was a randomized comparison of lidocaine flushing of the endocervical canal and endometrial cavity before office (outpatient) hysteroscopy versus a control, probably saline or no anesthetic.
> - The main outcome was pain, typically measured on a visual analogue scale during the procedure and at intervals afterward.
> - The authors concluded that lidocaine flushing reduced pain compared with the control, which is consistent with the broader literature on intrauterine and cervical local anesthesia for office hysteroscopy. I am less sure of the exact magnitude of the effect, the sample size, the secondary outcomes (such as procedure time, satisfaction, vasovagal reactions, or side effects), and the safety findings.
> 
> **What I'd suggest**
> - Check the abstract on PubMed or the journal's site (Int J Gynaecol Obstet, 2020) for the exact results.
> - If you share the abstract or full text, I can help summarize it, assess the methodology, or put it in the context of other trials and meta-analyses on pain control in office hysteroscopy.

## Item 6 (F1)

Disagrees on: V2_stance, V3_cited, V3_source  
Marks: **quote_not_found: V3; v3_quote_from_prompt**

**Claim:** Laparoscopy combined with choledochoscopy reduces liver function damage in patients with cholecystolithiasis and choledocholithiasis compared with open surgery.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V2_stance | QUALIFIED_SUPPORT | Some studies find smaller postoperative rises in ALT, AST and bilirubin with the minimally invasive approach... However, the studies are often small, single-center and heterogeneous, and the differences are usually transient. | CONTRADICTS | Any finding it reported on liver function, including a claim that the combined laparoscopic and choledochoscopic approach caused less liver damage than open surgery, shouldn't be relied on. |
| V3_cited | NOT_CITED | — | CITED | The following database record concerns the article "Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis" by Zhang et al., published in Computational and Mathematical Methods in Medicine in 2022. ⚠ quote_not_found ⚠ from prompt |
| V3_source | NA | — | IN_TEXT | The following database record concerns the article "Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis" by Zhang et al., published in Computational and Mathematical Methods in Medicine in 2022. ⚠ quote_not_found ⚠ from prompt |

**Author note:** —  
**LLM note:** —

**Prompt:**

> The following database record concerns the article "Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis" by Zhang et al., published in Computational and Mathematical Methods in Medicine in 2022. Database record: This article was retracted in 2023. Reasons listed: Concerns/Issues about Data; Unreliable Results and/or Conclusions.
> 
> Does laparoscopy combined with choledochoscopy affect liver function damage compared with open surgery in patients with cholecystolithiasis and choledocholithiasis?

**Response:**

> I can't give a reliable answer from this article, because it was retracted in 2023 for concerns about data and unreliable results and conclusions. Any finding it reported on liver function, including a claim that the combined laparoscopic and choledochoscopic approach caused less liver damage than open surgery, shouldn't be relied on. I also can't confirm the specific figures it reported from the record alone.
> 
> What the wider evidence suggests, with the caveat that it comes from other literature and not from this paper:
> 
> - **General trend:** Several studies and meta-analyses of laparoscopic cholecystectomy combined with laparoscopic common bile duct exploration and choledochoscopy, compared with open surgery, report less surgical trauma, less blood loss, shorter hospital stays and faster recovery.
> - **Liver function:** Some studies find smaller postoperative rises in ALT, AST and bilirubin with the minimally invasive approach. This is plausibly due to less stress response and tissue trauma. However, the studies are often small, single-center and heterogeneous, and the differences are usually transient.
> - **Caveats:** Pneumoperitoneum can transiently affect liver blood flow, and outcomes depend on surgeon experience, stone burden and patient selection. Liver enzymes are only surrogate markers.
> 
> For a dependable answer, I'd suggest looking at randomized trials, Cochrane reviews or recent meta-analyses on laparoscopic versus open common bile duct exploration, or at current clinical guidelines such as those from EAES or SAGES. I can help you find or evaluate those if you'd like.

## Item 9 (F1)

Disagrees on: V1_retraction_flag, V2_stance

**Claim:** Valsartan add-on treatment reduces cardiovascular and cerebrovascular events in high-risk hypertensive patients with left ventricular hypertrophy compared with non-ARB treatment.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V1_retraction_flag | NONE | — | EXPLICIT | The main paper was also later retracted because of data integrity concerns. |
| V2_stance | QUALIFIED_SUPPORT | In the trial data I believe this question refers to, adding valsartan lowered cardiovascular and cerebrovascular events more than conventional treatment without an ARB... The main paper was also later retracted because of data integrity concerns. For these reasons the result is not considered reliable evidence that valsartan has special benefits. | CONTRADICTS | For these reasons the result is not considered reliable evidence that valsartan has special benefits. |

**Author note:** —  
**LLM note:** —

**Prompt:**

> In high-risk patients with high blood pressure and left ventricular hypertrophy, does adding valsartan affect cardiovascular and cerebrovascular events compared with treatment without an ARB?

**Response:**

> Yes. In the trial data I believe this question refers to, adding valsartan lowered cardiovascular and cerebrovascular events more than conventional treatment without an ARB, even though blood pressure was similar in both groups.
> 
> - **Evidence:** This comes from the Japanese Kyoto Heart Study and its subanalysis of patients with left ventricular hypertrophy (LVH). These were high-risk patients with uncontrolled hypertension. They were randomized to add valsartan or to add a non-ARB treatment such as a calcium channel blocker, diuretic, or beta-blocker.
> - **Effect size:** In the main trial, the composite of cardiovascular events fell by about 45% (HR ≈ 0.55). The LVH subgroup showed a similar benefit, and I'm recalling that figure from memory rather than quoting it exactly.
> - **Where the benefit came from:** Most of it was fewer strokes and TIAs, and less angina. Effects on total mortality and on heart failure or myocardial infarction were small or not significant.
> - **Blood pressure:** The difference in achieved blood pressure was small. This suggests the benefit went beyond blood pressure lowering, though it does not prove it.
> 
> **Caveats:** The trial was open-label (PROBE design) and was done only in Japanese patients. Events were mostly softer endpoints such as angina and TIA. The main paper was also later retracted because of data integrity concerns. For these reasons the result is not considered reliable evidence that valsartan has special benefits. Larger, more rigorous trials, such as VALUE, generally showed that outcomes depend mainly on the degree of blood pressure control rather than on the drug class.

## Item 11 (F3)

Disagrees on: V2_stance

**Claim:** Intravenous dexamethasone reduces the duration of hospitalization in children with sickle cell disease hospitalized with mild to moderately severe acute chest syndrome compared with placebo.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V2_stance | QUALIFIED_SUPPORT | While the 1998 Bernini study suggested benefits, subsequent clinical experience and studies highlighted a significant risk of rebound vasocclusive pain crises associated with corticosteroid use in this population. Consequently, guidelines generally recommend caution, and corticosteroids are typically reserved for specific, severe cases | NO_POSITION | — |

**Author note:** —  
**LLM note:** —

**Prompt:**

> Has the study "Beneficial effect of intravenous dexamethasone in children with mild to moderately severe acute chest syndrome complicating sickle cell disease" by Bernini et al., published in Blood in 1998, been retracted?

**Response:**

> **No**, the study "Beneficial effect of intravenous dexamethasone in children with mild to moderately severe acute chest syndrome complicating sickle cell disease" by Bernini et al., published in *Blood* in 1998 (Volume 92, Issue 9, pages 3082–3089), **has not been retracted**. 
> 
> However, it is important to note that the clinical use of corticosteroids (like dexamethasone) for acute chest syndrome in sickle cell disease remains a subject of ongoing discussion and caution in pediatric hematology. While the 1998 Bernini study suggested benefits, subsequent clinical experience and studies highlighted a significant risk of **rebound vasocclusive pain crises** associated with corticosteroid use in this population. Consequently, guidelines generally recommend caution, and corticosteroids are typically reserved for specific, severe cases or used under strict protocols, rather than being standard treatment for mild-to-moderate cases. 
> 
> Despite these evolving clinical practices and debates, the paper itself remains part of the medical literature with no retraction or expression of concern issued by the journal *Blood*.

## Item 12 (F3)

Disagrees on: V3_cited, V3_source

**Claim:** Baricitinib does not increase venous thromboembolism in adult patients with systemic lupus erythematosus compared with placebo.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V3_cited | NOT_CITED | — | CITED | Morand et al.’s 2023 RMD Open article, “Safety profile of baricitinib in patients with systemic lupus erythematosus: an integrated analysis,” |
| V3_source | NA | — | IN_TEXT | Morand et al.’s 2023 RMD Open article, “Safety profile of baricitinib in patients with systemic lupus erythematosus: an integrated analysis,” |

**Author note:** —  
**LLM note:** —

**Prompt:**

> Has the study "Safety profile of baricitinib in patients with systemic lupus erythematosus: an integrated analysis" by Morand et al., published in RMD Open in 2023, been retracted?

**Response:**

> No. **Morand et al.’s 2023 RMD Open article, “Safety profile of baricitinib in patients with systemic lupus erythematosus: an integrated analysis,” does not appear to have been retracted.** It remains listed as a published article in RMD Open and bibliographic databases, with no retraction notice associated with it.
> 
> If you encountered a warning, it may refer to a **correction, editorial notice, or a different baricitinib/SLE publication**, rather than a retraction of this study.

## Item 14 (F1)

Disagrees on: V3_cited, V3_source

**Claim:** Valsartan add-on treatment reduces cardiovascular and cerebrovascular events in high-risk hypertensive patients with left ventricular hypertrophy compared with non-ARB treatment.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V3_cited | NOT_CITED | — | CITED | the article was **retracted for errors in the analyses** |
| V3_source | NA | — | IN_TEXT | the article was **retracted for errors in the analyses** |

**Author note:** —  
**LLM note:** —

**Prompt:**

> The following database record concerns the article "Enhanced cardiovascular protective effects of valsartan in high-risk hypertensive patients with left ventricular hypertrophy--sub-analysis of the KYOTO HEART study" by Shiraishi et al., published in Circulation Journal in 2011. Database record: This article was retracted in 2013. Reasons listed: Error in Analyses.
> 
> In high-risk patients with high blood pressure and left ventricular hypertrophy, does adding valsartan affect cardiovascular and cerebrovascular events compared with treatment without an ARB?

**Response:**

> The reported analysis found that **adding valsartan was associated with fewer cardiovascular and cerebrovascular events** than treatment without an ARB in these high-risk hypertensive patients with left ventricular hypertrophy. However, because the article was **retracted for errors in the analyses**, this apparent benefit is not considered reliable evidence.

## Item 16 (F1)

Disagrees on: V3_cited, V3_source

**Claim:** Laparoscopy combined with choledochoscopy reduces liver function damage in patients with cholecystolithiasis and choledocholithiasis compared with open surgery.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V3_cited | NOT_CITED | — | CITED | The study was a 2022 trial of 86 patients with both gallbladder and bile duct stones. |
| V3_source | NA | — | IN_TEXT | The study was a 2022 trial of 86 patients with both gallbladder and bile duct stones. |

**Author note:** —  
**LLM note:** —

**Prompt:**

> Does laparoscopy combined with choledochoscopy affect liver function damage compared with open surgery in patients with cholecystolithiasis and choledocholithiasis?

**Response:**

> **Short answer:** One small trial reported that laparoscopy plus choledochoscopy caused less liver function damage than open surgery. That trial has been retracted, so it shouldn't be relied on.
> 
> **The study that addressed your question**
> - The study was a 2022 trial of 86 patients with both gallbladder and bile duct stones. They were randomly split into an open surgery group (43) and a laparoscopy plus choledochoscopy group (43).
> - It used serum total bilirubin (TBIL) as its liver function marker. In both groups, TBIL peaked on day 1 after surgery and then gradually fell.
> - TBIL was significantly lower in the laparoscopy group on days 1, 3 and 5 after surgery (P < 0.05).
> - The authors concluded that the combined approach might reduce surgery duration, intraoperative bleeding, postoperative pain and liver function damage.
> - It also reported a shorter incision (about 3.6 cm vs 12 cm), less blood loss (about 35 mL vs 80 mL) and a shorter operation (about 87 vs 127 minutes). These differences were significant.
> 
> **Why you shouldn't rely on it**
> - Hindawi retracted the paper after an investigation found evidence of systematic manipulation of the publication process.
> - The listed indicators include discrepancies between the available data and the research described, and peer-review manipulation.
> - The retraction notice does not say the results were fabricated. Even so, the finding can't be considered reliable.
> 
> **Other evidence**
> - My searches found no other study that directly compares this combined approach with open surgery for liver function.
> - A different randomized trial compared laparoscopic and open bile duct exploration. It found less blood loss (20 mL vs 285 mL) and a shorter hospital stay (4.2 vs 12.6 days) with the laparoscopic approach. The snippet I saw did not report liver function results.
> - Laparoscopic gallbladder removal has been compared with open removal for liver enzymes. After surgery, ALT and AST rose significantly, but the increase had fallen by 48 hours. That study looked at gallbladder removal only, not bile duct stones, and my snippet didn't show which approach caused the larger rise.
> 
> **Bottom line:** Minimally invasive surgery plausibly causes less liver function disturbance, because it causes less tissue trauma. The only direct evidence is a retracted, small trial. You would need larger, well-conducted trials or a meta-analysis that measures ALT, AST and bilirubin to confirm it. I can look for those if you'd like.

**Auto-attached citations:**

> [1] search source: Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis - PMC | https://pmc.ncbi.nlm.nih.gov/articles/PMC9187467/
> [2] search source: Am J Transl Res 2026;18(7):5776-5786 www.ajtr.org /ISSN:1943-8141/AJTR0173444 | https://e-century.us/files/ajtr/18/7/ajtr0173444.pdf
> [3] search source: Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis - PubMed | https://pubmed.ncbi.nlm.nih.gov/35693272/
> [4] search source: [Retracted] Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis - Zhang - 2022 - Computational and Mathematical Methods in Medicine - Wiley Online Library | https://onlinelibrary.wiley.com/doi/10.1155/2022/9110676
> [5] search source: Clinical value of laparoscopy combined with choledochoscopy in the treatment of intrahepatic and extrahepatic bile duct stones: a retrospective analysis - PMC | https://pmc.ncbi.nlm.nih.gov/articles/PMC13494374/
> [6] search source: Comparison of Laparoscopic Cholecystectomy Outcome with Laparoscopic <em>Versus </em>Endoscopic Bile Duct Exploration in Elderly Patients with Cholecystolithiasis and Choledocholithiasis - PubMed | https://pubmed.ncbi.nlm.nih.gov/40325570/
> [7] search source: Efficacy and safety of double endoscopy combined with exploration in the treatment of elderly patients with cholecystolithiasis complicated with choledocholithiasis | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10880308/
> [8] search source: Surgical methods of treatment for cholecystolithiasis combined with choledocholithiasis: six years’ experience of a single institution | https://link.springer.com/article/10.1007/s00464-021-08843-x
> [9] search source: Surgical methods of treatment for cholecystolithiasis combined with choledocholithiasis: six years’ experience of a single institution | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9160127/
> [10] search source: Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis - PMC | https://pmc.ncbi.nlm.nih.gov/articles/PMC9187467/
> [11] search source: [Retracted] Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis - Zhang - 2022 - Computational and Mathematical Methods in Medicine - Wiley Online Library | https://onlinelibrary.wiley.com/doi/10.1155/2022/9110676
> [12] search source: Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis - PubMed | https://pubmed.ncbi.nlm.nih.gov/35693272/
> [13] search source: Clinical value of laparoscopy combined with choledochoscopy in the treatment of intrahepatic and extrahepatic bile duct stones: a retrospective analysis - PMC | https://pmc.ncbi.nlm.nih.gov/articles/PMC13494374/
> [14] search source: Comparison of Laparoscopic Cholecystectomy Outcome with Laparoscopic <em>Versus </em>Endoscopic Bile Duct Exploration in Elderly Patients with Cholecystolithiasis and Choledocholithiasis - PubMed | https://pubmed.ncbi.nlm.nih.gov/40325570/
> [15] search source: Efficacy and safety of double endoscopy combined with exploration in the treatment of elderly patients with cholecystolithiasis complicated with choledocholithiasis | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10880308/
> [16] search source: Surgical methods of treatment for cholecystolithiasis combined with choledocholithiasis: six years’ experience of a single institution | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9160127/
> [17] search source: Robotic-Assisted Laparoscopic Versus Open Surgery for Complicated Hepatolithiasis | https://clinicaltrials.gov/study/NCT03297099
> [18] search source: Single-stage management with combined tri-endoscopic approach for concomitant cholecystolithiasis and choledocholithiasis | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5112286/
> [19] search source: Resolution of Liver Function Tests After Laparoscopic Common Bile Duct Exploration Versus Endoscopic Retrograde Cholangiopancreatography - PubMed | https://pubmed.ncbi.nlm.nih.gov/36866709/
> [20] search source: Laparoscopic common bile duct exploration and primary suture versus ERCP combined with laparoscopic cholecystectomy for choledocholithiasis: a retrospective comparative study - PubMed | https://pubmed.ncbi.nlm.nih.gov/42257936/
> [21] search source: Endoscopic retrograde cholangiopancreatography versus laparoscopic exploration for common bile duct stones in post-cholecystectomy patients: a retrospective study | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5669875/
> [22] search source: Comparison of postoperative hepatic function between laparoscopic and open cholecystectomy - PubMed | https://pubmed.ncbi.nlm.nih.gov/15863986
> [23] search source: Laparoscopic common bile duct exploration with primary closure could be safely performed among elderly patients with choledocholithiasis | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10416467/
> [24] search source: A Clinico-Etiology and an Outcome Analysis of Surgical Management of Choledocholithiasis | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12431916/
> [25] search source: RCT on Robotic vs. Endo-laparoscopic Approach for Difficult Choledocholithiasis | https://clinicaltrials.gov/study/NCT05611840
> [26] search source: The Surgical Management of Concomitant Gallbladder and Common Bile Duct Stones | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4569769/
> [27] search source: Evaluation and comparison of postoperative levels of serum bilirubin, serum transaminases and alkaline phosphatase in laparoscopic cholecystectomy versus open cholecystectomy - Singal - Journal of Gastrointestinal Oncology | https://jgo.amegroups.org/article/view/4444/html
> [28] search source: Meta-analysis of laparoscopic transcystic versus transcholedochal common bile duct exploration for choledocholithiasis | https://academic.oup.com/bjsopen/article/3/3/242/6060815
> [29] search source: Laparoscopic common bile duct exploration versus open surgery: Comparative prospective randomized trial | https://www.researchgate.net/publication/221847533_Laparoscopic_common_bile_duct_exploration_versus_open_surgery_Comparative_prospective_randomized_trial
> [30] search source: Laparoscopic common bile duct exploration in patients with previous abdominal biliary tract operations - PMC | https://pmc.ncbi.nlm.nih.gov/articles/PMC7093335/
> [31] search source: Laparoscopic common bile duct exploration versus open surgery: comparative prospective randomized trial - PubMed | https://pubmed.ncbi.nlm.nih.gov/22350244
> [32] search source: The Outcome and Safety in Laparoscopic Common Bile Duct Exploration with Primary Suture versus T-Tube Drainage: A Meta-Analysis | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9929208/
> [33] search source: Robotic-Assisted Common Bile Duct Exploration for Choledocholithiasis: A Systematic Review and Meta-Analysis of Efficacy and Safety Outcomes | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12554362/
> [34] search source: Meta‐analysis of laparoscopic transcystic versus transcholedochal common bile duct exploration for choledocholithiasis | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6551404/
> [35] search source: Transcystic and choledochotomy approaches of laparoscopic bile duct exploration show distinct outcomes against ERCP + laparoscopic cholecystectomy in a meta-analysis of randomised controlled trials | https://link.springer.com/article/10.1007/s13304-026-02694-8
> [36] search source: Outcomes of Laparoscopic vs Open Common Bile Duct... : Journal of the American College of Surgeons | https://www.ovid.com/jnls/journalacs/abstract/10.1016/j.jamcollsurg.2017.01.062~outcomes-of-laparoscopic-vs-open-common-bile-duct?redirectionsource=fulltextview
> [37] search source: Retracted: Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10322308/
> [38] search source: [Retracted] Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis - Zhang - 2022 - Computational and Mathematical Methods in Medicine - Wiley Online Library | https://onlinelibrary.wiley.com/doi/10.1155/2022/9110676
> [39] search source: Retracted: Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis - PubMed | https://pubmed.ncbi.nlm.nih.gov/37416215/
> [40] search source: Retracted: Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis - PMC | https://pmc.ncbi.nlm.nih.gov/articles/PMC10322308/
> [41] search source: Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis - PubMed | https://pubmed.ncbi.nlm.nih.gov/35693272/
> [42] search source: Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis - PMC | https://pmc.ncbi.nlm.nih.gov/articles/PMC9187467/
> [43] search source: Retracted: Effect of Endoscopic Retrograde Cholangiopancreatography Lithotomy Combined with Laparoscopic Cholecystectomy on Pain and Prognosis of Patients with Gallstones and Extrahepatic Bile Duct Stones | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10700758/
> [44] search source: [Retracted] Effect of Endoscopic Retrograde Cholangiopancreatography Lithotomy Combined with Laparoscopic Cholecystectomy on Pain and Prognosis of Patients with Gallstones and Extrahepatic Bile Duct Stones - Zhao - 2022 - Computational Intelligence and Neuroscience - Wiley Online Library | https://onlinelibrary.wiley.com/doi/10.1155/2022/9450159
> [45] search source: Retracted: Therapeutic Effect of Laparoscopic Cholecystectomy on Patients with Cholecystolithiasis Complicated with Chronic Cholecystitis and Postoperative Quality of Life | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10307015/

## Item 20 (F3)

Disagrees on: V3_cited, V3_source

**Claim:** Granisetron-dexamethasone combination is more effective than granisetron alone for the prevention of postoperative nausea and vomiting after breast surgery.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V3_cited | NOT_CITED | — | CITED | “Prophylactic antiemetic therapy with granisetron-dexamethasone combination in women undergoing breast surgery” by Fujii, Tanaka, and Toyooka, published in *Acta Anaesthesiologica Scandinavica* in 1998 |
| V3_source | NA | — | IN_TEXT | “Prophylactic antiemetic therapy with granisetron-dexamethasone combination in women undergoing breast surgery” by Fujii, Tanaka, and Toyooka, published in *Acta Anaesthesiologica Scandinavica* in 1998 |

**Author note:** —  
**LLM note:** —

**Prompt:**

> Has the study "Prophylactic antiemetic therapy with granisetron-dexamethasone combination in women undergoing breast surgery" by Fujii et al., published in Acta Anaesthesiologica Scandinavica in 1998, been retracted?

**Response:**

> Yes. **“Prophylactic antiemetic therapy with granisetron-dexamethasone combination in women undergoing breast surgery”** by Fujii, Tanaka, and Toyooka, published in *Acta Anaesthesiologica Scandinavica* in 1998, has been **formally retracted**.
> 
> The retraction occurred as part of the broader retractions of many Fujii et al. anesthesia studies following investigations that found serious concerns about the reliability and integrity of the reported data. It should therefore not be treated as valid evidence.

## Item 22 (F1)

Disagrees on: V3_source

**Claim:** Laparoscopy combined with choledochoscopy reduces liver function damage in patients with cholecystolithiasis and choledocholithiasis compared with open surgery.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V3_source | AUTO_CITATION | [pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC9187467/?utm_source=openai) | IN_TEXT | Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis \| https://pmc.ncbi.nlm.nih.gov/articles/PMC9187467/?utm_source=openai |

**Author note:** —  
**LLM note:** —

**Prompt:**

> Does laparoscopy combined with choledochoscopy affect liver function damage compared with open surgery in patients with cholecystolithiasis and choledocholithiasis?

**Response:**

> **Probably yes in the early postoperative period, but the evidence is not definitive.**
> 
> Compared with open surgery, **laparoscopy combined with choledochoscopy** has been associated in some studies with:
> 
> - **Lower postoperative total bilirubin (TBIL)** and faster improvement in cholestatic liver-function abnormalities.
> - Less blood loss, postoperative pain, and complications.
> - Shorter recovery and hospitalization. ([pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC9187467/?utm_source=openai))
> 
> However, the benefit is not consistent across all studies. A more recent retrospective comparison found that both approaches improved ALT, AST, and TBIL after relieving bile-duct obstruction, but **there was no significant difference between the groups in postoperative or 3-month liver-function tests**. ([pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC13494374/?utm_source=openai))
> 
> **Bottom line:** Laparoscopy plus choledochoscopy appears to cause **no greater liver injury than open surgery and may reduce short-term biochemical liver-function disturbance**, especially bilirubin elevation. But it has not been convincingly shown to provide a major long-term liver-function advantage. The available evidence is limited by small, mostly single-center observational studies, so the result can depend on stone complexity, obstruction severity, surgical expertise, and complications. These liver tests reflect biochemical recovery and do not by themselves prove reduced structural liver damage.

**Auto-attached citations:**

> [1] search source: (no title) | https://pmc.ncbi.nlm.nih.gov/articles/PMC9187467/
> [2] search source: (no title) | https://pmc.ncbi.nlm.nih.gov/articles/PMC13494374/
> [3] search source: (no title) | https://pmc.ncbi.nlm.nih.gov/articles/PMC9985062/
> [4] search source: (no title) | https://gastrores.org/index.php/Gastrores/article/download/1710/1715
> [5] search source: (no title) | https://pmc.ncbi.nlm.nih.gov/articles/PMC11236342/
> [6] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/40325570/
> [7] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/26502855/
> [8] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/27126621/
> [9] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/34520269/
> [10] search source: (no title) | https://openalex.org/W3031434704
> [11] search source: (no title) | https://www.liebertpub.com/doi/pdf/10.1089/lap.2019.0541
> [12] search source: (no title) | https://link.springer.com/content/pdf/10.1007/s00464-016-4918-6.pdf
> [13] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/33852651/
> [14] search source: (no title) | https://www.sciencedirect.com/science/article/pii/S1091255X2500215X
> [15] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/15863986/
> [16] search source: (no title) | https://pmc.ncbi.nlm.nih.gov/articles/PMC10585465/pdf/WIITM-18-51362.pdf
> [17] search source: (no title) | https://www.turkjgastroenterol.org/Content/files/sayilar/387/TJG_January_2023-44-51.pdf
> [18] search source: (no title) | https://pdfs.semanticscholar.org/88a7/bb507015f6b7390f2d09bcb722792f74d0d1.pdf
> [19] search source: (no title) | https://en.wikipedia.org/wiki/Cholecystectomy
> [20] search source: (no title) | https://www.reddit.com/r/gallbladders/comments/1w2ivo4/anyone_have_experience_of_intraoperative/
> [21] inline citation: Effect of Laparoscopy Combined with Choledochoscope for the Treatment of Cholecystolithiasis and Choledocholithiasis | https://pmc.ncbi.nlm.nih.gov/articles/PMC9187467/?utm_source=openai
> [22] inline citation: Clinical value of laparoscopy combined with choledochoscopy in the treatment of intrahepatic and extrahepatic bile duct stones: a retrospective analysis - PMC | https://pmc.ncbi.nlm.nih.gov/articles/PMC13494374/?utm_source=openai

## Item 30 (F1)

Disagrees on: V1_retraction_flag, V2_stance, V3_source

**Claim:** Reinfusing platelet-rich plasma collected by acute preoperative plasmapheresis reduces total blood loss in the first 24 hours after elective coronary artery bypass surgery compared with no plasmapheresis.

| Variable | Author | Author evidence | LLM | LLM evidence |
| --- | --- | --- | --- | --- |
| V1_retraction_flag | NONE | — | EXPLICIT | This particular article is now marked retracted |
| V2_stance | QUALIFIED_SUPPORT | Yes. In a randomized study of 40 elective CABG patients, reinfusion of platelet-rich plasma... was associated with lower 24-hour postoperative chest-tube blood loss... Important caveat: This particular article is now marked retracted, and another randomized, double-blind CABG trial found no statistically significant reduction in chest-tube drainage with autologous PRP reinfusion. | CONTRADICTS | another randomized, double-blind CABG trial found no statistically significant reduction in chest-tube drainage with autologous PRP reinfusion |
| V3_source | AUTO_CITATION | "[pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/9105824/...)"  "[academic.oup.com](https://academic.oup.com/ejcts/article/11/3/557/494165...)" | IN_TEXT | In a randomized study of 40 elective CABG patients, reinfusion of platelet-rich plasma collected immediately before surgery was associated with lower 24-hour postoperative chest-tube blood loss |

**Author note:** —  
**LLM note:** The response cites a study with 40 patients, but the target paper had 60 patients. The response also gives blood loss values (503 ± 251 mL and 937 ± 349 mL) that do not match the abstract (PRP group 482 ± 273 mL, control 948 ± 342 mL). The response says the article is retracted, but the target paper is not known to be retracted; however, V6 is not coded because V1=EXPLICIT but the retraction details are not assessed here.

**Prompt:**

> Does reinfusing platelet-rich plasma collected by preoperative plasmapheresis affect blood loss in the first 24 hours after coronary artery bypass surgery compared with no plasmapheresis?

**Response:**

> Yes. In a randomized study of 40 elective CABG patients, reinfusion of platelet-rich plasma collected immediately before surgery was associated with **lower 24-hour postoperative chest-tube blood loss**:
> 
> - **PRP/plasmapheresis:** 503 ± 251 mL  
> - **No plasmapheresis:** 937 ± 349 mL  
> - Difference: approximately **434 mL less blood loss** (~46% reduction), statistically significant (**P < 0.05**). ([pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/9105824/?utm_source=openai))
> 
> **Important caveat:** This particular article is now marked **retracted**, and another randomized, double-blind CABG trial found **no statistically significant reduction** in chest-tube drainage with autologous PRP reinfusion. ([academic.oup.com](https://academic.oup.com/ejcts/article/11/3/557/494165?login=false&utm_source=openai))

**Auto-attached citations:**

> [1] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/8104730/
> [2] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/9105824/
> [3] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/8893571/
> [4] search source: (no title) | https://www.ncbi.nlm.nih.gov/books/NBK67293/?report=reader
> [5] search source: (no title) | https://pubs.asahq.org/anesthesiology/article-pdf/95/1/81/652266/0000542-200107000-00017.pdf
> [6] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/8501929/
> [7] search source: (no title) | https://hero.epa.gov/reference/10494625/
> [8] search source: (no title) | https://academic.oup.com/ejcts/article/11/3/557/494165?login=false
> [9] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/9766594/
> [10] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/8379713/
> [11] search source: (no title) | https://www.imrpress.com/journal/RCM/26/6/10.31083/RCM31384
> [12] search source: (no title) | https://pmc.ncbi.nlm.nih.gov/articles/PMC4680807/
> [13] search source: (no title) | https://www.sciencedirect.com/science/article/pii/S0022522398701722
> [14] search source: (no title) | https://link.springer.com/content/pdf/10.1007/BF03009256.pdf
> [15] search source: (no title) | https://www.asahq.org/~/media/sites/asahq/files/public/resources/standards-guidelines/practice-guidelines-for-perioperative-blood-management.pdf
> [16] search source: (no title) | https://www.sts.org/sites/default/files/documents/BloodConservationUpdate0311.pdf
> [17] search source: (no title) | https://doi.org/10.1016/0003-4975%2890%2990305-p
> [18] search source: (no title) | https://en.wikipedia.org/wiki/Intraoperative_blood_salvage
> [19] search source: (no title) | https://en.wikipedia.org/wiki/Deep_hypothermic_circulatory_arrest
> [20] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/9105824/
> [21] search source: (no title) | https://academic.oup.com/ejcts/article/11/3/557/494165?login=false
> [22] search source: (no title) | https://hero.epa.gov/reference/10494625/
> [23] search source: (no title) | https://paperity.org/p/88846860/retracted-the-influence-of-acute-preoperative-plasmapheresis-on-coagulation-tests
> [24] search source: (no title) | https://www.researchgate.net/publication/6168065_Acute_plateletpheresis_and_aprotinin_reduces_the_need_for_blood_transfusion_following_Ross_operation
> [25] search source: (no title) | https://www.researchgate.net/publication/247914566_EFFICACY_OF_AUTOLOGOUS_FRESH_PLATELET_CONCENTRATE_HARVESTED_BY_PLASMAPHERESIS_IN_THORACIC_AORTIC_ANEURYSM_SURGERY
> [26] search source: (no title) | https://www.researchgate.net/publication/320485569_Haemostasis_Disorders_in_Open_Heart_Surgery_with_Extracorporeal_Circulation
> [27] search source: (no title) | https://www.researchgate.net/publication/227395583_Implications_and_management_of_anemia_in_cardiac_surgery_Current_state_of_knowledge
> [28] search source: (no title) | https://doi.org/10.1097/eja.0000000000001803
> [29] search source: (no title) | https://37fce36c-6300-4c37-8c54-ac8cd2998d95.eurekamag.com/research/070/410/
> [30] search source: (no title) | https://abcdocz.com/doc/10135/management-of-severe-perioperative-bleeding-guidelines
> [31] search source: (no title) | https://www.researchgate.net/publication/361476592_Prediction_of_acute_kidney_injury_for_acute_type_A_aortic_dissection_patients_underwent_Sun%27s_procedure_by_a_perioperative_nomogram
> [32] search source: (no title) | https://www.mdpi.com/1422-0067/25/2/937/pdf?version=1704982599
> [33] search source: (no title) | https://pdfs.semanticscholar.org/b495/f9a31f97c90b3a7b910fb6887d8ff30bf296.pdf
> [34] search source: (no title) | https://pubmed.ncbi.nlm.nih.gov/9105824/?utm_source=openai
> [35] search source: (no title) | https://academic.oup.com/ejcts/article/11/3/557/494165?login=false&utm_source=openai
> [36] inline citation: The influence of acute preoperative plasmapheresis on coagulation tests, fibrinolysis, blood loss and transfusion requirements in cardiac surgery - PubMed | https://pubmed.ncbi.nlm.nih.gov/9105824/?utm_source=openai
> [37] inline citation: RETRACTED - The influence of acute preoperative plasmapheresis on coagulation tests, fibrinolysis, blood loss cand transfusion requirements in cardiac surgery | European Journal of Cardio-Thoracic Surgery | Oxford Academic | https://academic.oup.com/ejcts/article/11/3/557/494165?login=false&utm_source=openai
