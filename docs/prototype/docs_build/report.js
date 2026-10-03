const fs = require("fs");
const { R, pct, f2, f3, makeKit, REFS, d } = require("./helpers");
const { Document, Packer, Paragraph, TextRun, AlignmentType, LevelFormat, Footer, PageNumber,
        TableOfContents, HeadingLevel, BorderStyle, SectionType, PositionalTab, PositionalTabAlignment, PositionalTabRelativeTo, PositionalTabLeader } = d;
const K = makeKit({ size: 24, line: 300, pAfter: 140 });
const { P, B, N, T, TCap, Fig, Code, Brk } = K;
const HEADS = [];
const H = (lvl, text) => { if (lvl <= 2) HEADS.push([lvl, text]); return K.H(lvl, text); };
const PAGES = fs.existsSync(__dirname + "/pages.json") ? JSON.parse(fs.readFileSync(__dirname + "/pages.json", "utf8")) : {};

// ---------------------------------------------------------------- numbers
const E1 = R.E1_dept, PROP = E1["Char + word TF-IDF + LogReg (proposed)"], CHAR = E1["Char n-gram TF-IDF + LogReg"];
const KW = E1["Keyword lexicon (no ML)"];
const E3 = R.E3_calibration, tau50 = R.E3_abstention_curve.find(c => c.tau === 0.5);
const E4 = R.E4_ward, E5 = R.E5_severity, E6 = R.E6_dedup, E7 = R.E7_asr_noise, E8 = R.E8_end_to_end;
const nErr = R.E2_confusions.length;
const nAuto = E8.counts.auto_correct + (E8.counts.auto_wrong_dept || 0) + (E8.counts.auto_wrong_ward || 0);
const deptErrCaught = nErr - (E8.counts.auto_wrong_dept || 0);
const DATA = R.data;
const cer10 = E7.find(e => e.cer === 0.1), cer20 = E7.find(e => e.cer === 0.2), cer30 = E7.find(e => e.cer === 0.3);

// ---------------------------------------------------------------- title page
const TP = (t, o = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: o.after ?? 120, before: o.before ?? 0 },
  children: [new TextRun({ text: t, bold: o.bold, size: o.size || 24, italics: o.it })] });
const title = [
  TP("A Mini-Project Report on", { before: 600, size: 26, it: true }),
  TP("NagarVani: A Marathi Voice-First AI Triage Layer", { bold: true, size: 36, before: 200, after: 40 }),
  TP("for Municipal Grievance Redressal (PMC)", { bold: true, size: 36, after: 360 }),
  TP("Submitted in partial fulfilment of the requirements of the course", { size: 24 }),
  TP("IT3232 — Artificial Intelligence (Course Project)", { bold: true, size: 24 }),
  TP("Third Year B.Tech. — Information Technology", { size: 24, after: 400 }),
  TP("Submitted by", { it: true, size: 24, after: 160 }),
  K.T(["Name", "PRN / Roll No."], [["[Student Name 1]", "[PRN]"], ["[Student Name 2]", "[PRN]"],
       ["[Student Name 3]", "[PRN]"], ["[Student Name 4]", "[PRN]"]], [4200, 2800], { size: 22 }),
  TP("Under the guidance of", { it: true, size: 24, before: 400, after: 80 }),
  TP("Prof. (Dr.) Pravin R. Futane", { bold: true, size: 26, after: 500 }),
  TP("Department of Information Technology", { bold: true, size: 26, after: 40 }),
  TP("Vishwakarma Institute of Technology, Pune", { bold: true, size: 26, after: 40 }),
  TP("(An Autonomous Institute affiliated to Savitribai Phule Pune University)", { size: 22, after: 40 }),
  TP("Academic Year 2026–27", { size: 24 }),
  Brk(),
];

// ---------------------------------------------------------------- abstract
const abstract = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: "ABSTRACT", bold: true, size: 28 })] }),
  P(`The Pune Municipal Corporation (PMC) receives civic complaints through many channels, but each complaint must still be read by a nodal officer and manually assigned to a department and a ward office. In the first week of September 2026, PMC CARE 2.0 showed 14,644 pending complaints, and the administration acknowledged that complaints from the preceding two months had not been consistently forwarded to the departments concerned [17]. That manual sorting step is the problem this project addresses.`),
  P(`NagarVani is a prototype triage layer that sits in front of PMC CARE. It accepts a complaint written in Marathi, Hindi, romanised Marathi or Marathi–English code-mixed text, and produces a pre-triaged ticket: a department (one of ten PMC departments), a ward office (one of fifteen), a priority band P1–P4 with a service-level deadline, a duplicate link to any open ticket describing the same defect, and a routing decision. Department assignment uses a character- and word-n-gram TF-IDF logistic-regression classifier. Ward resolution uses a 59-locality gazetteer with suffix-tolerant exact matching and a fuzzy fallback. Severity is assigned by a 19-rule forward-chaining expert system that returns the rules it fired as an explanation. Duplicates are detected by blocking on (ward, department) and comparing location-masked text similarity against two thresholds. A calibrated confidence gate sends uncertain cases to a nodal-officer review queue instead of guessing. Tickets are stored in SQLite and exported as per-ward CSV queues. A Flask console demonstrates the workflow.`),
  P(`On a separately hand-written test set of 160 complaints, the department classifier reaches ${pct(PROP.acc)} accuracy (macro-F1 ${f3(PROP.macro_f1)}, top-3 accuracy ${pct(PROP.top3)}), against ${pct(KW.acc)} for a keyword baseline. At a confidence threshold of 0.50 the pipeline auto-routes ${pct(E8.auto_rate, 0)} of complaints, and ${pct(E8.auto_precision)} of those reach the correct department and ward; ${deptErrCaught} of the ${nErr} department errors are held for human review. When text is corrupted at a simulated 10% character error rate, department macro-F1 falls to ${f3(cer10.dept_macro_f1)}. Adding fuzzy matching raises ward resolution at that error rate from ${pct(cer10.ward_acc_exact, 0)} to ${pct(cer10.ward_acc, 0)}.`),
  P(`All data used here was constructed by the project team, not taken from PMC. No speech model was run, because pretrained Marathi ASR weights could not be downloaded in the build environment. The severity rule base was written by the same team that labelled the test set. These limits are stated wherever the corresponding numbers appear.`),
  P(`**Keywords —** civic grievance triage, Marathi NLP, code-mixed text classification, expert system, production rules, duplicate detection, selective prediction, e-governance.`),
  Brk(),
];

// ---------------------------------------------------------------- index
function buildIndex() {
  const out = [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: "INDEX", bold: true, size: 28 })] })];
  out.push(new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "Section", bold: true, size: 22 }),
    new TextRun({ children: [new PositionalTab({ alignment: PositionalTabAlignment.RIGHT, relativeTo: PositionalTabRelativeTo.MARGIN, leader: PositionalTabLeader.NONE }), "Page"], bold: true, size: 22 })] }));
  for (const [lvl, t] of HEADS) {
    out.push(new Paragraph({ indent: { left: lvl === 1 ? 0 : 400 }, spacing: { before: lvl === 1 ? 100 : 0, after: 30 },
      children: [new TextRun({ text: t, bold: lvl === 1, size: 22 }),
        new TextRun({ children: [new PositionalTab({ alignment: PositionalTabAlignment.RIGHT, relativeTo: PositionalTabRelativeTo.MARGIN, leader: PositionalTabLeader.DOT }), String(PAGES[t] ?? "")], size: 22, bold: lvl === 1 })] }));
  }
  out.push(Brk());
  return out;
}

