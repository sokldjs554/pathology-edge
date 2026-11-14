# Dense supervision implementation plan

> **For agentic workers:** Use superpowers:executing-plans natively. One fresh whole-task reviewer at completion; no implementer delegation.

**Goal:** Test a single denser loss change against fixed Ki67 detector acceptance criteria, then execute eligible actual-center/heldout paths.
**Architecture:** Saved-peak diagnosis → train-only three-loss fit comparison → deterministic loss decision → three fresh GNwidth16 models → unchanged conditional classifier/external stages. Prior hash-bound source stays immutable.
**Tech Stack:** Existing CPU PyTorch/NumPy/SciPy/Pillow and standalone HTML.
**Spec:** docs/superpowers/specs/2026-11-14-ki67-supervision-design.md

## Global Constraints
Native224RGB,Gaussian sigma2radius6,train696/validation227,seed17/18/19,24epochs,Adam.001,batch8,1thread,max3workers. Twelve original thresholds and distances4/6/8;match6. All original FP/FN/recall floors unchanged. All3selections before holdouts, all3denominator. Seven learner sources/history/dist unchanged. Test407/BCData133 are reused; DeepLIIF597 all-cell staining/formatprobeexcluded. No clinical/wholeWSI/default-model claims.

## Review Focus
1. Soft targets/empty or full targets/extreme logits must yield finite correctly directed gradients, not binary-only or pixel-pooled loss.
2. A fitting diagnostic with wrong membership, changed initialization, nonfinite metrics or heldout exposure must not select an objective.
3. Three distinct seed jobs must complete and lock; duplicated/missing seeds, altered loss/source/input/control hashes cannot qualify.
4. Historical A adoption baseline and normalized24epoch control cannot be confused; old checkpoints and source must remain verifiable.
5. Eligible automatic classification uses actual centers; no missing-case MAE advantage, ineligible inference or external-driven tuning.

### Task1: loss and diagnostic decision
Files:src/pathology_edge/ki67_supervision.py;tests/test_ki67_supervision.py;scripts/audit_ki67_supervision_spike.py.
Interfaces:supervision_loss(logits,target,mode)->scalar;choose_loss(reports:dict)->dict(selected_loss,best_by_mode,criteria);audit_spike(root)->report.
- [x] RED known MSE(.5 binary/.3333soft) and BCE(2log2), per-image mean, empty/full gradients, gradcheck, invalidshape/dtype/nonfinite/range/mode; decision .03 boundary, positive-recall rejection,tie,missingarm,heldout120/0 contract,forgedbest.
- [x] Implement exact spec formulas and deterministic choice; GREEN focused tests and original center regression.
- [x] Independently replay three fitting checkpoints on exact120trainimages, originalpoint/mask hashes, full36configs, savedbest and initialization equality. Freeze decision and audit hashes before validation training. If neither loss qualifies, stop main study and deliver diagnostic evidence honestly.

### Task2: frozen three-seed study
Files:src/pathology_edge/ki67_supervision_experiment.py;scripts/run_ki67_supervision.py;tests/test_ki67_supervision_experiment.py;scripts/audit_ki67_supervision.py.
Interfaces:prepare(normalized_root,diagnostic_root,output);checked(root,selected=False);job_name(width,seed);primary_models(selection);fit_worker(root,width,seed);seal(root). WIDTHS=(16,),same infer_peaks/model class; no old source edits.
- [ ] RED complete3seed/missing/duplicate/wrongwidth,decision/loss/protocol/control/source drift,partialseal,initialtensorcontrol equality,old-gates no relaxation; implement and GREEN.
- [ ] Commit frozen source before prepare; execute three24epoch workers once, same initial tensors as existing normalized controls, store2592trials/checkpoints/optimizer/RNG. Audit independent fullgrid/GT/checkpoint replays and matched control provenance. Lock all3.

### Task3: conditional pipeline and delivery
Files:src/pathology_edge/ki67_supervision_pipeline.py;scripts/run_ki67_supervision_pipeline.py;scripts/run_ki67_supervision_deepliif.py;scripts/audit_ki67_supervision_deepliif.py;scripts/export_ki67_supervision_review.py;tests/test_ki67_supervision_pipeline.py;docs/KI67_SUPERVISION.md;docs/STEP_93.md;newartifacts.
Interfaces:select_classifiers(root);checked_pipeline(root);evaluate(root,external=False), same frozenclassifier/casecoverage contracts as normalized pipeline; new imports/schema only for immutable prior evidence. External pureadapter reused unchanged.
- [ ] RED three-model bindings,zeroeligible no-inference and all3denom,unknown/wrongclassifierlock,actualcenter output/coverage assertions; implement and GREEN with existing pipeline/external tests.
- [ ] Conditional select→internal→BCData→DeepLIIF stages; independent actual-center/metric audits if executed, explicit no-run if noeligible. No external tuning.
- [ ] Actual browser six improved/worsened examples with exactnumbers/overlays/sameRGB at1440/390; captures, report/ZIP and honest limitations/userpending. Clean CI, fresh final reviewer; publish draftbranch and verify immutable downloads/exact-head CI.

## Executed outcome
Task1completed:35newtests,360training-imagecheckpointreplays/108configs. Neither objective qualifies; Task2 and conditional Task3performance paths were intentionally not implemented/executed. Separate smoothing diagnostic audited120checkpoint-images/600maps/180configs; no sigma qualifies. No new model adopted, no heldout inference, no freshUI/browser claim. Delivery of rejected-hypothesis report/evidence and final review continues; existing user U106 unchanged.
