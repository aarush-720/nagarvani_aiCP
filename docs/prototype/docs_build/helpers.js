const fs = require("fs");
const d = require("docx");
const { Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType,
        BorderStyle, ShadingType, ImageRun, PageBreak } = d;

const R = JSON.parse(fs.readFileSync(__dirname + "/../results/results.json", "utf8").replace(/\bNaN\b/g, "null"));
const FIGDIR = __dirname + "/../results/figures/";
const pct = (x, dp = 1) => (100 * x).toFixed(dp) + "%";
const f2 = (x) => Number(x).toFixed(2);
const f3 = (x) => Number(x).toFixed(3);

function makeKit(cfg) {
  const FONT = cfg.font || "Times New Roman";
  const SIZE = cfg.size || 24;          // half-points
  const CS = "Nirmala UI";
  const fontObj = { ascii: FONT, hAnsi: FONT, cs: CS, eastAsia: FONT };

  function runs(text, base = {}) {
    // mini markdown: **bold**, *italic*, `code`
    const out = [];
    const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
    let last = 0, m;
    while ((m = re.exec(text)) !== null) {
      if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
      const t = m[0];
      if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
      else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: "Consolas", size: (base.size || SIZE) - 2 }));
      else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
      last = m.index + t.length;
    }
    if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
    return out;
  }
  const P = (text, o = {}) => new Paragraph({
    children: runs(text, o.run || {}), alignment: o.align ?? AlignmentType.JUSTIFIED,
    spacing: { after: o.after ?? cfg.pAfter ?? 120, before: o.before ?? 0, line: cfg.line || 276 },
    indent: o.indent, keepNext: o.keepNext });
  const H = (lvl, text) => new Paragraph({ heading: [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3][lvl - 1],
    children: [new TextRun(text)], keepNext: true });
  const B = (text, ref = "bullets", level = 0) => new Paragraph({ numbering: { reference: ref, level },
    children: runs(text), alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: cfg.line || 276 } });
  const N = (text, ref) => B(text, ref, 0);

  const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
  const borders = { top: border, bottom: border, left: border, right: border };
  function T(headers, rows, widths, o = {}) {
    const total = widths.reduce((a, b) => a + b, 0);
    const fs_ = o.size || (SIZE - 4);
    const cell = (txt, w, head, shade) => new TableCell({
      borders, width: { size: w, type: WidthType.DXA },
      shading: head ? { fill: "DCE6F0", type: ShadingType.CLEAR, color: "auto" } : (shade ? { fill: shade, type: ShadingType.CLEAR, color: "auto" } : undefined),
      margins: { top: 50, bottom: 50, left: 80, right: 80 },
      children: String(txt).split("\n").map(line => new Paragraph({ children: runs(line, { size: fs_, bold: head || undefined }),
        alignment: AlignmentType.LEFT, spacing: { after: 0, line: 240 } })) });
    const trs = [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true)) })];
    rows.forEach((r, ri) => trs.push(new TableRow({ cantSplit: true,
      children: r.map((c, i) => cell(c, widths[i], false, o.highlightRow === ri ? "FFF2CC" : undefined)) })));
    return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, rows: trs,
      alignment: AlignmentType.CENTER });
  }
  const Cap = (text) => new Paragraph({ children: runs(text, { size: SIZE - 4 }), alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 200 } });
  const TCap = (text) => new Paragraph({ children: runs(text, { size: SIZE - 4 }), alignment: AlignmentType.CENTER,
    spacing: { before: 160, after: 80 }, keepNext: true });
  function pngSize(p) { const b = fs.readFileSync(p); return [b.readUInt32BE(16), b.readUInt32BE(20)]; }
  function Fig(name, widthIn, caption) {
    const p = FIGDIR + name; const [w, h] = pngSize(p);
    const W = Math.round(widthIn * 96), Hh = Math.round(W * h / w);
    return [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 0 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(p), transformation: { width: W, height: Hh },
        altText: { title: caption, description: caption, name: name } })] }), Cap(caption)];
  }
  const Code = (lines, sz) => lines.map((l, i) => new Paragraph({ children: [new TextRun({ text: l || " ", font: "Consolas", size: sz || SIZE - 6 })],
    shading: { fill: "F2F2F2", type: ShadingType.CLEAR, color: "auto" }, spacing: { after: 0, line: 240 },
    indent: { left: 200 }, keepNext: i < lines.length - 1, keepLines: true }));
  const Brk = () => new Paragraph({ children: [new PageBreak()] });
  return { P, H, B, N, T, Cap, TCap, Fig, Code, Brk, runs, fontObj };
}