// ---------------------------------------------------------------- chapter 1
const ch1 = [
  H(1, "Chapter 1  Introduction"),
  H(2, "1.1  Background"),
  P(`Indian urban local bodies run centralised grievance-redressal systems through which citizens report potholes, uncollected garbage, water-supply failures, broken streetlights, blocked drains, stray animals and illegal construction. The Pune Municipal Corporation operates PMC CARE, which accepts complaints through several channels: a mobile application, a web portal, a Marathi web interface, WhatsApp and a call centre. Receiving complaints is not the difficult part. What arrives is unstructured Marathi, Hindi and code-mixed text or voice. A nodal officer must read each complaint and assign it by hand to one of roughly 43 departments across 15 regional (ward) offices.`),
  P(`That manual step is where the process fails. As of the first week of September 2026, PMC CARE 2.0 had 14,644 complaints pending. Kondhwa–Yewalewadi alone accounted for 2,010. The administration attributed the backlog to staff transfers and election-roll (SIR) duty, and acknowledged that complaints registered over the preceding two months had not been consistently forwarded to the departments concerned [17]. A second failure concerns closure. Complaints have been marked resolved without any work on the ground, and the Standing Committee has directed that no complaint be closed without first obtaining the complainant's feedback [18].`),
  P(`Much of the backlog is therefore *triage* work rather than *repair* work. A complaint that has waited two months at the initial stage has not been judged difficult. Nobody has yet read it and forwarded it. That kind of task suits a supervised classifier with a well-defined label space, provided that it can hand uncertain cases back to a human.`),
  H(2, "1.2  Problem statement"),
  P(`**Given a short, unstructured civic complaint in Marathi, Hindi, romanised Marathi or Marathi–English code-mixed text, which carries no explicit category, department, ward or priority label, produce a structured ticket.** The ticket must name the responsible PMC department and ward office, assign a priority band with a service-level deadline, link the complaint to any open ticket that describes the same physical defect, and record whether the system is confident enough to route it automatically. When it is not, the ticket goes to a nodal-officer review queue with the top three department candidates filled in.`),
  H(2, "1.3  Objectives"),
  N("To build a text-normalisation front end that brings Devanagari, romanised and code-mixed input to one canonical form.", "numObj"),
  N("To train and compare department classifiers on the four input varieties, including a no-machine-learning keyword baseline.", "numObj"),
  N("To resolve free-text Pune locality mentions, including inflected Marathi forms such as *कोथरूडमध्ये*, to one of the 15 PMC ward offices, and to flag ambiguous or missing locations rather than guess.", "numObj"),
  N("To design a rule-based expert system (a production system with forward chaining) that assigns priority bands P1–P4 and explains each decision by the rules it fired.", "numObj"),
  N("To detect duplicate reports of the same defect and use the size of the duplicate cluster as evidence of severity.", "numObj"),
  N("To combine these components behind a confidence gate that routes confident cases to per-ward queues and defers the rest to a human, and to measure each component on a held-out test set.", "numObj"),
  H(2, "1.4  Scope and boundary"),
  P(`**PMC CARE exposes no public API, so NagarVani does not file complaints into it.** The prototype writes to a local SQLite database and exports one CSV queue per ward office, plus a nodal-review queue. Its output is a pre-triaged recommendation that awaits confirmation by a nodal officer. It is a triage layer that could sit in front of PMC CARE, and it is presented as a proposal, not as an integration.`),
  P(`The full architecture proposed in PBL-3 has twelve modules, including speech recognition, closure verification from photographs and continual learning. This report implements and evaluates the text-triage core of that design. Section 3.2 lists every module with its implementation status. Speech input is represented by an ASR interface and a transcription-noise simulator, because no Marathi acoustic model could be run in the build environment (Section 4.7).`),
  H(2, "1.5  Organisation of the report"),
  P(`Chapter 2 reviews the relevant literature and states the gaps that the project responds to. Chapter 3 describes the methodology: the data, each module, the expert system and the evaluation protocol. Chapter 4 describes the implementation, the user interface and a worked demonstration. Chapter 5 reports and discusses the measured results, including their limitations. Chapter 6 concludes and sets out future work.`),
  Brk(),
];

// ---------------------------------------------------------------- chapter 2
const ch2 = [
  H(1, "Chapter 2  Relevant Study"),
  P(`No single body of literature covers the NagarVani pipeline end to end. The survey (PBL-2) therefore split the system into the research problems it inherits and reviewed sixteen works in five themes. This chapter summarises that review, and adds the classical AI material on production systems on which the severity module is based.`),
  H(2, "2.1  Speech recognition for low-resource and code-mixed Indian languages"),
  P(`Whisper [1] trains a single encoder–decoder transformer on about 680,000 hours of weakly supervised multilingual audio. It generalises zero-shot to noisy and accented speech, but its quality in a language depends on how much of that language was in the training mix, and Marathi is a small share. wav2vec 2.0 [2] learns speech representations without transcripts through a contrastive masked objective. Fine-tuned on as little as ten minutes of labelled speech, it reaches usable error rates, and this is what makes low-resource ASR feasible. IndicWav2Vec [3] applies the same recipe to 40 Indian languages. It shows that pre-training on related Indic languages transfers to Marathi better than pre-training on large but distant corpora. Palivela *et al.* [4] study Hindi–Marathi code-switching and find that multilingual models handle mid-utterance language shifts better than monolingual ones. This finding is why the NagarVani test set contains a separate code-mixed split.`),
  H(2, "2.2  Pre-trained language representations for Indian languages"),
  P(`BERT [5] established the recipe of pre-training once and then fine-tuning with a small head. MuRIL [6] adds transliterated text to pre-training, so that romanised and Devanagari Marathi map to nearby representations. This matters because WhatsApp complaints are often typed in Latin script. IndicNLPSuite [7] releases corpora, the IndicGLUE benchmark and the compact IndicBERT. L3Cube-MahaBERT [8] shows that continued pre-training on a large Marathi corpus beats general multilingual models on Marathi tasks. L3Cube-MahaSTS [9] provides 16,860 human-scored Marathi sentence-similarity pairs and a Marathi Sentence-BERT model with Pearson correlation ≈ 0.96 against human judgements.`),
  H(2, "2.3  Complaint and ticket classification, prioritisation and deduplication"),
  P(`Sentence-BERT [10] embeds sentences independently, so near-duplicate search becomes a vector lookup instead of one cross-encoder pass per pair. Isotani *et al.* [11] detect duplicate industrial bug reports by embedding each field separately and fusing the scores (MAP 0.829 against 0.751 for TF-IDF). They show that domain fine-tuning accounts for most of the gain. Rakhimzhanov *et al.* [12] compare large language models with fine-tuned multilingual embeddings on public-transport complaints and reach about 90% accuracy with the cheaper embeddings. Zicari *et al.* [13] show that single deep ticket classifiers overfit to spurious cues such as channel and boilerplate text, and recommend ensembles combined with explanations.`),
  H(2, "2.4  AI systems in public administration"),
  P(`Cortés-Cediel *et al.* [14] review 52 papers and 25 deployed government chatbots. They find that nearly all of them retrieve information, and very few take part in consequential workflows such as grievance handling. Chen *et al.* [15] find that the factors driving *adoption* of public-sector AI chatbots differ from those driving successful *implementation*: knowledge management, technical skills, resources and the management of citizen expectations. This argues for thin integrations and explicit human-review paths.`),
  H(2, "2.5  Vision-based defect verification"),
  P(`Safyari *et al.* [16] review pothole detection and find that deep and hybrid detectors outperform classical image processing, but that all methods weaken under poor illumination, water-filled defects and occlusion. Visual evidence should therefore be one signal among several when a ticket is closed. That module is deferred in this prototype.`),
  H(2, "2.6  Production systems and expert systems"),
  P(`A production system represents knowledge as condition–action rules over a working memory. An inference engine repeatedly matches rules against the facts and fires them, using a conflict-resolution strategy such as rule salience [20]. Expert systems built this way are transparent: the fired rules *are* the explanation. This property is valuable where a decision affects public safety and must be auditable, and it is why NagarVani assigns severity by rules rather than by a learned model (Section 3.7). Section 5.6 compares the two approaches on the same data.`),
  H(2, "2.7  Comparative summary"),
  TCap("Table 2.1  The eight works most directly used by the design"),
  T(["Ref.", "Method", "Key result", "Use in NagarVani"], [
    ["[1] Whisper", "Weakly supervised enc–dec ASR, 680k h", "Zero-shot robustness to noise and accent", "Planned ASR backend (interface in M2)"],
    ["[3] IndicWav2Vec", "Indic self-supervised pre-training + CTC", "Indic transfer beats distant corpora for Marathi", "Alternative ASR backend; WER/CER protocol"],
    ["[4] Palivela", "Code-switching ASR comparison", "Multilingual models handle mid-utterance switches", "Separate code-mixed test split"],
    ["[6] MuRIL", "Multilingual BERT with transliterated data", "Aligns romanised and native script", "Motivates script-agnostic char n-grams"],
    ["[8] MahaBERT", "Marathi continued pre-training", "Beats multilingual models on Marathi", "Future encoder for M4a"],
    ["[9] MahaSTS", "Marathi STS dataset + SBERT", "r ≈ 0.96 with human judgements", "Future similarity model for M6"],
    ["[11] Isotani", "Field-wise SBERT duplicate detection", "MAP 0.829 vs 0.751 (TF-IDF)", "Field-wise design: location masked out of text similarity"],
    ["[12] Rakhimzhanov", "Embeddings vs LLMs for complaints", "≈90% accuracy at far lower compute", "Supports a compact discriminative classifier"],
  ], [1500, 2500, 2500, 2526]),
  H(2, "2.8  Research gap and how the prototype responds"),
  P(`The survey identified four gaps. The prototype responds to three of them at small scale.`),
  B(`**No Marathi civic-domain resource exists.** The project builds a 2,000-complaint template corpus, a 160-complaint hand-written test set labelled for department, locality and severity, 30 labelled duplicate pairs, and a 59-locality gazetteer. These are small, but they are the first of their kind for this task.`),
  B(`**Classification is evaluated apart from routing.** NagarVani reports *end-to-end* routing correctness (right department *and* right ward office) together with the rate at which it defers, instead of classifier accuracy alone.`),
  B(`**Severity and duplication are treated independently.** In NagarVani the size of a duplicate cluster is an input to the severity rules (rule R32).`),
  B(`**Closure verification is unmodelled.** This gap is not addressed in the prototype and is carried to future work.`),
  Brk(),
];

