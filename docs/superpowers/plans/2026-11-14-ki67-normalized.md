# Normalized detector and prospective transfer implementation plan

> **For agentic workers:** Use superpowers:executing-plans natively; one fresh final reviewer. Existing isolated feat/auto-ki67 worktree.

**Goal:** Execute authorized performance items1–3 with unchanged acceptance criteria and honest negative results.
**Architecture:** Train-only diagnostic→normalized heatmapdetector primarywidth16/ablationwidth4→frozen actual-center classifiers→locked internal/BCData/newDeepLIIF evaluation.
**Tech Stack:** Existing CPU PyTorch/NumPy/SciPy/Pillow; HTTP ranges; standaloneHTML.
**Spec:** docs/superpowers/specs/2026-11-14-ki67-normalized-design.md

## Global Constraints
Seeds17/18/19,train696/val227,24epochs,Adam.001,batch8,1thread/worker,max4workers. SameGaussian/focal/augmentation. Fixed12cutoffs×3spacings. All6lock beforeholdout. ExactoldFPFN/recallfloors;no test/externaltuning. Primarywidth16 only;all3denominator. Sevenlearnerfiles/demo/historyunchanged. DeepLIIF597excludingpre-inspectedformatprobe,strictreference/range/hashchecks;all-cellstainnot tumorLI. Usernewreviewpending.

## Review Focus
1. Primary/ablation or seed confusion must not adopt a posthoc better arm;all6locks and threeprimarydenominators enforced.
2. Native centers and GroupNorm shape behavior;no mislabeled resized/GT-supplied inference or mismatched checkpoint constructor.
3. Classifier selection cannot win by dropping undefined fractions or using external outcome;authoritativeimages/GT and actualnewcenter classification replayed.
4. External greenboundary masks/mixedcomponents/nativeXY/CRC and failurehandling;positivefractionisallcells,nottumor,noiseandbordercountsvisible.
5. Everyhash/source/selection/input mutation rejected;newsourceisolatedfromoldfrozenruns;wronggroup/duplicateimage never silently scored.

### Task1: normalized detector and frozen workers
Files:src/pathology_edge/ki67_normalized_centers.py,src/pathology_edge/ki67_normalized_experiment.py,scripts/run_ki67_normalized.py,tests/test_ki67_normalized.py.
Interfaces:NormalizedCenterDetector(width=16);prepare(prior,output);checked(root,selected=False);fit_worker(root,width,seed);seal(root). Reusecenter_target/loss,configuration_trials,choose_refit,float64retain/summarize. OriginalAcheckedfromweights;storewidth-seedsubfolders.
- [ ] RED model shape/nativeRGB,parameter/checkpointwidth,sixdistinctjobs/primarywidth16/partialseal/hashdrift;implement;GREENwitholdcenter/unionregressions.
- [ ] Commit sourcebeforeprepare;launchmax4workerjobs,eachseed/armonce;savealltrials/peaks/checkpoints;selectionsimmutable. Noresultdependenttrainingchanges.

### Task2: fixed classifiers and holdout stages
Files:src/pathology_edge/ki67_normalized_pipeline.py,scripts/audit_ki67_normalized.py,tests/test_ki67_normalized_pipeline.py.
Interfaces:select_classifiers(root);evaluate(root,external=False);audit(root). Consumeall6detectorseal;produceclassifierlock,actualpoints/classes/GTcounts,all3stability. Reuseexistingmodels/load_sample/score_external,notcachedoldcenterlabels.
- [ ] RED fixedseedclassifiermapping,NaN/coveragecandidate rejection,noeligiblezeroinference,missingseed/wrongprimaryarm,source/protocol/lockmutation;implementandGREEN.
- [ ] Selectonlyonvalidation;freezeall3classifiers;eligibleonlyreused407/133evaluation. All4sameclassifiercomparisons andprimarychosenpair.
- [ ] Independent5184trialrecount/checkpointvalidationreplay;allactualholdoutclassifiers/GT/points rebound;testskipfalsepositivesregression.

### Task3: new external reference and evaluation
Files:src/pathology_edge/ki67_deepliif.py,scripts/run_ki67_deepliif.py,tests/test_ki67_deepliif.py.
Interfaces:segmentation_centers(mask)->points,classes,audit;decode_paired_png(raw)->RGB,GT,audit;read_range(url,low,high,total);fetch_zip_entry(url,entry,total);evaluate_new(root,index,output). Adapterdoesnotacceptmodeltuning;fixed597membershipfromcentralindexandformatprobe.
- [ ] RED purecolors/greenboundary/touching/differentclasses/empty/ties/noise/border/nativegeometry;range200/wrongCRC/truncation/duplicate/membershipfailures;implement/GREEN.
- [ ] Lockexternalprotocolbeforemodelresults;onlyafterdetector/classifierlocksstreamandverify597;reportexclusionsorfailclosed,notselecteasyexamples. Bothradii6/12prespecified.
- [ ] Recountreferencesandmetricsindependently,recordhashesandallpairedseedresults without clinical/tumorLIclaims.

### Task4: reviewed delivery (not Cowork integration)
Files:scripts/export_ki67_normalized_review.py,docs/KI67_NORMALIZED.md,docs/STEP_92.md,artifacts/experiments/newdir,smallreviewZIP.
- [ ] Exportrealimproved/worsenedcases;browser1440/390,coordinates/counts/overlays,screen captures.
- [ ] FullcleanCI/focusedtests,sourcepreservation,independentfreshwhole-taskreview;fiximportantfindingswithRED→GREEN.
- [ ] Publishnewimmutableevidence/ZIP,currentdraftPR;verifydownloadSHAandexactcommitCI;usernewreviewpending,U105unchanged.
