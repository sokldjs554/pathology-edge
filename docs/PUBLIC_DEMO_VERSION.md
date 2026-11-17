# 공개 데모와 저장소 버전

확인 기준: **2026-11-18 KST**. 공개 주소: https://pathology-edge-lab.ykh13571.chatgpt.site/

| 구분 | 소스·상태 |
|---|---|
| 공개 UI 기준 | [`feat/linked-pathology-workbench`](https://github.com/sokldjs554/pathology-edge/tree/feat/linked-pathology-workbench), [Draft PR #3](https://github.com/sokldjs554/pathology-edge/pull/3), main 미병합 |
| 검사한 UI 스냅샷 | [`5d7d843168f0b08bb87d6da2a56468f6a1522fbe`](https://github.com/sokldjs554/pathology-edge/tree/5d7d843168f0b08bb87d6da2a56468f6a1522fbe) |
| 호스팅 버전 | 공개 버전 27, 호스팅 저장소 커밋 `d27412a8fe2f4f7df3ea6d36ef79e2c9d1600b86` |
| main | 공개 TNBC 모델·저장 결과와 기존 UI. 현재 보라색 UI와는 화면 파일이 다름 |
| 후속 자동 IHC 연구 | [`feat/auto-ki67`](https://github.com/sokldjs554/pathology-edge/tree/feat/auto-ki67), [Draft PR #2](https://github.com/sokldjs554/pathology-edge/pull/2), 공개 데모에 미적용 |

GitHub 커밋과 호스팅 커밋은 서로 다른 저장소의 식별자다. 검사에서는 UI 스냅샷과 로컬 호스팅 소스의 `dist/` 2,197개 파일을 바이트 단위로 대조해 일치를 확인했다. 이번 문서 정리는 모델·결과·화면 파일을 변경하거나 새 버전을 배포하지 않는다.

## 현재 화면 실행

새 작업 폴더에서 [RUNBOOK의 로컬 화면 명령](RUNBOOK.md#local-viewer)을 실행하면 UI 브랜치를 받는다. `main`을 clone한 화면을 현재 공개 UI와 동일하다고 설명하지 않는다. 기존 작업 폴더에 수정 파일이 있으면 강제로 checkout/reset하지 말고 별도 폴더를 사용한다.

검사한 **특정 스냅샷**이 필요하면, 새 상위 작업 폴더에서 다음을 실행한다. 현재 UI 브랜치의 최신 문서와 과거 화면 스냅샷을 구분한다.

```bash
git clone --filter=blob:none --sparse --single-branch --branch feat/linked-pathology-workbench https://github.com/sokldjs554/pathology-edge.git pathology-edge-demo-snapshot
cd pathology-edge-demo-snapshot
git sparse-checkout set dist
git checkout --detach 5d7d843168f0b08bb87d6da2a56468f6a1522fbe
python3 -m http.server 8000 --directory dist --bind 127.0.0.1
```

`http://127.0.0.1:8000/`에서 보라색 경계 비교 화면과 현재 이미지의 개선·악화 사례, `/wsi.html`에서 WSI, `/ihc.html`에서 선택 세포 결과를 확인한다. 이는 저장 결과 표시이며 새 추론은 아니다.

## 검증 범위

해당 UI의 로컬 Chromium 브라우저 테스트 88개, 추가 조작 점검 14개, JavaScript 단위 테스트 21개가 통과했다. 패널 전환·이동·확대·수치/이미지 연결·오류 재시도와 375px부터 데스크톱까지의 화면을 검사했다. 이 실행을 사용자 직접 테스트로 기록하지 않는다.

현재 검사 환경의 공개 URL 직접 요청은 HTTP 403을 반환했다. 따라서 이번 로컬 검사를 공개 사이트의 현재 브라우저 조작 성공으로 확대하지 않으며, 이 응답만으로 일반 사용자의 공개 사이트 장애라고 단정하지 않는다. 기존 배포 당시의 공개 검증은 [UI 브랜치의 보관 기록](https://github.com/sokldjs554/pathology-edge/blob/5d7d843168f0b08bb87d6da2a56468f6a1522fbe/docs/UI_WSI_BOUNDARY_ZOOM.md)과 구분한다.
