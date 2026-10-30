# Writing the test_v2 complaints

**For:** Abhinandan, Viraj and Adithya. **Deadline:** Saturday 31 October, 13:00.

`test_v2` is a held-out test set. It answers the objection that the 160 `test_v1` complaints
were written by the same people who wrote the classifier's training templates and the severity
rules. You did not write those, so your complaints are a fairer test. The set only works if it
stays independent:

* **Do not look at** `corpus/test_handwritten.tsv`, `corpus/train_template.tsv`,
  `corpus/generate_train.py` or `nagarvani/severity.py`, and do not run your sentences through the app.
* Write complaints the way a real citizen would type or say them, not the way you think the system wants.
* Do not show your rows to Aarush or paste them into a Claude Code session. Aarush commits the
  files without opening them, and they are evaluated once, after the Phase 2 fixes are committed.

## What to write

Each of you writes **30 complaints**: **3 for each of the 10 departments**. Mix the language
varieties roughly like this:

| `lang` | Meaning | About |
|---|---|---|
| `mr` | Marathi in Devanagari | 15 |
| `hi` | Hindi in Devanagari | 4 |
| `mr-rom` | Marathi typed in Latin letters (`rasta khup kharab zala aahe`) | 6 |
| `mix` | Marathi or Hindi mixed with English words, either script (`Baner मध्ये garbage van आली नाही`) | 5 |

Other guidance:

* Name a Pune locality in about 25 of your 30, and use no place name in the rest (`loc` = `NONE`).
  Spell place names however people really do: `Kothrud`, `कोथरूड`, `कोथरुडमध्ये` and `kothrud la` are all fine.
* Vary the severity: include some real emergencies (P1) and some routine requests (P4), not only P3.
* Vary the length, from 6 to 30 words. Typos, missing punctuation and colloquial spelling are welcome.
* One problem per complaint. No real names, phone numbers or house numbers.

## The file

Copy `corpus/test_v2_TEMPLATE.tsv` to `corpus/test_v2_<YOU>.tsv`, where `<YOU>` is `ABH`
(Abhinandan), `VIR` (Viraj) or `ADI` (Adithya). Delete the three `EX` example rows and add your 30.

The file is **tab-separated** UTF-8 with a header row. Edit it in a text editor (VS Code,
Notepad++) or in Google Sheets and download as `.tsv`. Do not save it from Excel, which
can break the Devanagari. Never put a tab or a line break inside the text.

| Column | What to put |
|---|---|
| `id` | `<YOU>` plus a two-digit number: `ABH01` to `ABH30`. |
| `lang` | `mr`, `hi`, `mr-rom` or `mix` (table above). |
| `dept` | The department that should handle it: one code from the department table below. |
| `loc` | The locality key from the locality table below, or `NONE` if no place is named or the place is not in the table. |
| `sev` | The priority band P1–P4 by the severity guideline below. |
| `text` | The complaint itself. |

The three example rows in the template:

* `EX1` is SWM, P2: garbage uncollected for 3 days or more.
* `EX2` is ELEC, P1: a dangling live wire. It names no place, so `loc` is `NONE`.
* `EX3` is TREE, P4: a trimming request.

When you are done, swap files with another writer and check each other's `dept` and `sev`
labels against the guideline. Settle disagreements between the two of you, without Aarush.
Then send the file to Aarush.

## Departments

| Code | Department | Typical complaints |
|---|---|---|
| `ROAD` | Roads (पथ विभाग) | Potholes, damaged or dug-up roads, sunken road, broken speed breaker |
| `SWM` | Solid waste (घनकचरा व्यवस्थापन) | Garbage not collected, overflowing bins, burning waste, littering |
| `WATER` | Water supply (पाणीपुरवठा) | No water, low pressure, dirty water, pipeline leak or burst |
| `DRAIN` | Drainage (मलनिःसारण / ड्रेनेज) | Blocked drain, sewage overflow, open or broken manhole |
| `ELEC` | Street lights (विद्युत) | Street light off, dangling wire, open DP box, sparking pole |
| `HEALTH` | Health and pest control (आरोग्य व कीटक नियंत्रण) | Mosquitoes, fogging, rats, disease outbreak, dirty public toilet |
| `TREE` | Garden and trees (उद्यान व वृक्ष) | Fallen or dangerous tree, branches on wires, trimming, garden upkeep |
| `ENCROACH` | Encroachment (अतिक्रमण) | Hawkers or stalls on the footpath, illegal banners, blocked walkway |
| `BUILD` | Building permission (बांधकाम परवानगी) | Illegal or unsafe construction, extra floors, construction debris |
| `VET` | Veterinary (पशुवैद्यकीय) | Stray dogs, dog bites, dead animal, cattle on the road, injured animal |

