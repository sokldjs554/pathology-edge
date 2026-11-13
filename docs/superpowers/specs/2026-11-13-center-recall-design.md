# Center recall diagnosis and decoding comparison

The user authorized the next improvement after U95: identify why recall fell and
positive-fraction errors sometimes rose, then apply a justified correction.
Use the existing isolated `feat/auto-ki67` worktree and fixed three detector seeds.

## Approach

First replay the 227 validation images (four cases) with existing frozen weights.
For each missed reference center distinguish: no raw local peak within 6px;
nearby peaks all below threshold; nearby passing peaks all suppressed by minimum
distance; or a remaining peak assigned to another reference by one-to-one matching.
These are decoder-stage observations, not biological causes or proof of absence
of a cell. Report positive/negative tumor and other classes separately.

Compare decoding configurations with unchanged weights before considering more
training. This isolates score/distance effects. Retraining or classifier changes
would confound that comparison and are outside this increment.
The expanded threshold grid is fixed before the replay: .01,.02,.03,.05,.075,
.1,.2,.3,.5; distances4,6,8. Select maximum validation case-macro localization F1
subject to validation case-macro recall and pooled positive/negative localization
recalls at least the original LoG baseline. Ties: recall, higher threshold,
larger distance. If infeasible, report no feasible solution; never silently relax.
All four classifiers remain fixed and are reported, without ratio-based selection.

Lock protocol, source, inputs, configurations and weights before any test/external
re-evaluation. All three seeds remain visible. Reused407/BCData133 results are
re-evaluations, not fresh external validation. New decisions use validation only;
the experiment is motivated by previously observed failures and is exploratory.

## Evidence and delivery

Preserve old experiments, ZIPs and seven learner files. Add meaningful synthetic
tests, stage counts, class count/error decomposition, complete comparison results,
and an actual-image review artifact with downloadable evidence. No claim of clinical,
full-WSI, automatic improvement in every metric, or user execution. One user visual
review remains pending until their reply. If recall improvement trades off F1 or
ratio accuracy, retain both modes rather than replacing the existing default.
