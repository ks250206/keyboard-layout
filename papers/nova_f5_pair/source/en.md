# NOVA F5-Pair: Pair-Constrained Keyboard Layout Optimization for Japanese Romanized Input, English, and Source Code

ks250206

NOVA keyboard-layout project | Research manuscript, version 1.0 | 31 October 2026

## Abstract

Keyboard layouts optimized for movement alone can distribute punctuation in ways that are difficult to memorize. We developed a reproducible computational workflow for Japanese romanized input, English prose, and programming text, culminating in NOVA F5-Pair. A frequency-weighted motor-time surrogate combines same-finger travel, finger-specific row and lateral costs, and explicit opposite-hand Shift actions. Digits remain fixed, shifted letters remain uppercase, and nine punctuation pairs must be adjacent in their prescribed order on one layer or share a base/Shift key. Multi-start simulated annealing evaluated 64 million proposals for unconstrained-symbol F4 experiments and 38.4 million proposals for pair-constrained F5 experiments. Final Japanese inputs were split at sentence level; English and seven programming languages used separate training and test documents or files. F5-Pair yielded modeled speed gains of 16.00%, 15.99%, 10.81%, and 10.61% over the modeled QWERTY-JIS baseline on Japanese test sentences, loanword-rich diagnostic Japanese, English test prose, and held-out code, respectively. The corresponding KLA-main approximation scores were 72.82, 70.64, 72.93, and 62.00. Relative to F4-Balance, the code-time penalty was only 0.154%, while all nine pair constraints were satisfied. F5-Pair was selected for adoption in the GALACTYPE typing-game project as a rule-consistent compromise, not as a proven human-performance optimum. All time coefficients remain uncalibrated; learning, errors, fatigue, IME operations, and developer productivity were not measured. These results support prototype selection and prospective testing, rather than claims of demonstrated typing-speed improvement.

Keywords: keyboard layout; Japanese romanization; simulated annealing; punctuation pairs; Shift modeling; reproducibility

## 1. Introduction

A keyboard layout must serve sequences of actions, not merely place frequent letters near the home row. Japanese romanized input, English prose, and source code place different demands on the same physical device. A Japanese-oriented design can benefit from consonant–vowel alternation, whereas English contains frequent consonant sequences and source code adds brackets, operators, capitalization, and indentation. This study treats these demands jointly while retaining the conventional 1–0 digit order.

Existing alternatives provide useful design baselines. Colemak emphasizes, among other constraints, reduction of same-finger sequences; Workman explicitly discusses directional and lateral reach rather than home-row occupancy alone [5,6]. The Onishi layout separates vowels and consonants and was developed using an Aozora Bunko-derived Japanese corpus [4]. Its published author-side statistics are not directly comparable with the smaller, differently normalized inputs used here. We therefore re-evaluate existing layouts under the same present geometry, character mapping, and objective rather than transfer scores from external websites.

Corpus-based movement optimization and stochastic layout search have precedents in virtual-keyboard research [7]. However, stylus-based movement models are not direct measurements of ten-finger touch typing. Overlapping actions, preparation, skill, and correction behavior limit any simple additive model [3]. Accordingly, we call the present computation a motor-time surrogate and retain a separate KLA-inspired structural score [2]. We do not identify either quantity with observed words per minute.

The central design question is whether explicit rules for related symbols can be imposed without forfeiting most of the efficiency found by free optimization. The contributions are an auditable sequence of design stages, an explicit Shift-aware surrogate, a constrained search over both symbol layers, and a fully specified final candidate. The final adoption decision is a project decision; it does not substitute for an experimental validation of learnability.

## 2. Study design and provenance

### 2.1. Development sequence

The project progressed from small Japanese tasks and distance-based comparisons to bilingual and source-code benchmarks, modern-style Japanese diagnostics, a finger-by-row model, expanded symbol layers, and finally mnemonic pair constraints. Table 1 separates these stages so that early results are not mistaken for directly comparable final-model measurements. The present report is based on repository snapshot ec596b262328ce66629c4f56874dffb364395e7d [1]. The underlying F4/F5 model and fixed candidate layouts were not re-optimized for this manuscript.

{{table:history}}

The initial benchmark itself used six authored Japanese tasks, not Aozora Bunko. Earlier discussion of Aozora Bunko concerned external motivation and the Onishi baseline. This distinction matters because the initial tasks contained only 10 long-vowel marks in 2,749 romanized input characters (0.364%). A later deliberately loanword-rich set contained 118 such marks in 2,733 characters (4.318%). Neither authored set estimates population-wide Japanese frequencies.

