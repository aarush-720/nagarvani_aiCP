const fs = require("fs");
const { R, pct, f2, f3, makeKit, REFS, d } = require("./helpers");
const { Document, Packer, Paragraph, TextRun, AlignmentType, LevelFormat, SectionType, Table, TableRow, TableCell,
        WidthType, BorderStyle } = d;
const K = makeKit({ size: 20, line: 240, pAfter: 40 });
const E1 = R.E1_dept, PROP = E1["Char + word TF-IDF + LogReg (proposed)"], CHAR = E1["Char n-gram TF-IDF + LogReg"];
const KW = E1["Keyword lexicon (no ML)"];
const E3 = R.E3_calibration, tau50 = R.E3_abstention_curve.find(c => c.tau === 0.5);
const E4 = R.E4_ward, E5 = R.E5_severity, E6 = R.E6_dedup, E7 = R.E7_asr_noise, E8 = R.E8_end_to_end;
const nErr = R.E2_confusions.length, DATA = R.data;
const nAuto = E8.counts.auto_correct + (E8.counts.auto_wrong_dept || 0);
const caught = nErr - (E8.counts.auto_wrong_dept || 0);
const cer10 = E7.find(e => e.cer === 0.1), cer20 = E7.find(e => e.cer === 0.2);

const P = (t, o = {}) => new Paragraph({ children: K.runs(t, o.run || {}), alignment: AlignmentType.JUSTIFIED,
  indent: o.noIndent ? undefined : { firstLine: 202 }, spacing: { after: 40, line: 240 } });
const roman = ["I", "II", "III", "IV", "V", "VI", "VII"];
let sec = 0, sub = 0;
const S = (t) => { sub = 0; return new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 160, after: 80 },
  children: [new TextRun({ text: `${roman[sec++]}. `, size: 20 }), new TextRun({ text: t, smallCaps: true, size: 20 })] }); };
const SS = (t) => new Paragraph({ keepNext: true, spacing: { before: 80, after: 40 },
  children: [new TextRun({ text: `${String.fromCharCode(65 + sub++)}. ${t}`, italics: true, size: 20 })] });
const TCAP = (n, t) => [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 0 },
  children: [new TextRun({ text: `TABLE ${n}`, size: 16, smallCaps: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { after: 60 }, children: [new TextRun({ text: t, size: 16, smallCaps: true })] })];
const FIG = (name, cap) => { const f = K.Fig(name, 3.2, cap); return f; };
const Bl = (t) => new Paragraph({ numbering: { reference: "b", level: 0 }, children: K.runs(t), alignment: AlignmentType.JUSTIFIED, spacing: { after: 20, line: 240 } });
const T = (h, rows, w) => K.T(h, rows, w, { size: 15 });
const COLW = 4838;

// ------------------------------------------------ title + authors
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const nb = { top: none, bottom: none, left: none, right: none, insideHorizontal: none, insideVertical: none };
const author = (name, line2, w) => new TableCell({ borders: nb, width: { size: w, type: WidthType.DXA }, children: [
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: name, size: 20 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Dept. of Information Technology", size: 17, italics: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Vishwakarma Institute of Technology", size: 17, italics: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Pune, India", size: 18 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: line2, size: 18 })] })] });
const W3 = 3290;
const authors = [
  new Table({ width: { size: W3 * 3, type: WidthType.DXA }, columnWidths: [W3, W3, W3], borders: nb, alignment: AlignmentType.CENTER, rows: [
    new TableRow({ children: [author("[Author 1 Name]", "[email]@vit.edu", W3), author("[Author 2 Name]", "[email]@vit.edu", W3), author("[Author 3 Name]", "[email]@vit.edu", W3)] })] }),
  new Table({ width: { size: W3 * 2, type: WidthType.DXA }, columnWidths: [W3, W3], borders: nb, alignment: AlignmentType.CENTER, rows: [
    new TableRow({ children: [author("[Author 4 Name]", "[email]@vit.edu", W3), author("Pravin R. Futane (Guide)", "[guide email]@vit.edu", W3)] })] }),
];
const head = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({
    text: "NagarVani: An Explainable Triage Layer for Marathi, Hindi and Code-Mixed Municipal Grievances", size: 44 })] }),
  ...authors,
];