// ---------------------------------------------------------------- chapter 3
const ruleRows = [
  ["R01", "100", "Injury, bite or accident has occurred", "P1"],
  ["R02", "100", "DRAIN and manhole/chamber cover missing, broken or open", "P1"],
  ["R03", "100", "ELEC and (live current, or dangling wire, or open DP box)", "P1"],
  ["R04", "100", "ELEC/TREE/BUILD/ENCROACH and collapse imminent or occurred", "P1"],
  ["R05", "100", "TREE and (fallen tree blocking road, or branch dangling)", "P1"],
  ["R06", "100", "Disease outbreak / people fallen ill", "P1"],
  ["R07", "100", "DRAIN and sewage entering a dwelling", "P1"],
  ["R08", "100", "VET and rabid animal", "P1"],
  ["R10", "50", "Explicit risk of accident or damage", "≤ P2"],
  ["R11", "50", "Public-health nuisance (smell, burning, carcass, contamination, sewage on road)", "≤ P2"],
  ["R12", "50", "WATER and supply outage ≥ 2 days", "≤ P2"],
  ["R13", "50", "SWM and garbage uncollected ≥ 3 days", "≤ P2"],
  ["R14", "50", "WATER and pipeline burst / major wastage", "≤ P2"],
  ["R15", "50", "DRAIN and drain blocked / overflowing", "≤ P2"],
  ["R16", "50", "TREE and property damaged", "≤ P2"],
  ["R20", "10", "Service request or cosmetic issue, and no hazard rule fired", "P4"],
  ["R30", "0", "Near a school or hospital", "escalate 1"],
  ["R31", "0", "Problem persists ≥ 14 days", "escalate 1"],
  ["R32", "0", "≥ 3 citizens reported the same defect (duplicate cluster)", "escalate 1"],
];
const ch3 = [
  H(1, "Chapter 3  Methodology"),
  H(2, "3.1  Design principles"),
  B(`**Augment, do not replace.** PMC CARE remains the system of record. NagarVani produces well-formed recommendations and changes no municipal workflow.`),
  B(`**Abstention is an output, not a failure.** Below a confidence threshold, or when the location cannot be resolved, the ticket goes to a human with the top three candidates filled in. No complaint is ever dropped.`),
  B(`**Rules decide where safety is at stake.** Severity is assigned by explicit production rules, and life-safety rules override everything else. A model trained mostly on routine complaints cannot be trusted at the dangerous tail of the distribution.`),
  B(`**Every decision is explainable.** Each ticket stores its top-three departments with probabilities, the matched locality, the fired rules and the duplicate evidence.`),
  H(2, "3.2  Architecture and implementation status"),
  ...Fig("fig_architecture.png", 6.2, "Fig. 3.1  Implemented NagarVani data flow. The dashed ASR box is an interface whose backend was not run (Section 4.7)."),
  P(`Fig. 3.1 shows the implemented pipeline. A complaint is normalised (M3). It is then classified to a department (M4a) and resolved to a ward office (M4b) independently. The duplicate detector (M6) searches open tickets in the same (ward, department) block, and the resulting cluster size feeds the severity expert system (M5). The abstention gate (M7) then decides whether the ticket is auto-routed to a ward queue or deferred to the nodal officer. Table 3.1 maps this pipeline to the twelve-module design in PBL-3.`),
  TCap("Table 3.1  PBL-3 modules and their status in this prototype"),
  T(["Module", "PBL-3 plan", "Prototype status"], [
    ["M1 Ingestion", "WhatsApp, IVR and web adapters", "Partial: web console and text channel tag"],
    ["M2 ASR", "Fine-tuned Whisper / IndicWav2Vec", "Interface + Whisper wrapper; not run (weights unavailable). Replaced in evaluation by a CER noise simulator"],
    ["M3 Normalisation", "Unicode, transliteration, lexicon repair", "Implemented (Unicode, digits, case, zero-width, repeats); no transliteration"],
    ["M4a Classifier", "Fine-tuned Marathi transformer ensemble", "Implemented as TF-IDF + logistic regression; four baselines"],
    ["M4b Location", "NER + gazetteer + GPS prior", "Implemented: gazetteer exact + fuzzy; no NER, no GPS"],
    ["M5 Severity", "Gradient-boosted ordinal model + rule override", "Implemented as a 19-rule expert system; learned model used as a baseline"],
    ["M6 Deduplication", "SBERT + HNSW + geo-blocking", "Implemented: (ward, dept) blocking + masked char n-gram cosine, two thresholds"],
    ["M7 Routing / SLA", "Routing table + calibrated gate", "Implemented: confidence + location gate, SLA deadlines"],
    ["M8 Clarification", "One Marathi TTS question", "Not implemented (deferred cases go to a human)"],
    ["M9 Closure verification", "Photo + geotag + citizen confirmation", "Not implemented"],
    ["M10 PMC CARE adapter", "Four-operation adapter", "Out of scope: no public API; SQLite + CSV export instead"],
    ["M11 Dashboard", "Ward pendency, hotspots, SLA", "Partial: ward-queue view in console"],
    ["M12 Continual learning", "Active learning, fairness gate", "Not implemented"],
  ], [1900, 3000, 4126]),
  H(2, "3.3  Data"),
  H(3, "3.3.1  Label spaces"),
  P(`PMC has roughly 43 departments. The prototype uses the ten that handle the large majority of everyday civic complaints (Table 3.2). The location label space is the 15 PMC ward offices. Priority has four bands with service-level deadlines of 24 hours, 72 hours, 7 days and 15 days.`),
  TCap("Table 3.2  Department label space"),
  T(["Code", "Department", "Typical complaints"], [
    ["ROAD", "Road Department", "Potholes, dug-up roads, damaged footpaths, speed breakers"],
    ["SWM", "Solid Waste Management", "Uncollected garbage, overflowing bins, burning, public toilets"],
    ["WATER", "Water Supply", "No water, low pressure, contamination, pipeline bursts, billing"],
    ["DRAIN", "Drainage", "Blocked sewers, open manholes, sewage on road or in homes"],
    ["ELEC", "Electrical (Street Lighting)", "Streetlights off, dangling wires, leaning poles, DP boxes"],
    ["HEALTH", "Health (Vector Control & Sanitation)", "Mosquitoes, fogging, dengue/malaria cases, carcasses"],
    ["TREE", "Garden / Tree Authority", "Fallen trees and branches, trimming, illegal felling"],
    ["ENCROACH", "Anti-Encroachment", "Hawkers on footpaths, illegal stalls, banners, hoardings"],
    ["BUILD", "Building Permission & Construction", "Unauthorised floors, dangerous buildings, debris"],
    ["VET", "Veterinary (Stray Animals)", "Stray dogs, bites, stray cattle, pigs, monkeys"],
  ], [1300, 3100, 4626]),
  H(3, "3.3.2  Training corpus (template-generated)"),
  P(`No public Marathi civic-complaint corpus exists, so the team built one. For each department and each of four input varieties (Marathi Devanagari, Hindi, romanised Marathi, code-mixed), the team wrote banks of issue phrases, and tagged each phrase with its semantic properties (injury, hazard, risk, outbreak, sewage-in-home, nuisance, outage, wastage, request). A generator combines an issue phrase with optional greetings, a locality drawn from the gazetteer, a school or hospital mention, a duration, and a closing request. It produces ${DATA.n_train.toLocaleString("en-IN")} unique complaints: ${DATA.train_lang.mr} Marathi, ${DATA.train_lang.hi} Hindi, ${DATA.train_lang["mr-rom"]} romanised and ${DATA.train_lang.mix} code-mixed. Each complaint's severity label is computed from the tags of the phrases it was built from, following the guideline below, and never from keyword matching on the final string.`),
  H(3, "3.3.3  Hand-written test set"),
  P(`The test set was written separately and by hand, and the generator does not produce it. It contains 160 complaints, 16 per department: ${DATA.test_lang.mr} Marathi, ${DATA.test_lang.hi} Hindi, ${DATA.test_lang["mr-rom"]} romanised and ${DATA.test_lang.mix} code-mixed. The complaints were written in a deliberately spontaneous register, with inflected localities (*धायरीत*, *कोंढव्यात*), abbreviations, mid-sentence switches between Marathi and English, and cases that are hard by design: a locality outside the gazetteer (*एरंडवणे*, *लक्ष्मी रोड*), a negated duration ("*महिना झाला नाही*"), and an injured animal rather than an injured person. Each complaint is labelled with its department, its locality key (or NONE; ${DATA.test_loc_none} complaints have none), and its severity band. The severity distribution is P1 ${DATA.test_sev.P1}, P2 ${DATA.test_sev.P2}, P3 ${DATA.test_sev.P3} and P4 ${DATA.test_sev.P4}.`),
  H(3, "3.3.4  Severity annotation guideline"),
  P(`**P1** is assigned when an injury, bite or accident has happened, or when there is an immediate threat to life: an open manhole, a live or dangling wire, a structure, tree, pole or hoarding that has collapsed or "can fall any time", a rabid animal, a disease outbreak, or sewage entering a home. **P2** covers an explicit risk without an event, public-health nuisances, a water outage of at least 2 days, garbage uncollected for at least 3 days, and pipeline bursts. **P3** is the default for a functional defect. **P4** covers service requests and cosmetic issues. After the band is set, it rises by one level when the site is near a school or hospital, when the problem has persisted for 14 days or more, or when three or more citizens have reported it.`),
  H(3, "3.3.5  Gazetteer and duplicate pairs"),
  P(`The gazetteer maps 59 Pune localities to the 15 ward offices. It stores Devanagari, Hindi and romanised aliases, and Marathi oblique stems such as *कोंढव्या* and *मुंढव्या*. The bare name *वडगाव* is listed as ambiguous, because it can refer to Vadgaon Budruk (Sinhagad Road) or Wadgaon Sheri (Nagar Road). The mapping was built from public locality names and is approximate, not an official boundary file. For deduplication, 30 pairs were written: 15 true duplicates (a paraphrase of a test complaint), 10 pairs from the same ward but different departments, and 5 hard negatives from the same ward and the same department that describe a different defect.`),
  H(2, "3.4  Text normalisation (M3)"),
  P(`Every downstream module receives the same canonical form. The text is composed to Unicode NFC, which merges decomposed vowel signs and nukta variants. Zero-width joiners and byte-order marks inserted by mobile keyboards are removed. Devanagari digits are mapped to ASCII, Latin text is lower-cased, runs of three or more identical characters are collapsed, and punctuation other than commas, hyphens and full stops is stripped.`),
  H(2, "3.5  Department classification (M4a)"),
  P(`The proposed classifier concatenates two TF-IDF representations: character n-grams of length 2–5 within word boundaries, and word unigrams and bigrams. Both use sublinear term frequency, and they feed a multinomial logistic-regression model with class-balanced weights. Character n-grams are chosen because Marathi attaches case markers and postpositions to the noun (*रस्त्यावर*, *खड्ड्यात*). They also let the same model read Devanagari and Latin input, since romanised forms such as *khadda* share sub-strings across spellings. Logistic regression outputs class probabilities, which the abstention gate needs. The regularisation constant C = 10 was chosen by 5-fold cross-validation on the training set only (macro-F1: C = 0.3 → ${f3(R.E1_C_search["0.3"])}, C = 10 → ${f3(R.E1_C_search["10"])}). Four baselines are compared: a hand-built keyword lexicon with no learning, word TF-IDF with multinomial Naive Bayes, word TF-IDF with logistic regression, and character n-grams alone with logistic regression.`),
  H(2, "3.6  Ward resolution (M4b)"),
  P(`The resolver matches gazetteer aliases against the normalised text, longest first, and masks each match so that *वडगाव शेरी* is not also counted as the ambiguous *वडगाव*. Devanagari aliases match as sub-strings, which tolerates attached suffixes (*कोथरूड*मध्ये). Latin aliases match only as whole words. When exactly one ward is hit, the complaint is *resolved*. Hits in two wards make it *ambiguous*, and no hits make it *unresolved*. Neither of those cases is guessed; both are sent to review. If exact matching finds nothing, a fuzzy fallback compares each alias of four or more characters with every token window of the same length, using the difflib similarity ratio, and accepts the best match at a ratio of 0.80 or higher. The fallback exists for transcription errors (Section 5.7).`),
  H(2, "3.7  Severity expert system (M5)"),
  P(`Severity is assigned by a forward-chaining production system with four parts [20].`),
  B(`**Knowledge base.** A fact-extraction lexicon of 23 cue groups (226 cue strings in Marathi, Hindi, romanised and English) and 19 production rules (Table 3.3).`),
  B(`**Working memory.** Boolean facts found in the complaint, the predicted department, the longest stated duration in days (parsed from number words and units in all three scripts), and the duplicate-cluster size.`),
  B(`**Inference engine.** Rules are matched in descending salience. The default band is P3. A *set* rule lowers the band number to its target when that is more severe. The *relax* rule (R20) moves a complaint to P4 only if no hazard rule has fired. *Escalate* rules then raise the band by one level each, never beyond P1.`),
  B(`**Explanation facility.** The IDs and English text of the fired rules are stored with the ticket and shown to the officer.`),
  TCap("Table 3.3  Rule base (salience in descending order)"),
  T(["Rule", "Sal.", "Condition", "Action"], ruleRows, [800, 700, 6026, 1500], { size: 18 }),
  H(3, "Algorithm 1 — Severity inference"),
  ...Code([
    "Input : complaint text x, department d, cluster size c",
    "Output: band b in {P1..P4}, fired rule list F",
    "1  W <- ExtractFacts(x) U {DEPT=d, DAYS=ParseDuration(x), CLUSTER=c}",
    "2  b <- 3 ; F <- [] ; hazard <- false",
    "3  for r in RULES sorted by salience (descending):",
    "4      if not r.cond(W): continue",
    "5      if r.kind = SET:      b <- min(b, r.band); hazard <- true; F.append(r)",
    "6      if r.kind = RELAX and not hazard: b <- 4; F.append(r)",
    "7      if r.kind = ESCALATE: b <- max(1, b-1); F.append(r)",
    "8  return P{b}, F",
  ]),
  H(2, "3.8  Duplicate detection (M6)"),
  P(`Comparing a new complaint against every open ticket is unnecessary. Candidates are first *blocked* to open tickets with the same predicted department and the same resolved ward office. Within the block, similarity is the cosine between character-2–4-gram TF-IDF vectors after every gazetteer alias has been removed from both texts. This field-wise masking follows [11]: two different problems in Kothrud should not look alike merely because both mention Kothrud. The decision uses two thresholds set before evaluation. A similarity of θ_high = 0.45 or more merges the complaint into the existing cluster. A similarity between θ_low = 0.30 and θ_high flags it for a one-tap officer decision. Anything lower opens a new cluster.`),
  H(2, "3.9  Abstention gate and routing (M7)"),
  P(`A ticket is **auto-routed** to its ward-office queue only if the classifier's top probability is at least τ and the location status is *resolved*. Otherwise it is held in the **nodal-review queue**, with the reason recorded and the top three departments filled in. The prototype uses τ = 0.50. Chapter 5 reports the full coverage–accuracy curve, from which a municipality could choose τ according to its reviewers' capacity.`),
  H(3, "Algorithm 2 — End-to-end triage"),
  ...Code([
    "1  u <- Normalise(x)",
    "2  (d, p, top3) <- Classifier(u)",
    "3  (loc, ward, status) <- ResolveWard(u)            # exact, then fuzzy",
    "4  if status = resolved:",
    "5      (decision, parent, s) <- Dedup(u, d, ward, OpenTickets(ward, d))",
    "6      c <- ClusterSize(parent) + 1 if decision = merge else 1",
    "7  (band, F) <- SeverityInfer(u, d, c) ; due <- now + SLA[band]",
    "8  route <- AUTO_ROUTED if p >= tau and status = resolved else NODAL_REVIEW",
    "9  Store(ticket) ; append to queue_<ward>.csv or queue_nodal_review.csv",
  ]),
  H(2, "3.10  Evaluation protocol"),
  P(`All models are trained on the template corpus and evaluated once on the hand-written test set. The template corpus is never used to report test performance. The metrics are: accuracy, macro-F1 and top-3 accuracy for departments, with results broken down by input variety; expected calibration error (ECE, 10 bins) [21] and the coverage–accuracy curve for the gate; ward-resolution accuracy, counting a correct "unresolved" as success when the complaint names no known locality; band accuracy, mean absolute band error, and P1 precision and recall for severity; precision and recall for duplicate pairs; degradation under simulated transcription error at character error rates of 5–30% (5 random seeds each); and, end to end, the share of tickets auto-routed and the share of those with the correct department *and* ward.`),
  Brk(),
];