### 2.2. Corpus construction and an audited count correction

The three-domain synthetic corpus was designed from 144 source sentences and assembled into 48 composite documents, totaling 23,483 romanized characters with reuse. Inspection of the documents actually stored in the repository recovers 142 distinct source sentences: two authored sentences were not represented in those composites. The final frozen statistics therefore contain 94 training sentences, 24 validation sentences, and 24 test sentences—not the nominal 96/24/24 previously stated in descriptive material. Character totals and all published numerical scores are unchanged. The correction is derived both from source-sentence identifiers and from the first-character counts in the stored n-gram statistics.

Sentences were divided within topic by source index; this is a deterministic split, not a random sample of contemporary Japanese. The three domains are everyday life, business communication, and technology. The final splits do not share identical sentences, but they share authoring style and topic construction. Earlier composite-document splits reused source sentences and are not treated as independent evidence. Table 2 records the actual final input sizes.

{{table:corpus}}

English consists of six authored passages: four for training and two for testing. Final code evaluation covers Python, JavaScript, TypeScript, Go, C, C++, and Java, with one training and one different test file per language. Sources include Requests/CPython, noVNC, MathJax, the Go standard library, Biopython, sharp, and LibreOffice Java examples. Sampling windows and source/sample SHA-256 hashes are archived. An earlier eight-language external check included Rust, but it is distinct from the final seven-language F4/F5 test set and is not pooled into the final scores.

### 2.3. Input representation and information leakage

Japanese is evaluated as fixed romanized input strings, not as displayed kanji/kana characters. The long-vowel mark U+30FC is retained as ASCII hyphen, and a fixed spelling policy uses si/ti/tu/hu/zi with specified extensions for palatalized and loanword sounds. English capitalization and code punctuation are preserved. Supported inputs are printable ASCII, tab, and line feed. Non-supported characters are filtered, and transitions are counted within documents only; no artificial bigram is added between documents. Space, Enter, and Tab remain fixed.

The final Japanese test set has 1,301 input characters; English has 1,208; pooled code has 76,876. These are small or domain-specific samples. The loanword-rich diagnostic set and several other test results had already been inspected during earlier project decisions. Thus, although search candidates were selected using training objectives, these evaluations are not fresh blind tests. The stored validation split is reported for inspection, not used as a separately demonstrated model-selection procedure.

## 3. Computational methods

### 3.1. Physical geometry and action states

The final geometry approximates a staggered JIS keyboard [9]: 13 number-row keys, 12 upper-row keys, 12 home-row keys, and 11 lower-row keys. Row coordinates in key-pitch units are (c−0.5, 2), (c, 1), (c+0.22, 0), and (c+0.47, −1), respectively. These are schematic coordinates, not measurements of the user's device. A pitch of 19.05 mm is used when reporting travel distance. The printed yen key is fixed but outside the ASCII evaluation alphabet. A blank Shift face is not an output character.

Each input character maps to a physical key and a base/Shift layer. Lowercase letters stay on unshifted non-number-row keys and their uppercase equivalents remain on the same shifted key. Digits 1–0 cannot move. All five vowels are constrained to the left hand in newly searched F4/F5 layouts, and the hyphen must remain unshifted. Existing baselines are adapted to the common JIS-like geometry; they are not claimed to be faithful firmware implementations of every original national variant.

### 3.2. Motor-time surrogate

Let u_i, g_ij, f_i, and l_i denote character counts, within-document bigram counts, and document-start and document-end counts. For the action assigned to character i, p(i), the total modeled time is

{{equation:time}}

The per-action term includes a 118 ms base interval, a location surcharge, and 8 ms of coordination for a shifted character. For consecutive different keys operated by the same finger, the transition surcharge is 36 + 56 log₂(1+d) + 6d ms, where d is direct key-to-key distance in pitch units. Repeating one physical key costs 23 ms beyond the base interval. For different fingers, the surcharge is 19h_next + 9h_previous ms, plus 8 ms for the same hand, where h is distance from the finger's home key. This is an additive approximation; the reduced return coefficient is not a full simulation of parallel movement.

{{table:costs}}

The row penalties encode the user's reported discomfort: left pinky/upper +18 ms, left ring/lower +18 ms, left middle/lower +12 ms, right middle/lower +9 ms, right ring/lower +9 ms, and right pinky/upper +7 ms. These are uncalibrated hypotheses, not measured effect sizes. The implementation additionally assigns 12 ms to number-row actions; inward offsets cost 7 ms for index fingers and 5 ms otherwise, and outward offsets cost 10 ms for pinkies and 6 ms otherwise. A same-finger upper-to-lower or lower-to-upper transition adds 7 ms; arrival into inward/outward zones adds 4/6 ms. The zone threshold is a signed horizontal displacement exceeding 0.4 pitch from the finger's home position.

