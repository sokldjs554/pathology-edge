# Cowork 전달 파일

**현재 통합 묶음: [PathologyEdge-Cowork-U97-20261113.zip](https://raw.githubusercontent.com/sokldjs554/pathology-edge/cede17581ae9bde9e33d458950bdedb0d984a5a7/artifacts/handoff/PathologyEdge-Cowork-U97-20261113.zip)** — 781파일, 24,135,855bytes(약24.1MB). 기존 U86 자료에 자동 Ki-67 패치 분석·후보 제거·학습 중심·재현율 진단과 U87–U97 응답을 통합했습니다. U98은 예정입니다. 압축을 풀어 `START_HERE.html`을 여세요.

SHA256: `fc4362f179c03c20e6dbf40f702f44e87b0b68d1a5f1d4cbf60651524acab9ee`. 문서 기준 소스 `7a13d43993b179a359fbe8314392e0ae34276325`. [실제 다운로드 대조](u97-checks/download-check.json) · [패키지 검사](u97-checks/build-report.json) · [브라우저 확인](u97-checks/browser-check.json) · [현재 요약](../../docs/HANDOFF_U97.md). 큰 원본 모델·예측·모바일 캡처는 ZIP 안 `EVIDENCE_DOWNLOADS.md`의 고정 링크·SHA로 보존했습니다. 완전한 설치 패키지는 아닙니다.

현재 후속 소스는 draft PR #2이며 main 병합·공개 데모 배포를 하지 않았습니다. 최신 실제 코드 CI는 `fda5695`의571passed/skip0이며 이번 통합은 문서·포장·브라우저 연결 검사만 수행했습니다. 사용자 새 실행으로 기록하지 않습니다.

## 이전 발행 기록 — 당시 상태 그대로


**최신 통합 묶음(2026-11-13 KST):** [PathologyEdge-Final-Handoff-20261113.zip 다운로드](https://raw.githubusercontent.com/sokldjs554/pathology-edge/main/artifacts/handoff/PathologyEdge-Final-Handoff-20261113.zip). **415개 파일 · 16,397,030bytes(약16.4MB)**. 이전365개 파일의 범위를 유지하면서 최신 문서, NuCLS51시야·5케이스 결과/정렬 그림, U84–U86 확인을 통합했다. 압축을 풀어 `START_HERE.html`부터 읽는다. 큰 원본 증거ZIP7개는 고정 링크·SHA로 연결한다.

SHA256: `a74b32bcfacf0f347600b2f6efd627d1b808cca338d0c975227a801def50b073`. [파일 목록·검사](manifest-final-20261113.json) · [독립 내용 대조](review-final-20261113.json). 기준 소스 `dced5d0cfaee955015f0ece599bb29ce808ccc1f`. 자동 Ki-67 검출과 외부 성능 개선 성공은 후속 연구 후보로 표시했으며 새 실험을 실행한 것으로 포함하지 않았다. 기존 발행 ZIP은 변경하지 않았다.

**최신 추가 자료:** [NuCLS36쌍 격자 불일치 처리](../../docs/NUCLS_GRID_ALIGNMENT.md)로51시야·5케이스 모두 평가했다. Dice0.628150→0.613006,8상승·43하락. [보충 증거 ZIP](../experiments/nucls-alignment-20261113/evidence-v2.zip)은 선행NuCLS ZIP과 함께 사용한다. 아래최종v2와 선행15시야 ZIP의 내용·해시는 유지했다. 후속 응답으로 정렬 비교 세 패널의 사용자 표시 확인을 U86에 추가했다. 새 추론·독립 좌표 검증·전체36쌍 검토는 확인하지 않았다. U86은 보충 ZIP 발행 이후의 별도 기록이다.

2026-11-13 KST에는 [NuCLS SP.3 원본 연결 평가](../../docs/NUCLS_SP3_EVALUATION.md)를 추가했습니다. 원본5개 해시 확인,15시야·4케이스 실제 평가,36쌍 치수 불일치 보류를 구분합니다. [추가 실험 근거 ZIP](../experiments/nucls-sp3-20261113/evidence.zip)은 별도 파일이며 아래최종v2 ZIP의 내용·해시는 바꾸지 않았습니다. 후속 응답으로 최대 악화 사례 네 패널 표시를 사용자 확인 U84에 기록했습니다. 선정15시야 평균의 선택 편향·전체51시야로의 일반화 제한 해석도 U85에 기록했습니다. 사용자 새 추론 실행은 확인하지 않았으며, U84–U85는 아래최종v2 ZIP 발행 이후의 추가 기록입니다.

최종v2 발행 후 [추가 공개자료 조사 검토](../../docs/PUBLIC_DATA_UPLOAD_REVIEW.md)를 기록했습니다. 새 IHC 후보의 JSON 11개·영상/마스크 1쌍을 대조했으며 새 성능평가·임상 검증·전체 WSI 정답 검증은 아닙니다. 아래ZIP의 기존 내용·해시는 유지합니다.

**이전 최종v2 묶음:** [PathologyEdge-Final-Handoff-20261112-v2.zip 직접 다운로드](https://raw.githubusercontent.com/sokldjs554/pathology-edge/main/artifacts/handoff/PathologyEdge-Final-Handoff-20261112-v2.zip). **365개 파일 · 11,552,627 bytes(약11.6MB)**. [목록·검사](manifest-final-20261112-v2.json).

소스 커밋: `a21bb05c4e22e4fd78718cd230312a59109243c7`
SHA256: `ed4c0479ed515d8d448a007f586b7b1b36a5569a70ad3ab4f4abc9fc11ab35f1`

압축을 풀어 `START_HERE.html` 또는 `START_HERE.txt`부터 읽습니다. 전체 진행 요약, 직접 작성한7개 항목의 코드·범위, 사용자 실행·검토 **U01–U83**, 당시 단계 문서와 제출 근거, BCData402장·원본 WSI/주석 대조 결과, 보관 화면·실제 오류 그림을 포함합니다. 큰 원본 증거 ZIP5개는 고정 다운로드·SHA로 연결합니다.

이번 갱신에는 다음 직접 수행 기록을 추가했습니다.

- BCData 공식test1206파일의 수신 완료 보고와 기대 manifest SHA 일치.
- 제공된 도구를 이용한109·367 두 장의 본인 추론, 저장 결과 일치 보고, 세 패널 표시 확인, 양성률·분모·세포 분류 정확도에 대한 해석.
- MoNuSeg 외부14ROI의 평균 하락과 최대 하락 사례의FN 감소·FP 증가를 근거로 일반화 한계를 설명한 답변.
- A0ST 외부 비교 그림의 표시 확인.

BCData402장 전체와 MoNuSeg14장 전체 평가 실행은 제공된 개발 환경 수행입니다. 모든 외부 영상의 개별 검토, 임상 검증, 전체 WSI 핵 정답 검증은 완료한 것으로 기록하지 않습니다. 새 학습·추론·브라우저 테스트·배포는 이번 포장 범위에 포함하지 않습니다.

BCData 원영상·HDF5·개별 세포 좌표·비공개 비교SVG는 포함하지 않습니다. 공식 다운로드를 통해 확보한 사용자 로컬 원자료는 별도 보관합니다. 공개 파생 그림의 출처·이용 조건은 ZIP 내부 `LICENSES_AND_SCOPE.txt`를 따릅니다.

ZIP CRC, 구성 파일별SHA, HTML 내부 경로, 문서 실행 예제 보존 및 연결한 원본 증거 ZIP5개의CRC를 확인했습니다. 상세 결과는 위 manifest에 있습니다.

## 이전 보관본

아래 파일의 내용과 기존 해시는 유지했습니다. 최신 직접 수행 기록은 맨 위20261113 통합 묶음을 사용하세요.

| 파일 | 범위 | SHA256 |
|---|---|---|
| [최종20261112 원본](https://raw.githubusercontent.com/sokldjs554/pathology-edge/f2713b212828b87bf42da03708de931fb4431d40/artifacts/handoff/PathologyEdge-Final-Handoff-20261112.zip) | U01–U73,348개 파일·11,528,072bytes | `643cb7d5f52d675e4490430e71d8b41cb0bdd8fd8afed29175c5104f18efab73` |
| [초기 Cowork v2](PathologyEdge-Cowork-v2.zip) | 14개 파일·3,579,126bytes | `f276a4752c988215721a4966b973e89453a083f7b13f18b6fe5a62a76b2b4a8d` |
| [초기 Cowork v1](PathologyEdge-Cowork.zip) | 8개 파일·2,104,347bytes | `03162180b9fb3d7b8696d698b9a20eb0f93f3de1fb58d42a52b648e33159af57` |

이전 버전의 상태 표기는 발행 당시 기록입니다. 최종 상태는 최신 묶음의 `docs/FINAL_PROGRESS.md`와 `docs/CONTRIBUTIONS.md`를 확인하세요.