// ---------------------------------------------------------------- chapter 4
const trace = JSON.parse(fs.readFileSync(__dirname + "/../results/demo_trace.json", "utf8"));
const grab = (card, key) => { const m = card.split("\n"); const i = m.indexOf(key); return i >= 0 ? m[i + 1] : ""; };
const demoRows = trace.map(t => {
  const c = t.card;
  const dept = (grab(c, "Department").match(/\(([A-Z]+)\)/) || [])[1] || "";
  const conf = (grab(c, "Department").match(/confidence ([0-9.]+)/) || [])[1] || "";
  const ward = grab(c, "Locality → ward office").replace(/^.*→ /, "");
  const pr = (grab(c, "Priority").match(/P[1-4]/) || [""])[0];
  const dup = grab(c, "Duplicate check").replace(/\(best similarity ([0-9.]+)\), cluster size (\d+)/, "($1), n=$2");
  const route = c.includes("Auto-routed") ? "Auto" : "Review";
  return [String(t.step), t.text, `${dept} ${conf}`, ward, pr, dup, route];
});
const ch4 = [
  H(1, "Chapter 4  Implementation"),
  H(2, "4.1  Environment and technology stack"),
  P(`The prototype is written in Python 3.11 and uses scikit-learn 1.8 [19] for all learned components, NumPy 2.4, Matplotlib 3.10 for figures, SQLite (Python standard library) for storage, and Flask 3.1 for the officer console. Playwright with headless Chromium drives the console for the scripted demonstration. The whole pipeline runs on a 2-vCPU, 7 GB machine with no GPU. Training the proposed classifier takes under ${Math.ceil(PROP.fit_seconds)} s, and the full evaluation, including cross-validation and 30 noise runs, takes under a minute. The code base is about 1,300 lines.`),
  H(2, "4.2  Code organisation"),
  TCap("Table 4.1  Source layout"),
  T(["Path", "Responsibility"], [
    ["nagarvani/normalise.py", "M3 canonical text form; script profiling"],
    ["nagarvani/classifier.py", "M4a proposed classifier, three learned baselines, keyword baseline, department names"],
    ["nagarvani/location.py", "M4b WardResolver: longest-first exact matching, ambiguity handling, fuzzy fallback"],
    ["nagarvani/severity.py", "M5 cue lexicon, duration parser, Rule dataclass, 19-rule base, inference engine, explanations"],
    ["nagarvani/dedup.py", "M6 DuplicateDetector: blocking, location masking, two-threshold decision"],
    ["nagarvani/asr.py", "M2 ASRBackend interface, WhisperBackend wrapper, transcription-noise simulator"],
    ["nagarvani/store.py", "SQLite schema, ticket store, per-ward CSV export"],
    ["nagarvani/pipeline.py", "Triage class: the end-to-end Algorithm 2"],
    ["app/app.py, app/templates/", "Flask console: triage form, ticket card, ward queues, export endpoint"],
    ["corpus/", "Template generator, 2,000-row training set, 160-row test set, 30 duplicate pairs"],
    ["data/gazetteer.json", "15 ward offices, 59 localities, aliases, ambiguous names"],
    ["experiments/", "run_eval.py (all metrics and figures), demo_scenario.py, make_architecture.py"],
  ], [3000, 6026]),
  H(2, "4.3  Key implementation details"),
  H(3, "4.3.1  Classifier pipeline"),
  P(`The proposed model is a single scikit-learn Pipeline, so normalisation, feature extraction and classification are serialised together (\`results/model.pkl\`), and exactly the same preprocessing is applied during training and when serving:`),
  ...Code([
    "FeatureUnion([",
    "  ('char', TfidfVectorizer(analyzer='char_wb',",
    "            ngram_range=(2,5), sublinear_tf=True,",
    "            min_df=2, preprocessor=normalise)),",
    "  ('word', TfidfVectorizer(analyzer='word',",
    "            ngram_range=(1,2), sublinear_tf=True,",
    "            token_pattern=r'(?u)[^\\s,.\\-]+',",
    "            preprocessor=normalise))])",
    "-> LogisticRegression(C=10, class_weight='balanced',",
    "                      max_iter=4000)",
  ]),
  P(`The custom token pattern matters. The default scikit-learn pattern \`\\b\\w\\w+\\b\` splits Devanagari words at dependent vowel signs, because Python does not treat those combining marks as word characters, and this produces meaningless fragments.`),
  H(3, "4.3.2  Rules as data"),
  P(`Each rule is a \`Rule(rid, text, cond, kind, band, salience)\` object, and its condition is a small predicate over the working-memory dictionary, for example:`),
  ...Code([
    "Rule('R02',",
    "     'IF dept=DRAIN AND cover missing/broken/open THEN P1',",
    "     lambda f: f['DEPT'] == 'DRAIN' and f['COVER'] and f['OPEN'],",
    "     'set', 1, 100)",
  ]),
  P(`Because rules are data, the engine can be switched between configurations (for example with escalation turned off for the ablation in Section 5.6) without changing its code, and the explanation shown to the officer is exactly the text of each fired rule.`),
  H(3, "4.3.3  Duration parsing"),
  P(`Durations are parsed with a regular expression over number words in Marathi (*दोन*, *पंधरा*), Hindi (*दो*, *पांच*) and romanised Marathi, or over digits, followed by a unit stem for day (*दिवस/दिन/divas/day*), week (*आठवड/हफ्त/week*) or month (*महिन/महीन/month*). Fixed expressions are also recognised: *आठवडाभर* (7 days), *महिनोन् महिने* (60 days) and *कई दिनों* (3 days). The parser deliberately does not handle negation, and Section 5.6 shows one error that results.`),
  H(2, "4.4  Data store"),
  P(`Each ticket row stores the raw text, the normalised text, the department and its confidence, the top-three candidates as JSON, the locality, the ward, the ward-resolution status, the priority, the SLA deadline, the fired rules, the cluster id, the duplicate decision and score, the route status (AUTO_ROUTED or NODAL_REVIEW) and a lifecycle status. The export writes one UTF-8 CSV per ward office, sorted by priority and then deadline, plus \`queue_nodal_review.csv\`. It uses a byte-order mark so that Excel displays Devanagari correctly. When the 160 test complaints are run as a stream, the export produces 15 ward files and one review file.`),
  H(2, "4.5  Officer console"),
  P(`The Flask console has two views. The *triage* view accepts a complaint and shows the resulting ticket card (Fig. 4.1). The *ward-queues* view lists every ticket grouped by ward office, with deferred tickets in a separate nodal-review group, each group sorted by priority and deadline (Fig. 4.3).`),
  ...Fig("screen_step4.png", 5.6, "Fig. 4.1  Ticket card for the third report of the same Kothrud pothole: merged into the existing cluster (similarity 0.80, cluster size 3), and escalated from P3 to P2 by rule R32."),
  ...Fig("screen_step5.png", 5.6, "Fig. 4.2  An ambiguous location (वडगाव) is not guessed: the ticket is held for nodal review even though the department confidence is 0.94."),
  ...Fig("screen_queues.png", 5.6, "Fig. 4.3  Ward-queue view after the seven-step demonstration."),
  H(2, "4.6  Worked demonstration"),
  P(`Table 4.2 traces a scripted scenario of seven complaints entered through the console. It exercises every branch of the pipeline: a duplicate merge, recurrence escalation, a life-safety override, an ambiguous location, a missing location and a code-mixed complaint.`),
  TCap("Table 4.2  Demonstration trace (output of experiments/demo_scenario.py)"),
  T(["#", "Complaint", "Dept, conf.", "Ward office", "Pri.", "Duplicate (sim), cluster", "Route"], demoRows,
    [350, 3000, 1150, 1500, 550, 1700, 776], { size: 16 }),
  P(`Steps 1, 2 and 4 describe the same pothole. Step 2 merges into cluster 1 (similarity 0.64). Step 4 merges at 0.80, which makes the cluster size 3, so rule R32 escalates it from P3 to P2. This is the recurrence-as-evidence mechanism that the survey identified as missing from the literature. Step 3 fires the open-manhole rule R02 and receives a 24-hour deadline. Steps 5 and 6 have high department confidence but no usable location, so both are deferred and the reason is recorded.`),
  H(2, "4.7  What was not implemented, and why"),
  B(`**Speech recognition was not run.** The build environment's network policy blocked the model hubs that host Whisper and IndicWav2Vec checkpoints, so no Marathi acoustic model could be loaded. The ASR interface and a Whisper wrapper are in the code base (\`nagarvani/asr.py\`). The effect of transcription errors on everything downstream is measured with a character-level noise simulator (Section 5.7). The simulator is uniform and random, whereas real ASR errors are phonetically structured, so it only approximates them.`),
  B(`**No PMC CARE integration.** PMC CARE has no public API, and the scope boundary in Section 1.4 applies.`),
  B(`**No transformer encoder.** MahaBERT, MuRIL and MahaSBERT, which PBL-3 planned for M4a and M6, are hosted on the same blocked model hub. The TF-IDF models are a deliberate, lighter substitute, and Chapter 5 shows how far they get.`),
  B(`**Clarification dialogue, closure verification and continual learning** (M8, M9, M12) are not implemented and remain future work.`),
  Brk(),
];

