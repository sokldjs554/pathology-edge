# Candidate correspondence filter: fixed-detector ablation

Authorized scope: next step after U91. Base b582212, isolated feat/auto-ki67 worktree.
Existing learner code, data, classifiers, detector, historical artifacts and demo stay unchanged.

## Design and limits

Keep the previous LoG detector (.10 response / 8px distance) and all four classifiers fixed.
Add a deterministic standardized logistic gate (C=1, balanced weights, lbfgs, max_iter=2000)
using the existing 40 color features plus LoG response. No class logits or GT enter inference.
Train on 696 images / 15 training cases only: positive = one-to-one match within 6px;
negative proxy = farther than 12px from every annotated center AND at least 24px from
the image edge; all other candidates ignored. The label means correspondence to released
annotations, NOT expert proof of 'not a cell'. Empty-GT training patches contribute no
negatives because their annotation coverage cannot be inferred. No randomized sampling.

Patherea paper section4/appendixA describes exhaustive four-class cell annotation inside
selected polygons (https://arxiv.org/html/2412.16425v2); the released patches do not provide
the original polygon support mask. This remains a proxy-label limitation, including inside
the 24px margin. Dataset license CC BY-NC 4.0; all negative labels are algorithm-derived.
No claim of reproducing Patherea-P2P, manual background truth or whole-slide validity.

Threshold candidates fixed before fit: 0,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95,.99,1.
Select on 227 validation images / 4 cases by case-macro localization F1, requiring each
case's recall >=90% of its ungated recall. Ties favor higher case-macro recall, then lower
threshold. Threshold0 is an explicit no-filter fallback. Equality is kept. Fixed 6px match.
No test/external annotation can enter training/selection. Gate weights, threshold, source,
data and classifier hashes locked before scoring. Reuse Patherea407 and BCData133 only
as re-evaluations, not fresh holdouts. No promise of improvement.

## Tasks / interfaces

- [ ] Task1 TDD: `ki67_candidate_filter.py` training proxy labels, 41-feature extraction,
  fit/export, finite validated scores, apply keep mask, validation-only selection. Test
  border/ignore/empty labels, finite/shape/class validation, maximum matching, fallback,
  each-case recall guard, tied threshold, train-only scaler, no-GT inference signature.
- [ ] Task2 staged runner: fresh prepare/fit/evaluate; hash-lock inputs and models;
  detailed metrics for fixed baseline vs filtered LR and all three CNNs. Independently
  recount point matches/counts/fractions; source/image-only replay. Re-evaluate external
  only using frozen filter and exact prior input identities; no parameter change afterward.
- [ ] Task3 actual before/after figure for previously reviewed107-candidate case, report
  FP/FN/recall and ratio coverage, commands and one user review step. Scoped local tests,
  full CI on fresh runner, one fresh final reviewer, publish on existing draft PR.

Review focus: proxy labels vs true non-cell truth; rejection cannot recover missed nuclei;
threshold0/empty cases and NaN weights fail safely; any per-case recall budget is validation
only; baseline prediction identity and rematching after rejection; denominator coverage;
known external exposure and no raw BCData image/point redistribution.

Pre-flight: Tasks1->2 keep-mask indexes must subset both points and every classifier's
classes without changing order; Tasks2->3 figures use exact same saved rows and threshold.
Local disk almost full; no full repository-copy tests here. Full suite runs in CI.
