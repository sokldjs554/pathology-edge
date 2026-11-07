# 확대 후 이동 오류 수정

2026-11-07. 사용자 보고: 드래그와 트랙패드 두 손가락 스크롤 모두 이동 불가.
사용자의 브라우저 이름은 확인되지 않았습니다. 사용자 직접 검토는 대기 상태입니다.

## 재현과 원인

- 1440×1000에서 맞춤 후 `+` 한 번: 약123% 배율, canvas528×696, 영상630×630.
  기존 `clampCenter`는 영상 높이가 canvas보다 작으면 중심 y를256으로 강제했습니다.
  32px 아래로 드래그해 중심 y가 약230이 되어야 해도256에 머물렀습니다.
- 1280×800,390×844에서도 세로 이동이 고정되었습니다. 넓은 단일 영상에서는 가로 이동이 고정되었습니다.
- wheel 이벤트는 ctrl/meta와 가로 스크롤 여부를 무시하고 언제나 배율을 바꿨습니다.
  두 손가락 스크롤에 해당하는 `deltaX=24,deltaY=32`에서도 이동 대신 배율이1.23047→1.06997로 바뀌었습니다.
- 이전 검사는300% 확대에서 x/y 중 무엇이든 바뀌면 통과했습니다. 한 축만 움직이는 오류를 놓친 검사였습니다.

수정 전 [재현 실행42375243590](https://github.com/sokldjs554/pathology-edge/actions/runs/42375243590)에서
새 이동 검사6개가 Chromium과 WebKit 모두 실패했습니다. 기존 Chromium 검사12개는 통과해 검증 공백을 확인했습니다.

## 수정 범위

- 화면 중심이 원본 이미지 범위 안에 남도록 제한합니다. 영상이 한 축에 모두 들어와도 그 축의 이동을 막지 않습니다.
  가장자리에서는 여백이 보일 수 있으며, 영상 전체를 잃어버리는 이동은 제한합니다. `맞춤`으로 원위치에 돌아갑니다.
- 드래그·일반 휠·트랙패드 두 손가락 스크롤은 이동합니다.
- Ctrl/⌘+스크롤은 커서 위치를 중심으로 확대·축소합니다. `+`/`−` 버튼도 유지합니다.
- WebKit에서 canvas 높이가 실제 영상 행696px 대신 패널 전체756px로 계산되는 현상을 재현했습니다. 별도 영상 컨테이너 안에 canvas를 배치해 잘린60px와 좌표 범위 불일치를 수정했습니다.
- 화면 안내·접근성 설명에 조작 규칙을 반영했습니다.
- 모델·연구 결과·마스크·사용자 작성 대기 함수는 변경하지 않았습니다.

## 회귀 검사

`web-tests/pan.spec.js`는 약한 확대에서의 가로·세로 이동량을 각각 검증하고 실제 canvas 픽셀 변화도 확인합니다.
비교/단일/모바일 화면, 스크롤 이동시 배율 유지, Ctrl와 Command 확대 후 다시 이동, 맞춤 복원을 검사합니다.
수학 테스트는 이동 제한과 가장자리에서도 유효한 영상 범위를 확인합니다.
`requestAnimationFrame`으로 그린 좌표를 읽기 전에 실제 가로·세로 이동량이 화면에 반영될 때까지 기다립니다. WebKit trace에서 즉시 읽은 이전 좌표와 이후 정상 이동한 캡처가 달랐기 때문에 이 대기를 추가했습니다.
캔버스 영역 검사는 [run42375948106](https://github.com/sokldjs554/pathology-edge/actions/runs/42375948106)의 WebKit에서696px 예상/756px 실제로 실패한 뒤 레이아웃을 수정했습니다.

CI를 Chromium/WebKit 두 엔진으로 확장했습니다. Linux WebKit 검사는 사용자의 macOS11.7 Safari 실기 확인을 대신하지 않습니다.
기존 이미지404 주입 검사는 WebKit에서 이미 썸네일로 디코딩된 이미지를 재사용해 오류를 만들지 못했습니다.
실패 응답을 페이지 로딩 전에 설치해 실제 실패 상황을 검증하도록 테스트 준비 순서를 수정했습니다.

## 직접 확인할 한 단계

데모를 새로고침 → `+` 한 번 → 영상을 누른 채 상하/좌우로 끌기 → 두 손가락으로 스크롤.
A/B가 함께 움직이고 일반 스크롤에서는 배율이 그대로여야 합니다. Ctrl/⌘+스크롤이나 `+`/`−`로 배율을 바꿀 수 있습니다.

재현 명령은 저장소 루트에서 `node --test web-tests/viewer-math.test.cjs`.
브라우저 검사는 `web-tests` 폴더에서 `npm ci` 후 Ubuntu에서
`npx playwright install --with-deps chromium webkit`를 실행합니다.
`UI_BROWSER=chromium npx playwright test`와 `UI_BROWSER=webkit npx playwright test`는 각각 checkout을 검사합니다.
`UI_BASE_URL=https://pathology-edge-lab.ykh13571.chatgpt.site`를 함께 설정하면 공개 배포를 검사합니다.
GitHub Actions의 **UI browser review → Run workflow → production**도 같은 두 엔진을 실행합니다.

## 수정본 검증과 배포

UI source commit: `2eb23c9b8e706d2e2cc9be58be495025f6478107`.
[checkout 검증42376086501](https://github.com/sokldjs554/pathology-edge/actions/runs/42376086501): Chromium19개/WebKit19개, 좌표5개 모두 통과.
[기존 CPU 검사42376086399](https://github.com/sokldjs554/pathology-edge/actions/runs/42376086399):33 passed / 사용자 과제12 skipped.

Sites 공개 버전4의 source commit은 `e6bfb748f1ecb2eb9f9c1b6cecdfa368682ff4b2`입니다.
[배포 파일47개 대조](../artifacts/ui/pan-fix/production-files.json) · [배포 정보](../artifacts/ui/pan-fix/deployment.json) · [연구 결과 보존](../artifacts/ui/pan-fix/invariants.json).

공개 주소의 [최종 검사42376303069](https://github.com/sokldjs554/pathology-edge/actions/runs/42376303069)도
**Chromium19 passed / WebKit19 passed**, 실패·skip·flaky0으로 완료했습니다.
[검증 요약](../artifacts/ui/pan-fix/verification.json) ·
[Chromium 이동 후 화면](../artifacts/ui/pan-fix/chromium/pan-1440-boundary.png) ·
[WebKit 이동 후 화면](../artifacts/ui/pan-fix/webkit/pan-1440-boundary.png) ·
[WebKit 모바일 크기](../artifacts/ui/pan-fix/webkit/pan-390-boundary.png).
사용자가 수정본을 실행·확인한 것으로 기록하지 않았습니다.