// ---------------------------------------------------------------- chapter 5
const mRows = Object.entries(E1).map(([n, v]) => [n.replace(" (proposed)", " **(proposed)**"), pct(v.acc), f3(v.macro_f1), pct(v.top3),
  pct(v.by_lang.mr, 0), pct(v.by_lang.hi, 0), pct(v.by_lang["mr-rom"], 0), pct(v.by_lang.mix, 0)]);
const pc = R.E2_per_class;
const pcRows = Object.keys(pc).map(k => [k, f2(pc[k].p), f2(pc[k].r), f2(pc[k].f1)]);
const sevRows = [["Always P3 (majority)", "majority_P3"], ["Learned: char TF-IDF + LogReg", "learned_logreg"],
  ["Rules, escalation off (gold dept)", "rules_no_escalation"], ["Rules (predicted dept)", "rules_pred_dept"],
  ["Rules (gold dept)", "rules_gold_dept"]].map(([n, k]) => { const v = E5[k];
  return [n, pct(v.acc), f3(v.mae), f3(v.macro_f1), pct(v.p1_recall), isNaN(v.p1_precision) || v.p1_precision === null ? "—" : pct(v.p1_precision), pct(v.under_triage)]; });
const cm = R.E5_confusion_rules;
const ch5 = [
  H(1, "Chapter 5  Results and Discussions"),
  H(2, "5.1  Experimental setup"),
  P(`Every number in this chapter is produced by \`experiments/run_eval.py\` and stored in \`results/results.json\`. Models are trained on the ${DATA.n_train.toLocaleString("en-IN")}-complaint template corpus and evaluated once on the 160-complaint hand-written test set. The random seed of the template generator and all noise seeds are fixed.`),
  H(2, "5.2  Department classification"),
  TCap("Table 5.1  Department classification on the hand-written test set (n = 160); accuracy by input variety on the right"),
  T(["Model", "Acc.", "Macro-F1", "Top-3", "mr (80)", "hi (20)", "rom (30)", "mix (30)"], mRows, [2826, 800, 900, 800, 900, 900, 950, 950], { size: 18, highlightRow: 4 }),
  ...Fig("fig_models.png", 5.8, "Fig. 5.1  Accuracy and macro-F1 of the five department classifiers."),
  P(`The proposed character-plus-word model reaches ${pct(PROP.acc)} accuracy and ${f3(PROP.macro_f1)} macro-F1. That is ${((PROP.acc - KW.acc) * 100).toFixed(1)} points above the keyword lexicon, and its top-3 accuracy is ${pct(PROP.top3)}, which means that the correct department appears in the nodal officer's shortlist for almost every complaint. The word-level models are no better than the keyword lexicon. They fail most on romanised Marathi (${pct(E1["Word TF-IDF + LogReg"].by_lang["mr-rom"], 0)}), where each spelling variant is a separate word type. Character n-grams are the single largest improvement.`),
  P(`**A result against our own choice.** The character-only model scored *higher* on the test set (${pct(CHAR.acc)}, macro-F1 ${f3(CHAR.macro_f1)}) than the proposed character-plus-word model. The proposed configuration was fixed before the test set was used, and both models reach 99.8% under cross-validation on the training data, so the training data could not separate them. The difference is ${Math.round((CHAR.acc - PROP.acc) * 160)} complaints out of 160, which is within the variation expected at this sample size. We report it rather than switching models after seeing test results. A larger development set is needed to settle the choice.`),
  P(`**The template gap.** Under 5-fold cross-validation *within* the template corpus, the proposed model reaches ${pct(R.E1_cv_template.acc)} accuracy. On hand-written text it reaches ${pct(PROP.acc)}. The difference of about 13 points measures how much easier generated text is than human writing, and it is why the test set was written separately. Any evaluation that reports results on template data alone would be misleading.`),
  H(3, "5.2.1  Per-department results and error analysis"),
  TCap("Table 5.2  Per-department precision, recall and F1 (proposed model)"),
  T(["Dept", "Precision", "Recall", "F1"], pcRows, [2000, 2000, 2000, 2000], { size: 20 }),
  ...Fig("fig_confusion.png", 4.3, "Fig. 5.2  Confusion matrix of the proposed classifier on the test set."),
  P(`The ${nErr} errors fall into three recognisable groups.`),
  B(`**Genuinely overlapping departments.** Examples: "गटाराचा प्रचंड वास येतो आणि डास झालेत" (drain smell and mosquitoes, DRAIN → SWM); "बांधकामाच्या ठिकाणी पाणी साचलंय, डासांची पैदास होतेय" (HEALTH → DRAIN); "झाडाची फांदी विजेच्या तारांवर लोंबकळतेय" (a branch on power lines, TREE → ELEC). Two departments can legitimately claim each of these, and a human would often need both.`),
  B(`**Vocabulary absent from training.** Examples: *निर्माल्य* (festival offerings, SWM), *गच्चीवर मोबाईल टॉवर* (a rooftop tower, BUILD), *गॅरेज … ऑइल* (a roadside garage, ENCROACH), *रोपं* (saplings, TREE). The template banks do not contain these words, and the model has nothing to match them against.`),
  B(`**Dominant object nouns.** "मेलेलं कुत्रं" (a dead dog) is sent to VET because *कुत्र* (dog) is a strong VET feature, although carcass disposal belongs to HEALTH. "इमारतीत … डेंग्यू" (dengue in a building) goes to BUILD because of *इमारत* (building).`),
  P(`None of these is a random failure. Each points to a specific fix: add the missing terms to the phrase banks, write explicit tie-break rules for the shared departments, or, for the overlapping cases, route the complaint jointly to both departments.`),
  H(2, "5.3  Calibration and the abstention gate"),
  ...Fig("fig_abstention.png", 5.0, "Fig. 5.3  Coverage (share of complaints auto-routed on department confidence) and accuracy among the auto-routed complaints, as τ varies."),
  P(`The classifier's confidence is informative. The mean top-class probability is ${f3(E3.mean_conf_correct)} on correct predictions and ${f3(E3.mean_conf_wrong)} on wrong ones. ECE is ${f3(E3.ece)}. The model is under-confident on average: its mean confidence is ${f3(E3.mean_conf)}, while its accuracy is ${pct(PROP.acc)}. At τ = 0.50, ${pct(tau50.coverage)} of complaints pass the department gate, and ${pct(tau50.acc_auto)} of those are correct, so the misrouting rate among confident cases falls from ${pct(1 - PROP.acc)} to ${pct(tau50.misroute_rate_auto)}. Raising τ to 0.90 gives 100% accuracy on the ${pct(R.E3_abstention_curve.find(c => c.tau === 0.9).coverage, 0)} of complaints that remain. The curve lets a ward office choose its own operating point according to how many deferred cases its reviewers can handle.`),
  H(2, "5.4  Ward resolution"),
  P(`On clean text, the exact matcher resolves all ${E4.n_with_locality} complaints that name a gazetteer locality to the correct ward office. It leaves all ${E4.n_without} complaints without a known locality unresolved, including the out-of-gazetteer *एरंडवणे* and *लक्ष्मी रोड* and the ambiguous *वडगाव*. With the fuzzy fallback switched on, one of those ${E4.n_without} is falsely resolved: *बाहेर* ("outside") matches the alias *बाणेर* at a ratio of 0.80. On clean text, then, the fallback costs one false resolution in 160. Section 5.7 shows what it gains when the text is noisy.`),
  P(`These clean-text figures should be read as a check that the gazetteer covers the test set, not as a measure of general performance. The gazetteer and the test set were written by the same team, and every locality in the test set was deliberately taken from the gazetteer or deliberately left out of it. On real complaints, localities missing from the gazetteer would be the main cause of deferral.`),
  H(2, "5.5  Duplicate detection"),
  ...Fig("fig_dedup.png", 5.0, "Fig. 5.4  Location-masked similarity for the 30 labelled pairs, grouped by pair type."),
  P(`Blocking on (ward, department) removes all ten cross-department negatives before any text is compared. Masking locations keeps the five same-ward, same-department negatives (for example, two different Kothrud road complaints) at a similarity of ${f2(Math.max(...E6.pairs.filter(p => p.kind === "same-ward-same-dept").map(p => p.sim)))} or less. At θ_high = 0.45, automatic merges have precision ${f2(E6.merge_block.precision)} and recall ${f2(E6.merge_block.recall)} (${E6.merge_block.tp} of 15). Counting the review band down to θ_low = 0.30, ${E6.review_block.tp} of the 15 true duplicates either merge or reach the officer. The one duplicate that is missed (D06) is lost at the blocking stage: the classifier assigned its first complaint to BUILD instead of HEALTH, so the two complaints never met. With only 30 pairs, all written by the team, precision of 1.00 means only that no false merge occurred on this set. It says little about the true rate.`),
  H(2, "5.6  Severity: expert system vs. learned model"),
  TCap("Table 5.3  Severity on the test set (n = 160)"),
  T(["Method", "Band acc.", "MAE (bands)", "Macro-F1", "P1 recall", "P1 precision", "Under-triage"], sevRows,
    [2826, 1000, 1000, 1000, 1000, 1100, 1100], { size: 18 }),
  ...Fig("fig_severity.png", 5.8, "Fig. 5.5  Band accuracy and P1 recall for severity methods."),
  P(`With the true department, the rule base assigns the correct band to ${pct(E5.rules_gold_dept.acc)} of complaints and recalls every P1 case. With the predicted department it assigns ${pct(E5.rules_pred_dept.acc)} correctly and recalls ${pct(E5.rules_pred_dept.p1_recall)} of P1 cases, because a department error can stop a department-specific life-safety rule from firing. A logistic-regression model trained on the same guideline labels, taken from the template corpus, reaches only ${pct(E5.learned_logreg.acc)} and misses ${pct(1 - E5.learned_logreg.p1_recall, 0)} of P1 cases. Turning off the three escalation rules lowers band accuracy to ${pct(E5.rules_no_escalation.acc)} and raises under-triage from ${pct(E5.rules_gold_dept.under_triage)} to ${pct(E5.rules_no_escalation.under_triage)}.`),
  P(`**This comparison favours the rules, and the reason must be stated.** The same team wrote the annotation guideline, the rule base and the test-set labels, and the cue lexicon was refined while the team was familiar with the test phrasing. The ${pct(E5.rules_gold_dept.acc)} figure therefore measures how completely the lexicon covers the guideline on text the authors know. It is an optimistic estimate and does not show that the guideline is correct. A fairer figure comes from applying the rules to the 2,000 template complaints, whose labels come from phrase tags and not from the lexicon: the rules reach ${pct(E5.rules_on_template_set_gold_dept.acc)} accuracy and ${pct(E5.rules_on_template_set_gold_dept.p1_recall)} P1 recall there. The lasting argument for rules is not a higher score. A rule can be read, audited, and changed by a municipal officer in one line, and a life-safety rule fires whenever its cues are present, however rare that case was in the training data.`),
  P(`The four remaining rule errors on the test set are all informative. *"महिना झाला नाही"* ("not even a month") is parsed as 30 days and wrongly escalated, because the parser does not handle negation. *"आठवडाभर पाणी नव्हतं"* refers to a past summer outage but fires R12. *"जखमी कुत्रं"* (an injured dog) fires the injury rule meant for people. *"terrace var illegal shed"* is a cosmetic P4 case with no cue in the lexicon. The confusion matrix of the rules has rows P1–P4 of [${cm.map(r => r.join(", ")).join("], [")}]: all errors are off by one band, and none moves a P1 complaint downward.`),
  H(2, "5.7  Robustness to transcription errors"),
  TCap("Table 5.4  Degradation under simulated character error rate (mean of 5 seeds; predicted department)"),
  T(["CER", "Dept macro-F1", "Ward (exact)", "Ward (exact + fuzzy)", "Severity band acc."],
    E7.map(e => [pct(e.cer, 0), f3(e.dept_macro_f1) + (e.cer ? " ± " + f3(e.dept_macro_f1_sd) : ""), pct(e.ward_acc_exact), pct(e.ward_acc), pct(e.sev_acc)]),
    [1200, 2200, 1800, 2000, 1826], { size: 20 }),
  ...Fig("fig_asr_noise.png", 5.0, "Fig. 5.6  Effect of simulated transcription errors on each stage."),
  P(`The classifier degrades gradually. Its macro-F1 is ${f3(cer10.dept_macro_f1)} at 10% CER and ${f3(cer20.dept_macro_f1)} at 20%, because character n-grams still find intact sub-strings in damaged words. Exact gazetteer matching is brittle: a single wrong character in a locality name defeats it, and exact-only ward accuracy falls to ${pct(cer10.ward_acc_exact, 0)} at 10% CER. The fuzzy fallback recovers most of this loss (${pct(cer10.ward_acc, 0)} at 10% and ${pct(cer20.ward_acc, 0)} at 20%). Severity is the most fragile stage (${pct(cer20.sev_acc, 0)} at 20%), because a rule fires only when its cue string is intact. Fuzzy cue matching is therefore the next change to make before speech input is connected. Where a real system falls on this curve depends on the character error rate that fine-tuned Marathi ASR [3], [4] achieves on civic speech, which has not been measured yet.`),
  H(2, "5.8  End-to-end routing"),
  P(`When the 160 test complaints are run through the full pipeline in sequence at τ = 0.50, ${nAuto} (${pct(E8.auto_rate, 1)}) are auto-routed, and ${E8.counts.auto_correct} of those (${pct(E8.auto_precision)}) reach the correct department *and* the correct ward office. The other ${E8.counts.deferred} are deferred: 25 because department confidence was low, and 23 because the location was unresolved or ambiguous. Of the ${nErr} department errors in the whole set, ${deptErrCaught} were among the deferred complaints and only ${E8.counts.auto_wrong_dept} were auto-routed to a wrong queue. Mean processing time is ${E8.latency_ms_mean.toFixed(1)} ms per complaint (95th percentile ${E8.latency_ms_p95.toFixed(1)} ms) on a 2-vCPU machine, including the SQLite write, so for triage itself the cost of computation is negligible.`),
  P(`For comparison with the PMC backlog, a pipeline with this behaviour would route about seven in ten complaints within seconds, with roughly one in thirty-seven of those going to a wrong queue (${E8.counts.auto_wrong_dept} of ${nAuto} here). The remaining three in ten would reach an officer with a shortlist that contains the right department ${pct(PROP.top3, 0)} of the time. This projection comes from team-written text and assumes that real complaints behave similarly. Testing that assumption on real complaints is the next step.`),
  H(2, "5.9  Threats to validity"),
  B(`**All data is synthetic or team-written.** No real PMC complaint was used. Real complaints will be longer and noisier, will often report several issues at once, and will contain vocabulary this corpus lacks.`),
  B(`**Author overlap.** The same team wrote the test set, the gazetteer, the rule base and the labels. The ward and severity figures are in-sample checks of coverage. The department figures are the most trustworthy, because the classifier learned only from template text.`),
  B(`**Small test set.** With 160 complaints, one error changes accuracy by 0.6 points. The differences between the top two classifiers, and all duplicate-detection figures, are within noise.`),
  B(`**Simulated speech.** The noise model is uniform and random, whereas real ASR errors are structured (vowel-sign confusions, word-boundary errors, English words transcribed in Devanagari).`),
  B(`**Single annotator.** No inter-annotator agreement was measured for the severity labels.`),
  H(2, "5.10  Discussion against the objectives"),
  TCap("Table 5.5  Objectives and outcomes"),
  T(["Objective", "Outcome"], [
    ["1  Normalisation", "Met. One canonical form for all four input varieties."],
    ["2  Department classifier + baselines", `Met. ${pct(PROP.acc)} accuracy, ${pct(PROP.top3)} top-3; +${((PROP.acc - KW.acc) * 100).toFixed(1)} points over keywords.`],
    ["3  Ward resolution with honest deferral", "Met on the gazetteer. Ambiguous and unknown localities are deferred, not guessed; the fuzzy fallback limits the damage from transcription errors."],
    ["4  Explainable expert system", `Met. 19 rules, every decision explained; P1 recall ${pct(E5.rules_pred_dept.p1_recall)} end to end (in-sample).`],
    ["5  Duplicates as severity evidence", "Met in mechanism (R32 demonstrated in Section 4.6); duplicate metrics are on a small, team-written set."],
    ["6  Confidence-gated routing", `Met. ${pct(E8.auto_rate, 0)} auto-routed at ${pct(E8.auto_precision)} correct; ${deptErrCaught} of ${nErr} department errors deferred.`],
  ], [3000, 6026]),
  Brk(),
];

