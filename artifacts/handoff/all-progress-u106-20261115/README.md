# 전체 자료 통합 검증 기록

- 소프트웨어/실험 기준 소스: fbc5f0d7e09f151c2790eca5e7463b41fdf279e7.
- `verification.json`: 1,754개 ZIP 파일의 CRC·해시, 사용자 코드7개 원문, 원본ZIP2개, U00–U106,23개 과정·주요70링크 검사.
- `browser.json`: 실제 Chromium1440px/390px에서 목차·개인기록·비교 그림·정규화 및 최종 검토 화면 확인. 최종 예제 전환,동일 RGB,표시 전환 시 수치 유지.
- 브라우저 검사 초기에 정규화 검토기를 SVG3개로 가정한 검사 코드를 실제 구현인 Canvas2개로 수정한 뒤 다시 확인했습니다. 제품 소스·수치는 바꾸지 않았습니다.
- 이 작업에서 학습·추론·임상 검증·사용자 수행을 추가하지 않았습니다. 소스 CI 결과와 패키지 검사를 구분합니다.
- `build.py`/`verify.py`/`serve.py`/`browser.mjs`는 원래 `work/all-progress-handoff-20261115/`에서 실행한 포장 도구 사본입니다. `git-inventory.json`은 고정 소스의 `git ls-tree -rl`로 만든 경로·blob·크기 목록이며 전체 항목은 ZIP의 `FILE_INVENTORY.json`에 있습니다. 이 도구 사본이 독립 모델 실행 패키지라는 뜻은 아닙니다.
- 실제 공개 URL 다운로드 검사는 게시 후 `publication.json`에 추가합니다. 해당 기록이 없다면 다운로드 성공을 추정하지 마세요.