Shift is assigned to the opposite-hand pinky. Starting a Shift run adds 30 ms plus 19 ms per pitch of modifier reach; ending the run adds 9 ms per pitch of return. The same Shift can remain held for adjacent compatible actions. Changing Shift side releases one and engages the other. If a boundary action uses a pinky that conflicts with the neighboring modifier state, a further 12 ms is added per applicable boundary condition. These assumptions account for more than a fixed per-capital surcharge, but still do not represent full multi-finger scheduling, key travel, or variable motor preparation.

### 3.3. Training objective and constraints

For F5-Pair, the training weights are 0.18/0.18/0.19/0.23/0.22 for everyday Japanese, business Japanese, technical Japanese, English, and code. Thus Japanese collectively receives 55%. Each domain is normalized by its input length, and code receives equal weight per training language, rather than weight proportional to file size. Code-heavy and Japanese-heavy variants use the profiles in Table 4.

{{table:weights}}

The training objective adds soft regularization to normalized motor time: 3 ms-equivalent per non-home-row fraction, 12 per different-key same-finger fraction, 10(L−0.5)² for left-hand use L, and 160Σ_f max(0, ℓ_f−cap_f)² for finger loads. Caps from left pinky through right pinky are 0.12, 0.16, 0.20, 0.28, 0.28, 0.20, 0.16, and 0.12. Thumb use is excluded from that eight-finger regularizer. These terms affect candidate selection, but they are not included in reported motor time or speed gain.

Nine ordered symbol pairs are constrained: parentheses, square brackets, braces, angle brackets, semicolon/colon, single/double quotation marks, comma/period, hyphen/underscore, and slash/backslash. In the mixed condition, each pair must occupy adjacent keys on the same row and layer in the stated left-to-right order, or one physical key with the first member on base and the second on Shift. No cognitive-time bonus is invented. Shift-only variants require all pairs on the same key; Grid variants couple () with <> and [] with {} across two adjacent base/Shift keys, while placing the other pairs on single keys.

### 3.4. Search and independent structural scoring

F4 used ten profile/constraint conditions, 64 starts each, and 100,000 proposals per start. F5 used six conditions at the same per-condition budget. The F5 proposal mixture comprised 48% whole-key swaps, 14% Shift-face swaps, 10% base/Shift symbol exchanges, and 28% pair/block relocations. Feasibility was checked after each move. Except for the initial seed run, starts were randomized by 1,200 feasible-move attempts from a fixed seed layout; these starts are not uniform samples of all feasible layouts.

The annealing temperature decreased geometrically from 1.8 to 0.001 in objective units. An uphill change ΔE was accepted with probability exp(−ΔE/T), followed by descent over the implemented legal neighborhoods. Fixed seeds and restart logs are archived. The search budget is not a count of unique layouts and does not prove global optimality. A separate, restricted enumeration of all 10! = 3,628,800 permutations on the QWERTY digit-row Shift faces supplies an exact optimum only within that restricted subproblem [1,8].

For an independent structural view, we compute KLA-main as a Patorjk-inspired approximation [2]:

{{equation:kla}}

D = max(0, (4−d̄)/4), with d̄ the modeled main-key travel in cm per input character; U = Σ_f w_f min(100ℓ_f,20)/260; F = max(0, (10−100s_f/N)/10); and H = max(0, (50−100s_h/N)/50). Here s_f and s_h count different-key same-finger and same-hand transitions, excluding thumb hand comparisons as implemented. Finger weights are 0.5/1/4/2/2/4/1/0.5/0.5, including the thumb. The score excludes modifier-pinky motion, even though the time surrogate includes it. It is neither the official web application's direct output nor a validated speed metric. Pooled code KLA is recomputed from pooled counts, not averaged across language scores.

## 4. Results

### 4.1. Final F5-Pair specification

Figure 1 shows the adopted candidate, whose internal identifier is F5-Balance-mixed. Table 5 gives the exact pair relationships. Seven pairs are horizontal neighbors and two share a base/Shift key. In particular, ;/: and slash/backslash share keys; parentheses are neighboring unshifted keys. The hyphen is on upper-row column 4, operated by the left index finger, while underscore occupies the next column. This outcome does not imply that left-hand hyphen placement is universally preferable.

{{figure:layout}}

{{table:pairs}}

### 4.2. Modeled time and KLA-main