// ---------------------------------------------------------------- chapter 6
const ch6 = [
  H(1, "Chapter 6  Conclusions"),
  H(2, "6.1  Conclusions"),
  P(`This project built and measured the text-triage core of NagarVani, a proposed triage layer that would sit in front of PMC CARE. The prototype shows that the sorting step behind PMC's backlog can be largely automated for Marathi, Hindi, romanised and code-mixed complaints with lightweight, inspectable methods, *provided that* the system is designed to defer when it is unsure. On a hand-written test set, the department classifier reaches ${pct(PROP.acc)} accuracy and ${pct(PROP.top3)} top-3 accuracy. The pipeline auto-routes ${pct(E8.auto_rate, 0)} of complaints with ${pct(E8.auto_precision)} correct on department and ward together, and holds most of its errors back for a human. The rule-based severity module assigns every decision a plain-language justification, and it treats the number of citizens reporting a defect as evidence of urgency.`),
  P(`Three findings go beyond the headline numbers. First, character n-grams matter more than any other single choice, because they cope with Marathi inflection and with Latin-script typing at once. Second, evaluating only on template-generated data would have overstated accuracy by about 13 points. Third, the stage most exposed to speech errors is not the classifier but the exact-match components, the gazetteer and the severity cues, and fuzzy matching is a cheap and effective fix, shown here for the gazetteer.`),
  H(2, "6.2  Limitations"),
  P(`All data was written by the project team. No speech model was run. The gazetteer is approximate. The ward and severity results are in-sample with respect to the authors. PMC CARE was not integrated with, by design. Section 5.9 discusses each of these limitations.`),
  H(2, "6.3  Future scope"),
  B(`**Real data.** Obtain anonymised PMC CARE complaints, or collect volunteer complaints, and have them labelled by at least two annotators with agreement measured. Re-evaluate every stage on this data.`),
  B(`**Speech.** Fine-tune Whisper or IndicWav2Vec [1], [3] on recorded Marathi civic speech with a civic lexicon for shallow fusion, and replace the noise simulator with measured WER and CER on clean, noisy and code-mixed splits.`),
  B(`**Stronger encoders.** Replace TF-IDF with a fine-tuned MahaBERT or MuRIL classifier [6], [8] and MahaSBERT similarity [9] for deduplication, keeping the TF-IDF model as a fast fallback.`),
  B(`**Fuzzy and negation-aware cues** in the expert system, a transliteration step for romanised text, and GPS-assisted ward resolution.`),
  B(`**Clarification and closure.** Add a one-question Marathi clarification turn (M8) and the evidence-bound closure predicate (M9) that responds to the Standing Committee's directive [18].`),
  B(`**Deployment study.** Pilot the system in one ward office as a recommendation tool, and measure the time from submission to department assignment, the officer override rate and the per-ward fairness of the model.`),
  Brk(),
];

