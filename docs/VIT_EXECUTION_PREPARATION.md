# ViT 비교 실행 준비

상태: **준비 완료 / [53단계](STEP_53.md) 실행 안내로 연결**. [52단계](STEP_52.md)의 C++ 측정 범위 해석을 확인했습니다. 지금 실행할 때는 원래 체크아웃 전후 검사까지 포함한53단계의 최종 명령을 사용합니다. 아래는 초기 준비 자료이며 별도로 반복 실행하지 않습니다.

## 실행할 비교

고정 소스 `917038feb5c80b1c7175d94ba44c208d9940220d`에서 TinyUNet과 SmallViTSegmenter를 한 번씩 학습합니다. 양쪽 모두 seed20261113, 학습33장·검증10장,128px crop,16epochs×20steps, BCE+기존 사용자 soft Dice를 사용합니다. 테스트7장은 무결성 해시만 읽으며 추론·평가하지 않습니다. [설계·참고 결과](CPP_VIT_COMPARISON.md).

현재 코드·실험을 유지하려고 별도 detached worktree에 고정 소스를 받습니다. 원래 작업 폴더의 `learner_wsi.py` 등 수정 파일을 복구·stash·덮어쓰지 않습니다. 기존 Python 환경을 사용하며 새 패키지 설치와 C++ 재빌드는 필요하지 않습니다. 새 체크아웃에는 저장소에 반영된 사용자 손실 함수가 들어가며, 원본 폴더의 미커밋 변경을 자동 복사하지 않습니다.

## 후속 안내에서 사용할 순서

1. 기존 저장소의 commit/status와 데이터 manifest 유무를 확인합니다.
2. `work/vit-source.*`에 새 detached worktree를 만들고 코드 SHA를 확인합니다. `git fetch`와 `git worktree add`는 Git 메타데이터를 추가하지만 원래 작업 파일과 체크아웃 브랜치를 바꾸지 않습니다.
3. 새 체크아웃의 실행기에 원래 `data`의 절대 경로를 전달합니다. 실행기는 소스 스냅샷을 만들고 두 모델을 별도 프로세스에서 순차 학습합니다.
4. 새 `work/my-cnn-vit.*`의 `RUN.txt`, 로그와 SUMMARY를 확인합니다. 터미널 변수가 없어져도 경로 기록으로 복구합니다. 실패한 폴더는 보존하며 부분 결과를 성공으로 해석하지 않습니다.

아래는 준비 당시 명령 틀입니다. 최종 실행 지시는 [53단계](STEP_53.md)에 있습니다. Codespaces의 `/workspaces/pathology-edge`에서 시작하며 각 단계가 성공해야 다음 명령을 실행합니다.

```bash
cd /workspaces/pathology-edge &&
mkdir -p work &&
PATHOLOGY_VIT_SOURCE="$(mktemp -d /workspaces/pathology-edge/work/vit-source.XXXXXX)" &&
git fetch origin 917038feb5c80b1c7175d94ba44c208d9940220d &&
git worktree add --detach "$PATHOLOGY_VIT_SOURCE" 917038feb5c80b1c7175d94ba44c208d9940220d &&
mkdir -p "$PATHOLOGY_VIT_SOURCE/work" &&
printf '%s\n' "$PATHOLOGY_VIT_SOURCE" > "$PATHOLOGY_VIT_SOURCE/work/SOURCE_PATH.txt" &&
python "$PATHOLOGY_VIT_SOURCE/scripts/run_model_comparison.py" \
  --repo "$PATHOLOGY_VIT_SOURCE" \
  --data /workspaces/pathology-edge/data
```

`work/SOURCE_PATH.txt`는 Git에서 제외하는 새 작업 폴더에 저장합니다. 새 실행기는 source snapshot의 `PYTHONPATH`를 사용하므로 기존 editable install이 원래 폴더를 가리켜도 학습 소스가 섞이지 않습니다.

학습 후 모델별16개 epoch, checkpoint 선택, 저장 확률맵의60개 영역 지표, 모델·소스·데이터 해시, 두 모델의 crop/증강 순서와 실행 전후 체크아웃 상태를 확인합니다. 실행기의 원본 보존 검사는 `--repo`로 지정한 새 체크아웃을 대상으로 하므로, 후속 안내에서는 기존 체크아웃의 전후 상태도 별도로 확인합니다.

사용자 학습 결과는 아직 없습니다. 참고 실행의 점수나 시간과 정확히 일치해야 하는 과제가 아니며, 환경 차이와 검증 데이터 선택이라는 한계를 함께 검토합니다.