Table 6 reports comparable final-model speed gains, defined as 100(T_QWERTY/T_layout−1). A 10% speed gain means a time ratio of 1/1.10, not a 10% time saving. F5-Pair reaches 16.00% on Japanese test sentences, 15.99% on loanword-rich Japanese, 10.81% on English, and 10.61% on pooled code. The code time is 149.109 ms per character versus 148.879 ms for F4-Balance: a 0.154% relative time penalty, or approximately 0.230 ms per character. The F4-Balance candidate satisfies none of the nine new strict pair rules, whereas F5-Pair satisfies all nine.

{{table:speed}}

KLA-main does not reproduce the same ranking (Table 7). F5-Pair scores 72.93 on English and 62.00 on code; F5-Code is slightly higher on code at 62.36. Onishi remains strong on loanword-rich Japanese at 73.22, above F5-Pair at 70.64. Such disagreement is expected because the time surrogate includes finger-specific location and Shift costs, while KLA-main uses a different weighted structure. No single headline score should be interpreted as a universal ranking.

{{table:kla_selected}}

Per-language code KLA-main for F5-Pair ranges from 59.76 for C to 63.31 for TypeScript (Table 8). The corpus-level score is not the mean of these seven numbers. Complete 30-layout comparisons are retained in Appendices A and B and in the machine-readable results.

{{table:code_languages}}

### 4.3. Long-vowel mark and symbol-layer ablations

In the loanword-rich diagnostic set, all 118 long-vowel marks occur in a vowel–hyphen–consonant sequence. Moving the hyphen from the vowel hand to the consonant hand changes L–L–R into L–R–R, preserving one hand alternation across the two transitions. Thus, the preceding vowel alone is insufficient to determine the best side. With vowels fixed left and whole layouts re-optimized under the Japanese profile, left-hyphen and right-hyphen solutions yield 131.839 and 132.226 ms per character, respectively; KLA-main reverses their order, at 70.14 and 72.13. These are coupled layout comparisons, not isolated causal effects of one key.

In separate F4 ablations, changing only the Shift symbols of F3-Balance raises the code gain from 6.83% to 7.92%; allowing both symbol layers to change with letters fixed raises it to 9.71%. Full F4-Code optimization reaches 11.47%. The corresponding fraction of shifted code characters falls from 13.59% for F3-Balance to 9.31% with both symbol layers optimized. By contrast, exact digit-row Shift-only optimization improves code speed by only about 0.082%. These results locate most of the modeled opportunity in symbol-layer placement, not merely in permuting symbols above fixed digits.

### 4.4. Search behavior and sensitivity

F4 recorded 64,000,000 proposals, 29,373,513 feasible evaluations, and 4,990,936 local-polish evaluations. F5 recorded 38,400,000 proposals, 14,085,600 feasible evaluations, and 1,893,732 polish evaluations. Figure 2 displays restart objective distributions for comparable Balance-profile conditions. Their spread describes stochastic optimization, not participant variability or a confidence interval for human performance. Constrained and unconstrained searches can find different local minima; a constrained run occasionally outperforming a broader search is evidence of finite-search limitations, not a contradiction in the feasible sets.

{{figure:restarts}}

Across the six archived combinations of row, lateral, and Shift scaling, F5-Pair remains above the corresponding QWERTY baseline: 14.72–17.26% for Japanese test, 10.07–11.56% for English, and 9.60–11.94% for code. These scenario ranges are not statistical uncertainty intervals. They sample only a small set of assumed coefficients and do not establish robustness to all plausible biomechanical models, corpora, or users.

## 5. Discussion and adoption decision

The main outcome is not that F5-Pair maximizes every score. It retains nearly all of the balanced F4 candidate's modeled efficiency while enforcing consistent locations for related symbols. F5-Code is a reasonable alternative when source code dominates; F5-Shift and F5-Grid provide stronger uniformity but require more Shift operations for some common symbols. A reduction in mnemonic complexity is a design rationale, not an observed reduction in learning time.

The project owner selected F5-Pair for the GALACTYPE typing game. This manuscript records that decision and freezes the mapping; it does not claim that game integration, operating-system remapping, or firmware deployment has already been implemented. Implementation should preserve the distinction between physical key events, produced characters, Shift state, and IME composition. A visible base/Shift diagram and pair-based practice tasks can expose the rules without changing the benchmark definition. Shortcut handling and existing QWERTY proficiency require separate decisions because the adopted F5-Pair does not preserve all familiar shortcut positions.