// ---------------------------------------------------------------- references
const refs = [
  H(1, "References"),
  ...REFS.map((r, i) => new Paragraph({ children: K.runs(`[${i + 1}]\t` + r, { size: 22 }), alignment: AlignmentType.LEFT,
    indent: { left: 567, hanging: 567 }, tabStops: [{ type: "left", position: 567 }], spacing: { after: 100, line: 260 } })),
];

// ---------------------------------------------------------------- document
const doc = new Document({
  creator: "NagarVani team", title: "NagarVani — PBL-4 Project Report",
  styles: {
    default: { document: { run: { font: K.fontObj, size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: K.fontObj, color: "12344D" }, paragraph: { spacing: { before: 120, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: K.fontObj, color: "12344D" }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, italics: true, font: K.fontObj }, paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
    { reference: "numObj", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] },
  ] },
  sections: [
    { properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
      children: [...title] },
    { properties: { type: SectionType.NEXT_PAGE, page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 },
        pageNumbers: { start: 1, formatType: "lowerRoman" } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 20 })] })] }) },
      children: [...abstract, ...buildIndex()] },
    { properties: { type: SectionType.NEXT_PAGE, page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 },
        pageNumbers: { start: 1, formatType: "decimal" } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
        new TextRun({ text: "NagarVani — PBL-4 Project Report    |    ", size: 18, color: "777777" }), new TextRun({ children: [PageNumber.CURRENT], size: 20 })] })] }) },
      children: [...ch1, ...ch2, ...ch3, ...ch4, ...ch5, ...ch6, ...refs] },
  ],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(process.argv[2] || "PBL-4_NagarVani_Project_Report.docx", b); console.log("ok"); });
fs.writeFileSync(__dirname + "/heads.json", JSON.stringify(HEADS));