## Severity guideline (PBL-4 §3.3.4)

Every complaint receives exactly one priority band. Apply the first matching clause.

| Band | SLA | Assign when |
|---|---|---|
| P1 | 24 h | A person has been injured / bitten / had an accident; OR an immediate threat to life exists (open manhole or drain, live or dangling electric wire, open DP box, structure/tree/pole/hoarding that has collapsed or "can fall any time", tree blocking a road, rabid animal); OR a disease outbreak / people fallen ill; OR sewage entering a dwelling. |
| P2 | 72 h | Explicit risk of accident or damage without an event; public-health nuisance (smell, burning, rotting waste, flies, carcass, contaminated water, sewage on road, blocked drain); water outage >= 2 days; garbage uncollected >= 3 days; pipeline burst / major wastage. |
| P3 | 7 days | Default: a functional civic defect with no hazard or health cue. |
| P4 | 15 days | Service request or cosmetic issue (trimming, sterilisation, new lights, billing, banners, timing, barking). |

Modifiers (applied after the band): near a school or hospital -> one band higher; problem stated to persist >= 14 days -> one band higher; >= 3 independent reports of the same defect -> one band higher. Bands never exceed P1.

The `sev` you write is the band **after** modifiers. You only know what the complaint says,
so apply a modifier only when the text states it (for example "शाळेसमोर", "15 दिवसांपासून").

## Localities

These are the only valid `loc` keys. They come from `data/gazetteer.json`. The Marathi name is
for recognition only, and your text may spell the place any way. A place that is not in this
table gets `NONE`.

| Ward office | Locality keys |
|---|---|
| AUB Aundh-Baner | `aundh` (औंध), `baner` (बाणेर), `balewadi` (बालेवाडी), `pashan` (पाषाण) |
| SGR Shivajinagar-Ghole Road | `shivajinagar` (शिवाजीनगर), `deccan` (डेक्कन), `model_colony` (मॉडेल कॉलनी), `fc_road` (एफसी रोड) |
| KOB Kothrud-Bavdhan | `kothrud` (कोथरूड), `bavdhan` (बावधन), `paud_road` (पौड रोड) |
| WKN Warje-Karvenagar | `warje` (वारजे), `karvenagar` (कर्वेनगर) |
| SHR Sinhagad Road | `sinhagad_road` (सिंहगड रोड), `vadgaon_bk` (वडगाव बुद्रुक), `dhayari` (धायरी), `anandnagar` (आनंदनगर), `hingne` (हिंगणे) |
| DSN Dhankawadi-Sahakarnagar | `dhankawadi` (धनकवडी), `sahakarnagar` (सहकारनगर), `katraj` (कात्रज), `balajinagar` (बालाजीनगर) |
| BIB Bibwewadi | `bibwewadi` (बिबवेवाडी), `market_yard` (मार्केट यार्ड), `gultekdi` (गुलटेकडी) |
| KYW Kondhwa-Yewalewadi | `kondhwa` (कोंढवा), `yewalewadi` (येवलेवाडी), `nibm` (एनआयबीएम), `undri` (उंड्री), `pisoli` (पिसोळी) |
| WRT Wanowrie-Ramtekdi | `wanowrie` (वानवडी), `ramtekdi` (रामटेकडी), `fatimanagar` (फातिमानगर), `salunke_vihar` (साळुंके विहार) |
| HMU Hadapsar-Mundhwa | `hadapsar` (हडपसर), `mundhwa` (मुंढवा), `magarpatta` (मगरपट्टा), `keshavnagar` (केशवनगर) |
| NWS Nagar Road-Wadgaon Sheri | `wadgaon_sheri` (वडगाव शेरी), `kharadi` (खराडी), `viman_nagar` (विमाननगर), `chandannagar` (चंदननगर) |
| YKD Yerawada-Kalas-Dhanori | `yerawada` (येरवडा), `vishrantwadi` (विश्रांतवाडी), `dhanori` (धानोरी), `kalas` (कळस), `lohegaon` (लोहगाव) |
| DPR Dhole Patil Road | `koregaon_park` (कोरेगाव पार्क), `sangamwadi` (संगमवाडी), `pune_station` (पुणे स्टेशन), `tadiwala_road` (ताडीवाला रोड) |
| KVB Kasba-Vishrambaugwada | `kasba_peth` (कसबा पेठ), `shaniwar_peth` (शनिवार पेठ), `sadashiv_peth` (सदाशिव पेठ), `narayan_peth` (नारायण पेठ) |
| BHP Bhavani Peth | `bhavani_peth` (भवानी पेठ), `nana_peth` (नाना पेठ), `guruwar_peth` (गुरुवार पेठ), `kashewadi` (काशेवाडी) |