A prospective evaluation should measure inter-keystroke intervals, uncorrected and corrected errors, learning curves, and retention using previously unseen Japanese, English, and code tasks. Within-person comparisons require counterbalanced training and careful treatment of transfer and carryover. The same hardware, input rules, accuracy criteria, and editing environment should be used. Finger/row coefficients should be fitted on training observations and tested on independent sessions; results should be reported separately for novice acquisition and practiced performance. This is a proposed validation program, not part of the completed study.

## 6. Limitations

First, all millisecond coefficients are hypotheses. Finger length, handedness, switches, stagger, posture, reach strategy, and simultaneous movement can alter performance. The additive formulation and its logarithmic same-finger term should not be presented as an experimentally established Fitts-law model of ten-finger typing [3]. Second, synthetic Japanese and short authored English are not representative language samples. Sentence-disjoint splitting removes exact sentence reuse, not stylistic or topic dependence. The deterministic source-index split may introduce additional structure.

Third, code samples include comments, spaces, and indentation; they model transcription rather than editing with completion, auto-pairing, navigation, or reasoning. The final seven-language set does not establish final-model Rust performance. Fourth, previously examined test and diagnostic material weakens claims of independent generalization. We provide descriptive comparisons, not p-values or participant-level confidence intervals. Fifth, pair constraints are only a structural proxy for memorability. Layout search does not quantify fatigue, strain, accessibility, or health benefits. Sixth, no search over the full space was exhaustive; the 10! result applies only to digit-row Shift faces. Finally, existing layouts are evaluated as common-geometry adaptations, so national variants and original implementation conventions remain outside the comparison.

## 7. Reproducibility and conclusion

The pinned repository snapshot [1] contains frozen corpus statistics, full key-layer definitions, candidate seeds, restart histories, score tables, diagrams, and tests. Recalculation for this manuscript reproduced all 768 F4 and 736 F5 layout/group cases without changing the frozen scores. The final adopted identifier is F5-Balance-mixed, displayed as F5-Pair. The input-statistics archive has SHA-256 311a34d5d6c1bc83bc56f83288617877beedee224edc1d06de4c676fc91d7b14. Appendix C provides commands and the complete base/Shift specification.

NOVA F5-Pair demonstrates that pair-consistent punctuation placement can be combined with a small modeled efficiency cost. Its selection is justified as an auditable prototype compromise across Japanese romanized input, English, and code. Human speed, learning, and comfort remain open empirical questions. The appropriate next step is prospective validation, not a claim that a universally best keyboard has been found.

## Declarations

This work reports computational experiments; no human-participant timing, error, physiological, or health measurements were collected. AI assistance was used for corpus generation, code development, analysis support, and manuscript drafting. Synthetic text is explicitly labeled. Source-code bodies from upstream projects are not redistributed in the benchmark archive; source references, hashes, and aggregate counts are provided. The manuscript is a research report, not a peer-reviewed publication. Author affiliation, funding, and conflict-of-interest declarations have not been supplied and must be completed before journal submission.

## References

{{references}}

[[PAGEBREAK]]
## Appendix A. All-layout KLA-main comparison

All values below are recomputed under the same final F4/F5 geometry and KLA-main approximation. Historical scores calculated under different models must not be substituted. Names are shortened only for display; full identifiers are retained in the CSV. Values are rounded to two decimals, so apparent ties may conceal small numerical differences. Source: results/kla_all.csv at snapshot [1].

{{table:kla_all}}

[[PAGEBREAK]]
## Appendix B. Domain-specific KLA-main comparisons

These are descriptive scores, not independent replications. Code-language scores are not averaged to form the pooled code score. The full 420-value matrix comprises 30 layouts and 14 evaluation groups.

{{table:kla_jp_domains}}

[[PAGEBREAK]]
### Appendix B continued. Seven code languages

{{table:kla_code_all}}

[[PAGEBREAK]]
## Appendix C. Fixed mapping and reproduction

The table lists each physical row from left to right, including the number row. The symbol ∅ denotes a face with no output; the hyphen character itself remains an ordinary output. The yen legend is outside the evaluated ASCII alphabet. Space, Tab, Enter, and both Shift keys are unchanged. The authoritative implementation-neutral mapping is layouts/f5/full_layers.json, layout F5-Pair.

{{table:mapping}}

Recalculate fixed scores without repeating the expensive search:

{{code:reproduce}}

A full search is a separate operation and should be run on a working branch because it regenerates candidates and results. The manuscript build checks recorded source hashes before creating tables. The project corpus audit in this paper corrects only a descriptive sentence count (142 present; 94 training); it does not alter corpus bytes, optimization, or performance values.