const REFS = [
  "A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey, and I. Sutskever, “Robust speech recognition via large-scale weak supervision,” in *Proc. 40th Int. Conf. Machine Learning (ICML)*, PMLR vol. 202, Honolulu, HI, USA, 2023, pp. 28492–28518.",
  "A. Baevski, Y. Zhou, A. Mohamed, and M. Auli, “wav2vec 2.0: A framework for self-supervised learning of speech representations,” in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 33, 2020, pp. 12449–12460.",
  "T. Javed *et al.*, “Towards building ASR systems for the next billion users,” in *Proc. AAAI Conf. Artificial Intelligence*, vol. 36, no. 10, 2022, pp. 10813–10821, doi: 10.1609/aaai.v36i10.21327.",
  "H. Palivela, M. Narvekar, D. Asirvatham, S. Bhushan, V. Rishiwal, and U. Agarwal, “Code-switching ASR for low-resource Indic languages: A Hindi-Marathi case study,” *IEEE Access*, vol. 13, pp. 9171–9198, 2025, doi: 10.1109/ACCESS.2025.3527745.",
  "J. Devlin, M.-W. Chang, K. Lee, and K. Toutanova, “BERT: Pre-training of deep bidirectional transformers for language understanding,” in *Proc. NAACL-HLT*, Minneapolis, MN, USA, 2019, pp. 4171–4186.",
  "S. Khanuja *et al.*, “MuRIL: Multilingual representations for Indian languages,” arXiv preprint arXiv:2103.10730, 2021.",
  "D. Kakwani *et al.*, “IndicNLPSuite: Monolingual corpora, evaluation benchmarks and pre-trained multilingual language models for Indian languages,” in *Findings of the Association for Computational Linguistics: EMNLP 2020*, 2020, pp. 4948–4961.",
  "R. Joshi, “L3Cube-MahaCorpus and MahaBERT: Marathi monolingual corpus, Marathi BERT language models, and resources,” in *Proc. WILDRE-6 Workshop, 13th Language Resources and Evaluation Conf. (LREC)*, Marseille, France, 2022.",
  "A. Mirashi, A. Joshi, and R. Joshi, “L3Cube-MahaSTS: A Marathi sentence similarity dataset and models,” arXiv preprint arXiv:2508.21569, 2025.",
  "N. Reimers and I. Gurevych, “Sentence-BERT: Sentence embeddings using Siamese BERT-networks,” in *Proc. EMNLP-IJCNLP*, Hong Kong, China, 2019, pp. 3982–3992.",
  "H. Isotani, H. Washizaki, Y. Fukazawa, T. Nomoto, S. Ouji, and S. Saito, “Sentence embedding and fine-tuning to automatically identify duplicate bugs,” *Frontiers in Computer Science*, vol. 4, art. no. 1032452, 2023, doi: 10.3389/fcomp.2022.1032452.",
  "D. Rakhimzhanov, S. Belginova, and D. Yedilkhan, “Automated classification of public transport complaints via text mining using LLMs and embeddings,” *Information*, vol. 16, no. 8, art. no. 644, 2025, doi: 10.3390/info16080644.",
  "P. Zicari, G. Folino, M. Guarascio, and L. Pontieri, “Combining deep ensemble learning and explanation for intelligent ticket management,” *Expert Systems with Applications*, vol. 206, art. no. 117815, 2022, doi: 10.1016/j.eswa.2022.117815.",
  "M. E. Cortés-Cediel, A. Segura-Tinoco, I. Cantador, and M. P. Rodríguez Bolívar, “Trends and challenges of e-government chatbots: Advances in exploring open government data and citizen participation content,” *Government Information Quarterly*, vol. 40, art. no. 101877, 2023, doi: 10.1016/j.giq.2023.101877.",
  "T. Chen, M. Gascó-Hernandez, and M. Esteve, “The adoption and implementation of artificial intelligence chatbots in public organizations: Evidence from U.S. state governments,” *The American Review of Public Administration*, vol. 54, no. 3, pp. 255–270, 2024, doi: 10.1177/02750740231200522.",
  "Y. Safyari, M. Mahdianpari, and H. Shiri, “A review of vision-based pothole detection methods using computer vision and machine learning,” *Sensors*, vol. 24, no. 17, art. no. 5652, 2024, doi: 10.3390/s24175652.",
  "Punekar News, “PMC Care 2.0: 14,644 citizen complaints pending across Pune,” Sep. 2026. [Online]. Available: https://www.punekarnews.in/?p=243635 (accessed Sep. 30, 2026).",
  "Punekar News, “Pune: PMC officials to face action if citizen complaints lodged through ‘PMC Care’ are closed without resolution,” 2026. [Online]. Available: https://www.punekarnews.in/?p=238398 (accessed Sep. 30, 2026).",
  "F. Pedregosa *et al.*, “Scikit-learn: Machine learning in Python,” *Journal of Machine Learning Research*, vol. 12, pp. 2825–2830, 2011.",
  "E. Rich, K. Knight, and S. B. Nair, *Artificial Intelligence*, 3rd ed. New Delhi, India: Tata McGraw-Hill, 2009.",
  "C. Guo, G. Pleiss, Y. Sun, and K. Q. Weinberger, “On calibration of modern neural networks,” in *Proc. 34th Int. Conf. Machine Learning (ICML)*, PMLR vol. 70, Sydney, Australia, 2017, pp. 1321–1330.",
];

module.exports = { R, pct, f2, f3, makeKit, REFS, d };