// ------------------------------------------------ body
const body = [
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 228 }, children: [
    new TextRun({ text: "Abstract", bold: true, italics: true, size: 18 }), new TextRun({ text: "—", bold: true, size: 18 }),
    ...K.runs(`Complaints to the Pune Municipal Corporation arrive as unstructured Marathi, Hindi and code-mixed text, and each one must be read and assigned to a department and a ward office by hand. In September 2026, 14,644 complaints were pending, many of them never forwarded. This paper presents NagarVani, a prototype triage layer intended to sit in front of the PMC CARE system. It combines a character- and word-n-gram TF-IDF logistic-regression department classifier, a suffix-tolerant gazetteer ward resolver with a fuzzy fallback, a 19-rule forward-chaining expert system that assigns priority bands P1–P4 and explains every decision, duplicate detection with (ward, department) blocking and location-masked similarity, and a confidence gate that defers uncertain cases to a human officer. On 160 hand-written test complaints in four input varieties, the classifier reaches ${pct(PROP.acc)} accuracy and ${pct(PROP.top3)} top-3 accuracy, against ${pct(KW.acc)} for a keyword baseline. The pipeline auto-routes ${pct(E8.auto_rate, 0)} of complaints, ${pct(E8.auto_precision)} of them to the correct department and ward, and defers ${caught} of its ${nErr} department errors. At a simulated 10% transcription error rate, department macro-F1 is ${f3(cer10.dept_macro_f1)}, and fuzzy matching raises ward accuracy from ${pct(cer10.ward_acc_exact, 0)} to ${pct(cer10.ward_acc, 0)}. All data is team-constructed, and the limitations this implies are stated.`, { size: 18, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, line: 228 }, children: [
    new TextRun({ text: "Keywords", bold: true, italics: true, size: 18 }), new TextRun({ text: "—", bold: true, size: 18 }),
    new TextRun({ text: "civic grievance triage, Marathi NLP, code-mixed text classification, expert systems, duplicate detection, selective prediction, e-governance", bold: true, size: 18 })] }),

  S("Introduction"),
  P(`PMC receives complaints through nine channels, including WhatsApp, a call centre, a mobile app and a Marathi web interface. Receiving complaints is not the bottleneck. Each complaint arrives as free Marathi, Hindi or code-mixed text or voice, and a nodal officer must assign it to one of about 43 departments across 15 regional offices. In the first week of September 2026, PMC CARE 2.0 had 14,644 complaints pending (2,010 in Kondhwa–Yewalewadi alone), and the administration acknowledged that complaints from the preceding two months had not been consistently forwarded [17]. Separately, the Standing Committee directed that no complaint be closed without the complainant's feedback [18]. Much of the backlog is therefore triage work, not repair work.`),
  P(`We present NagarVani, a triage layer that would take a complaint in any of four input varieties (Marathi in Devanagari, Hindi, romanised Marathi, and Marathi–English code-mixed text) and produce a department, a ward office, a priority band with a service-level deadline, a duplicate link, and an auto-route or defer decision. **Because PMC CARE exposes no public API, the prototype does not file complaints into it.** It writes to SQLite and exports per-ward CSV queues. Its output is a recommendation awaiting officer confirmation, a proposal and not an integration. Our contributions are: (i) a small multilingual civic-complaint resource (a template training corpus, a hand-written test set, duplicate pairs and a gazetteer); (ii) an explainable production-rule severity model that treats the number of citizens reporting a defect as evidence of urgency; (iii) an end-to-end evaluation that measures routing to the correct department *and* ward together with the deferral rate, including a transcription-noise stress test.`),

  S("Literature Survey"),
  P(`*Speech.* Whisper [1] generalises zero-shot to noisy speech, but its quality depends on how much of a language it was trained on. wav2vec 2.0 [2] and IndicWav2Vec [3] make low-resource Indic ASR feasible, and IndicWav2Vec shows that Indic-family pre-training transfers well to Marathi. Palivela *et al.* [4] find that multilingual models handle Hindi–Marathi code-switching better than monolingual ones.`),
  P(`*Language models.* BERT [5] set the pre-train-then-fine-tune recipe. MuRIL [6] aligns romanised and native-script text. IndicNLPSuite [7] provides corpora and benchmarks. MahaBERT [8] shows that Marathi-specific pre-training beats multilingual models, and MahaSTS [9] supplies Marathi sentence-similarity data.`),
  P(`*Complaints and tickets.* Sentence-BERT [10] makes large-scale similarity search cheap. Isotani *et al.* [11] obtain better duplicate detection by scoring fields separately. Rakhimzhanov *et al.* [12] reach about 90% accuracy classifying complaints with embeddings instead of LLMs. Zicari *et al.* [13] warn that ticket classifiers overfit to spurious cues and recommend ensembles with explanations.`),
  P(`*Public-sector deployment and verification.* Government chatbots mostly retrieve information [14], and their successful implementation depends on knowledge management and resources rather than model quality [15]. Vision-based pothole detection is useful but brittle [16].`),
  P(`*Gap.* No public Marathi civic-complaint resource exists. Classification is evaluated apart from routing. Duplicate detection and severity are treated independently. Production systems [20], although transparent and auditable, are rarely used for severity in this setting. NagarVani addresses these points at prototype scale.`),

  S("Proposed Methodology"),
  ...FIG("fig_architecture.png", "Fig. 1.  Implemented data flow. The ASR backend (dashed) was not run."),
  SS("Data"),
  P(`The label space is ten high-volume PMC departments (Road, Solid Waste, Water, Drainage, Electrical, Health, Tree, Anti-Encroachment, Building, Veterinary), 15 ward offices and four priority bands with deadlines of 24 h, 72 h, 7 days and 15 days. A generator combines tagged issue phrases with greetings, localities, durations and school or hospital mentions to produce ${DATA.n_train.toLocaleString("en-IN")} training complaints (${DATA.train_lang.mr} Marathi, ${DATA.train_lang.hi} Hindi, ${DATA.train_lang["mr-rom"]} romanised, ${DATA.train_lang.mix} code-mixed). Their severity labels come from the phrase tags. A **separately hand-written test set** of 160 complaints (16 per department; 80/20/30/30 by variety) uses a spontaneous register, inflected localities, out-of-gazetteer places and a negated duration. It is labelled for department, locality (${DATA.test_loc_none} have none) and severity (P1 ${DATA.test_sev.P1}, P2 ${DATA.test_sev.P2}, P3 ${DATA.test_sev.P3}, P4 ${DATA.test_sev.P4}) under a written guideline. We also wrote 30 duplicate pairs and a gazetteer of 59 localities mapped to wards, with Marathi oblique stems (*कोंढव्या*) and one ambiguous name (*वडगाव*).`),
  SS("Normalisation and Department Classification"),
  P(`Text is converted to Unicode NFC, stripped of zero-width characters, given ASCII digits, lower-cased, and cleaned of repeated characters. The classifier concatenates char_wb 2–5-gram and word 1–2-gram TF-IDF features (sublinear TF) and feeds them to class-balanced logistic regression (C = 10, chosen by 5-fold cross-validation on the training data). Character n-grams cope with Marathi suffixation (*रस्त्यावर*) and read Devanagari and Latin script with the same model. A custom token pattern is needed, because the default \\w pattern splits Devanagari words at vowel signs.`),
  SS("Ward Resolution"),
  P(`Aliases are matched longest first and masked once matched. Devanagari aliases match as sub-strings, which tolerates suffixes, and Latin aliases match only as whole words. One matched ward means *resolved*, two or more means *ambiguous*, and none means *unresolved*; the last two are deferred. If exact matching fails, a fuzzy fallback accepts the best alias whose difflib ratio against a token window is at least 0.80.`),
  SS("Severity Expert System"),
  P(`The knowledge base contains 23 cue groups (226 strings across the three scripts and English) and 19 condition–action rules. Working memory holds the extracted facts, the department, a parsed duration and the duplicate-cluster size. Rules fire in salience order. Life-safety rules at salience 100 set P1: injury or bite, an open manhole, a live or dangling wire, imminent collapse, a tree blocking a road, an outbreak, sewage in a home, or a rabid animal. Hazard and health rules at 50 cap the band at P2. A request rule at 10 relaxes the band to P4 only if no hazard rule has fired. Escalation rules at 0 raise the band one level for a school or hospital nearby, for a problem persisting 14 days or more, and for **three or more duplicate reports** (R32). Each ticket stores the text of the rules that fired.`),
  SS("Duplicate Detection and Routing"),
  P(`Candidates are blocked to open tickets with the same predicted department and ward. Similarity is the cosine between character-2–4-gram TF-IDF vectors after all gazetteer aliases have been removed, following the field-wise idea of [11]. A similarity of θ_high = 0.45 or more merges the complaint into the cluster, a similarity between θ_low = 0.30 and θ_high queues it for officer review, and anything lower opens a new cluster. A ticket is auto-routed only if its top department probability is at least τ = 0.50 **and** its ward is resolved. Otherwise it enters a nodal-review queue with the top three departments filled in.`),

  S("Results and Discussion"),
  SS("Department Classification"),
  ...TCAP("I", "Department classification on the hand-written test set (n = 160)"),
  T(["Model", "Acc.", "Macro-F1", "Top-3", "Rom.", "Mix"], Object.entries(E1).map(([n, v]) => [
    n.replace("TF-IDF + ", "").replace("Keyword lexicon (no ML)", "Keyword lexicon").replace(" (proposed)", " †"),
    pct(v.acc), f3(v.macro_f1), pct(v.top3), pct(v.by_lang["mr-rom"], 0), pct(v.by_lang.mix, 0)]),
    [1700, 620, 680, 620, 580, 638]),
  P(`Table I shows that the proposed model (†) beats the keyword lexicon by ${((PROP.acc - KW.acc) * 100).toFixed(1)} points, and the correct department is in its top three ${pct(PROP.top3)} of the time. Word-level models perform no better than the keyword lexicon and are weakest on romanised text. Two results run against our own configuration. First, character n-grams *alone* scored higher on the test set (${pct(CHAR.acc)}). We fixed the configuration before testing and report the difference (${Math.round((CHAR.acc - PROP.acc) * 160)} complaints) rather than switching models after seeing the results. Second, cross-validation *inside* the template corpus gives ${pct(R.E1_cv_template.acc)}, about 13 points above the hand-written result, which shows why the test set had to be written separately. The ${nErr} errors cluster in departments that overlap (drain smell → SWM, branch on power lines → ELEC), in vocabulary missing from the training data (*निर्माल्य*, a rooftop tower), and in dominant nouns (*मेलेलं कुत्रं*, a dead dog, → VET).`),
  SS("Confidence Gate"),
  ...FIG("fig_abstention.png", "Fig. 2.  Coverage and accuracy on auto-routed complaints vs. τ."),
  P(`Mean confidence is ${f3(E3.mean_conf_correct)} on correct predictions and ${f3(E3.mean_conf_wrong)} on errors (ECE ${f3(E3.ece)}; the model is under-confident on average). At τ = 0.50, ${pct(tau50.coverage)} of complaints pass the department gate with ${pct(tau50.acc_auto)} accuracy (Fig. 2), which cuts misrouting among confident cases from ${pct(1 - PROP.acc)} to ${pct(tau50.misroute_rate_auto)}.`),
  SS("Ward Resolution and Duplicates"),
  P(`On clean text, all ${E4.n_with_locality} gazetteer localities resolve correctly and all ${E4.n_without} complaints without a known locality stay unresolved. The fuzzy fallback adds one false resolution (*बाहेर* ≈ *बाणेर*). Because the same team wrote the gazetteer and the test set, this is a coverage check. For duplicates, blocking removes all ten cross-department negatives, and location masking keeps same-ward, same-department negatives at a similarity of ${f2(Math.max(...E6.pairs.filter(p => p.kind === "same-ward-same-dept").map(p => p.sim)))} or less. At θ_high, merges have precision ${f2(E6.merge_block.precision)} and recall ${f2(E6.merge_block.recall)}. Including the review band, ${E6.review_block.tp} of 15 duplicates are merged or reviewed. The one miss was lost at the blocking stage after a department error.`),
  SS("Severity: Rules vs. Learning"),
  ...TCAP("II", "Severity assignment (n = 160)"),
  T(["Method", "Acc.", "MAE", "P1 rec.", "Under"], [["Always P3", "majority_P3"], ["Learned LogReg", "learned_logreg"],
    ["Rules, no escalation", "rules_no_escalation"], ["Rules, pred. dept", "rules_pred_dept"], ["Rules, gold dept", "rules_gold_dept"]]
    .map(([n, k]) => [n, pct(E5[k].acc), f3(E5[k].mae), pct(E5[k].p1_recall), pct(E5[k].under_triage)]), [1700, 750, 750, 850, 788]),
  P(`With predicted departments, the rules reach ${pct(E5.rules_pred_dept.acc)} band accuracy and ${pct(E5.rules_pred_dept.p1_recall)} P1 recall. A logistic-regression model trained on the same guideline reaches ${pct(E5.learned_logreg.acc)} and misses ${pct(1 - E5.learned_logreg.p1_recall, 0)} of P1 cases. Removing escalation increases under-triage. **This comparison favours the rules:** the same authors wrote the guideline, the cue lexicon and the labels. On the 2,000 template complaints, whose labels come from phrase tags, the rules reach ${pct(E5.rules_on_template_set_gold_dept.acc)}. Every remaining test error is one band off, and none downgrades a P1. The errors come from negation (*महिना झाला नाही*), past tense, and an injured animal that triggered a rule meant for injured people. The lasting advantage of rules is that they can be audited, and that life-safety rules fire however rare the case is in training data.`),
  SS("Robustness to Transcription Errors"),
  ...FIG("fig_asr_noise.png", "Fig. 3.  Degradation under simulated character error rate (5 seeds)."),
  P(`No Marathi ASR model could be run, because the model hubs were blocked in our build environment. We therefore corrupted the test text with random substitutions, deletions and insertions. Department macro-F1 falls gradually (${f3(cer10.dept_macro_f1)} at 10% CER, ${f3(cer20.dept_macro_f1)} at 20%). Exact ward matching is brittle (${pct(cer10.ward_acc_exact, 0)} at 10%), and the fuzzy fallback recovers most of the loss (${pct(cer10.ward_acc, 0)}). Severity is the most fragile stage (${pct(cer20.sev_acc, 0)} at 20%), which makes fuzzy cue matching a priority before speech input is connected.`),
  SS("End-to-End Routing"),
  P(`Run as a stream, the pipeline auto-routes ${nAuto} of 160 complaints (${pct(E8.auto_rate, 0)}), ${E8.counts.auto_correct} of them to the correct department and ward (${pct(E8.auto_precision)}). It defers 48: 25 for low confidence and 23 for location. Only ${E8.counts.auto_wrong_dept} of the ${nErr} department errors reach a wrong queue. Mean latency is ${E8.latency_ms_mean.toFixed(1)} ms per complaint on 2 vCPUs. In a scripted demonstration, the third report of the same pothole merges at a similarity of 0.80 and rule R32 escalates it from P3 to P2.`),
  SS("Threats to Validity"),
  P(`All data was constructed by the team, the test set is small (one error changes accuracy by 0.6 points), ward and severity labels overlap with the authors' own rules, a single annotator labelled the data, and the speech noise is simulated. The department results are the most trustworthy, because the classifier learned only from template text.`),

  S("Conclusion"),
  P(`NagarVani shows that the sorting step behind PMC's backlog can be largely automated for multilingual and code-mixed Marathi complaints with lightweight, inspectable components, provided that the system defers when it is uncertain. Character n-grams, deferral that accounts for location, and a production-rule severity model with duplicate-driven escalation together auto-route about 70% of complaints at 97% end-to-end precision on our test set, and every decision carries an explanation an officer can audit.`),

  S("Future Scope"),
  P(`Next steps are to: evaluate on anonymised real PMC complaints labelled by multiple annotators; fine-tune Whisper or IndicWav2Vec on recorded civic speech and measure WER and CER; replace TF-IDF with MahaBERT or MuRIL and use MahaSBERT for deduplication; add fuzzy and negation-aware cues, transliteration and GPS priors; build the one-question Marathi clarification turn and evidence-based closure verification responding to [18]; and pilot the system as a recommendation tool in one ward office, measuring the time to department assignment and the officer override rate.`),

  new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 160, after: 80 },
    children: [new TextRun({ text: "References", smallCaps: true, size: 20 })] }),
  ...REFS.map((r, i) => new Paragraph({ children: K.runs(`[${i + 1}]\t` + r, { size: 16 }), alignment: AlignmentType.LEFT,
    indent: { left: 360, hanging: 360 }, tabStops: [{ type: "left", position: 360 }], spacing: { after: 30, line: 220 } })),
];

const page = { size: { width: 11906, height: 16838 }, margin: { top: 1080, bottom: 1440, left: 1015, right: 1015 } };
const doc = new Document({
  creator: "NagarVani team", title: "NagarVani — IEEE draft paper",
  styles: { default: { document: { run: { font: K.fontObj, size: 20 } } } },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 300, hanging: 200 } } } }] }] },
  sections: [
    { properties: { page, column: { count: 1 } }, children: head },
    { properties: { type: SectionType.CONTINUOUS, page, column: { count: 2, space: 340, equalWidth: true } }, children: body },
  ],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(process.argv[2] || "paper.docx", b); console.log("ok"); });
