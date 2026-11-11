# 56단계: 기존 C++·ViT 실행 원본 보관

상태: **사용자 ZIP 수신·무결성 확인·독립 감사 완료**. 2026-11-12에 제출한112파일 ZIP을 받아 두 모델SHA, C++ 원시72회와24개 표시값, ViT60영역과30개 이미지 표시값을 대조했습니다. 모두 일치합니다. [감사·오류 분석](USER_RESEARCH_AUDIT.md). 다음 사용자 작업은 [57단계 모듈 작성](STEP_57.md)입니다. 아래 명령은 완료한 단계의 재현 안내이며 다시 실행할 필요가 없습니다.

Codespaces 터미널에서 아래 블록을 통째로 실행하세요. 시작 폴더는 `/workspaces/pathology-edge`이며, 기존 두 실행 폴더를 새 `work/research-export.XXXXXX/`의ZIP과manifest로 보관하는 명령입니다. 저장소 갱신·패키지 설치·기존 코드/모델 덮어쓰기가 없습니다. 알려진 두 모델SHA와 원본 보존 기록·112개 안팎의 파일·원시 시간값을 검사합니다.

```bash
(
set -e
cd /workspaces/pathology-edge
PATHOLOGY_EVIDENCE_DIR="$(mktemp -d "$PWD/work/research-export.XXXXXX")"
curl -fsSL --retry 2 https://raw.githubusercontent.com/sokldjs554/pathology-edge/a63c49990b14e2b6a01ec57f7fa1fcaad0c40bd3/scripts/export_research_evidence.py -o "$PATHOLOGY_EVIDENCE_DIR/export.py"
python "$PATHOLOGY_EVIDENCE_DIR/export.py" \
  --cpp-run work/my-cpp-review.nd9wyi24 \
  --vit-run work/vit-source.tdbTh0/work/my-cnn-vit.4de29faebea2 \
  --expected-cnn-sha eeb89d657e8242547723bd7f344dcddd15f4cf6f87f6942b428c164901baf609 \
  --expected-vit-sha 469e471fe8082d490754c54cf71a1ca537b8aeb1e8e70bb0a553b8190922027f \
  --output "$PATHOLOGY_EVIDENCE_DIR/research-evidence.zip"
)
```

성공하면 마지막JSON에 `integrity_verified: true`, 두 모델SHA, `bundle` 경로가 나옵니다. `scientific_audit_performed: false`가 정상입니다. 보관 단계는 파일 무결성·기록의 일관성 검사이고, 정답과의 지표 재계산은 원본을 받은 다음 별도로 수행합니다. 출력 전체를 보내 주세요.

원본 전달은 같은 단계의 후속입니다. Codespaces 왼쪽 Explorer에서 출력된경로의 `research-evidence.zip`을 우클릭→Download한 뒤 채팅에 첨부하면 됩니다. 파일명 뒤 `.manifest.json`은 옆에 별도로 생기지만 같은 내용이ZIP 안에도 있습니다. 아카이브에는 실험 코드·모델·기록·확률맵이 들어가며 데이터 이미지나 환경변수/인증정보는 수집하지 않습니다. 원본 폴더는 그대로 둡니다.

폴더가 없거나 `Evidence rejected:`가 나오면 해당 오류를 보내 주세요. 이 경우 새 학습을 시작하거나 기존 결과를 삭제하지 않습니다. 성공JSON만 받은 상태와 실제ZIP을 받아 독립 감사한 상태를 구분해서 기록합니다.

[네 가지 보완의 전체 상태](RESEARCH_FOLLOWUP.md).
