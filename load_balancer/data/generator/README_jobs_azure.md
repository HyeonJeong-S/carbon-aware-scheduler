# jobs_azure.csv — Azure 2019 VM 트레이스에서 유도한 두 번째 워크로드

synthetic `load_balancer/data/jobs.csv`와 **같은 8열 스키마**(job_name, submit_time, duration, region, k, L_max, submit_local_hour, band)로 만들었다. 스케줄러의 `scheduler.data_loader.load_jobs_csv()`가 그대로 읽는다(아래 §7).

생성: `./.venv/bin/python gen_jobs_azure.py` (seed 42, 결정적 — 두 번 돌려 바이트 동일 확인). 약 8초.

## 1. 출처 (provenance)

| 항목 | 값 |
|---|---|
| 데이터셋 | Azure Public Dataset **V2** (2019 VM trace), https://github.com/Azure/AzurePublicDataset/blob/master/AzurePublicDatasetV2.md |
| 받은 파일 | `trace_data_vmtable_vmtable.csv.gz` (문서상 이름 `vmtable/vmtable.csv.gz`) |
| 정확한 URL | https://github.com/Azure/AzurePublicDataset/releases/download/dataset-v2/trace_data_vmtable_vmtable.csv.gz (링크 목록 `AzurePublicDatasetLinksV2.txt`에 수록; 예전 Azure Blob URL은 여기로 리디렉션) |
| 크기 | 437,594,496 바이트 (≈0.44 GB). 전체 데이터셋은 압축 156 GB/198 파일이지만 VM별 CPU 시계열(195파일)은 받지 않았다 |
| SHA256 | `e8c9a0ab0e06b4322747147b49f8b44c07cf017327a150a92b6fb95aab8de3e5` |
| 스키마 | 헤더 없음, 11열: vmid, subscriptionid, deploymentid, vmcreated, vmdeleted, maxcpu, avgcpu, p95maxcpu, vmcategory, vmcorecountbucket, vmmemorybucket (`schema.csv`로 확인). 시각은 트레이스 시작 기준 초, **300초(5분) 단위로 양자화** |
| 규모 | 2,695,548 VM, 6,687 구독, 30일 연속(마지막 시각 2,591,400 s = 29.993일), 단일 Azure 지역 |
| 라이선스 | 저장소 `LICENSE` = **Creative Commons Attribution 4.0 International (CC-BY 4.0)** — 저장소 루트 LICENSE 파일로 확인 |
| 인용 요청 | 저장소 README: "If you do use either of these VM traces in your research, please make sure to cite our SOSP'17 paper" |

인용 (Crossref DOI 레코드로 대조 확인):

> Eli Cortez, Anand Bonde, Alexandre Muzio, Mark Russinovich, Marcus Fontoura, and Ricardo Bianchini. 2017. **Resource Central: Understanding and Predicting Workloads for Improved Resource Management in Large Cloud Platforms.** In *Proceedings of the 26th Symposium on Operating Systems Principles (SOSP '17)*, Shanghai, China, October 28–31, 2017. ACM, New York, NY, USA, 153–167. https://doi.org/10.1145/3132747.3132772

(논문 본문의 분석 대상은 2017년 트레이스다. 2019년 V2 트레이스 자체를 분석한 논문은 없고, 저장소가 같은 SOSP'17 인용을 요청한다. 데이터셋 자체도 함께 적는 것이 안전: "Microsoft Azure. Azure Public Dataset V2, 2019. https://github.com/Azure/AzurePublicDataset".)

## 2. 원자료에서 발견한 것 — 매핑 설계를 바꾼 사실 세 가지

1. **vmcategory 라벨은 거의 없다.** VM 수 기준 Unknown 91.2 % / Delay-insensitive 5.9 % / Interactive 2.9 %. (데이터셋 동봉 `azure2019_data_category.txt`의 51/43/6은 VM 수가 아니라 VM-시간 가중 수치와 맞는다 — 실측 VM-시간 비중 62.4/30.6/7.0.) 게다가 **라벨이 붙은 VM은 전부 5일 이상 산 VM**(최소 431,100 s)이다. 절단 VM을 빼면 라벨 보유율은 0.51 %(DI 8,413 / Int 3,952 / Unknown 2,410,599). 따라서 "카테고리 → 등급" 매핑은 보조 신호로만 쓸 수 있고, 주된 등급 배정 규칙이 따로 필요하다.
2. **시각이 5분 단위**다. duration도 300 s의 배수이고, 5.9 %(144,116)는 duration = 0(같은 5분 버킷 안에서 생성·삭제). synthetic k4·k5(중앙 30 s·5 s)의 초 단위 길이는 트레이스로 재현할 수 없다.
3. **절단(censoring)이 크다.** created = 0인 VM 227,316(트레이스 시작 전부터 존재, 제출 시각 불명), deleted = T인 VM 224,509(끝까지 생존, 길이 불명), 둘 다인 것 179,241. 우측 절단을 빼면 마지막 날(29일째) 도착이 49,369로 평소(≈85,000)의 58 %로 꺼진다.

## 3. 매핑 결정 (전부 `gen_jobs_azure.py`에 구현)

| 항목 | 결정 | 근거 |
|---|---|---|
| 절단 처리 | created = 0, deleted = T, created ≥ 29일 **세 부류 모두 제거**. 남은 풀 2,373,595 VM | 좌측 절단은 제출 시각이, 우측 절단은 길이가 없다. 29일째는 우측 절단으로 도착·길이 분포가 모두 왜곡되므로 통째로 뺐다(타일 주기 29일). 남는 편향: 27~28일째 도착 중 1~2일 넘게 산 VM(전체의 약 5 %)이 조금 빠진다 |
| duration | `deleted − created` 그대로(300 s 배수). 0이면 **150 s** | 양자화 값을 바꾸지 않는다. 0은 실제 길이가 (0, 300) 어딘가라는 뜻이므로 구간 중앙값. 스케줄러 슬롯이 1시간이라 150 vs 300은 결과에 거의 무관 |
| k (라벨 있음) | Delay-insensitive → {1, 2}, Interactive → {4, 5}. 쌍 안에서는 **duration 내림차순 순위**로 synthetic 비율(k1:k2 = 3:1, k4:k5 = 2:3)에 맞춰 긴 쪽이 더 여유 있는 등급(k1, k4) | 과제 지시대로. synthetic에서도 k1 길이중앙 > k2, k4 > k5이므로 같은 방향. 라벨 VM이 전체의 0.5 %라 쌍 내 분할법은 결과에 거의 영향 없음 |
| k (Unknown, 99.5 %) | **synthetic 사전비율 3:1:1:2:3으로 난수 배정** (`--unknown-rule prior`, 기본) | (a) 과제의 1안 "Unknown → k=3"은 등급 혼합이 0.3:0.1:99:0.1:0.2가 되어 지연가능 작업이 사실상 없어지므로 기각. (b) "라벨 비율(DI:Int = 67:33)로 비례 분할"은 라벨 모집단이 5일 이상 생존 VM뿐이라 짧은 VM에 그 사전확률을 옮길 근거가 없고, 지연가능 비중이 40 %→67 %로 바뀌어 실제 트레이스 효과와 혼합 효과가 섞인다. (c) 채택안은 **등급 혼합을 synthetic과 같게 고정**하고 도착 과정·길이 분포만 실측으로 바꾸는 통제 실험이 된다. 트레이스에는 지연 허용 여부를 알려주는 신뢰할 신호가 없다는 점을 논문에 그대로 적어야 한다 |
| k 대안 | `--unknown-rule duration`: 긴 순서대로 k1→k5(할당량 3:1:1:2:3) | "배치 = 길다 = 미룰 수 있다"는 synthetic의 설계 논리를 트레이스에 적용하는 안. 등급과 길이가 1:1로 묶여(k1 중앙 15,300 s, k5 중앙 300 s) 지연가능 작업이 전부 긴 작업이 되므로 시간이동 효과가 구조적으로 달라진다. 비교용으로만 남긴다(`stats_azure_durationrule.txt`) |
| L_max | 등급별 범위(k1 43200–86400, k2 7200–28800, k3 120–600, k4 15–60, k5 1–5) 안에서 **log-uniform**, seed 42 | gen_jobs.py와 같은 분포·같은 범위. 난수 호출 순서는 다르므로 synthetic과 값이 같지는 않다 |
| region | **VM마다 8개 리전 균등 난수** (`--region-rule uniform`, 기본) | 트레이스는 단일 지역이라 보존할 공간 신호가 없다. 구독 해시 방식은 최대 구독 하나가 VM의 15.1 %를 차지해 어떤 배정으로도 한 리전이 ≥15 % (나머지 ≈12.1 %)가 되어 리전별 용량 수치의 비교 가능성이 깨진다(대안 `--region-rule subscription`, greedy 균형: France 61.3/일 vs 나머지 48.4/일, `stats_azure_subscriptionrule.txt`) |
| 도착(타일링) | 29일 타일 **13장**(0, 29, …, 348일), 13번째는 365일에서 절단. 타일마다 **다른 VM 11,600개를 비복원 추출**(11,600 = 146,000 × 29/365) | 12장(348일)으로는 모자라 13장. 타일마다 다른 표본이라 한 해가 같은 30일의 복사본이 아니다. 30 ≠ 7의 배수라 요일 주기는 보존되지 않는다(트레이스 시작 요일도 비공개) |
| 시각 해상도 | 5분 버킷 안에서 **U[0, 300) 지터**를 더해 동시 제출을 푼다 | 버킷 시작으로 내림된 값이라 실제 생성 시각은 버킷 안 어딘가. 시간 단위 도착 패턴은 그대로 유지 |
| 시계 해석 | 트레이스 시각을 **각 리전의 현지시각**으로 해석: `submit_time = (tile + t_trace + jitter − offset) mod 365일` | gen_jobs.py가 현지시각을 먼저 뽑고 UTC로 바꾸는 것과 같은 규약. 트레이스 시각이 UTC인지 현지인지 문서에 없다(미확인). 일중 진폭이 ±15 %로 작아 어느 쪽이든 영향은 작다 |
| 규모 | 146,016 jobs (목표 146,000, +0.01 %). 타일당 추출률 0.489 % | 작업 **수**는 맞췄지만 작업 **부하**는 다르다 — §5 참고 |
| t = 0 | 2025-01-01 00:00 UTC (탄소 자료 `interface/carbon_2025`와 같은 해) | gen_jobs.py 주석의 `START_DATE = "2026-01-01"`은 낡은 기록으로 보인다 — 확인 요망 |
| job_name | 제출 순서대로 `az_000000`… | synthetic `j_…`와 구별. `jobs_azure_provenance.csv`에 job_name ↔ vmid, 타일 번호, 원 시각, vmcategory를 남겼다 |

## 4. 결과 통계 (`stats_azure.txt` 원문)

### 4.1 등급 혼합

| k | jobs | 비중 | synthetic |
|---|---|---|---|
| 1 | 43,802 | 30.00 % | 30.0 % |
| 2 | 14,513 | 9.94 % | 10.0 % |
| 3 | 14,551 | 9.97 % | 10.0 % |
| 4 | 29,438 | 20.16 % | 20.0 % |
| 5 | 43,712 | 29.94 % | 30.0 % |
| 지연가능 (L_max ≥ 1 h) | 58,315 | 39.94 % | 39.92 % |

라벨 기여: Delay-insensitive 525 (k1 394, k2 131), Interactive 241 (k4 96, k5 145), Unknown 145,250.

### 4.2 duration 분위수 [s] — Azure vs synthetic

| k | p5 | p25 | p50 | p75 | p90 | p95 | p99 | max | 평균 |
|---|---|---|---|---|---|---|---|---|---|
| Azure k1 | 150 | 600 | 1,500 | 5,400 | 36,300 | 81,600 | 509,397 | 2,589,300 | 24,686 |
| Azure k2 | 150 | 600 | 1,500 | 5,100 | 35,400 | 78,120 | 518,964 | 1,650,300 | 19,917 |
| Azure k3 | 150 | 600 | 1,500 | 4,800 | 32,700 | 65,100 | 260,850 | 600,300 | 14,021 |
| Azure k4 | 150 | 600 | 1,500 | 4,800 | 34,200 | 71,145 | 312,246 | 2,584,500 | 18,417 |
| Azure k5 | 150 | 600 | 1,500 | 5,100 | 34,500 | 71,835 | 289,437 | 2,228,400 | 16,425 |
| **Azure 전체** | 150 | 600 | 1,500 | 5,100 | 35,100 | 74,400 | 347,400 | 2,589,300 | 19,412 |
| synthetic k1 | 1,213 | 2,952 | 5,370 | 9,874 | 17,050 | 21,600 | 21,600 | 21,600 | 7,294 |
| synthetic k2 | 404 | 957 | 1,748 | 3,225 | 5,592 | 7,730 | 14,400 | 14,400 | 2,585 |
| synthetic k3 | 48 | 105 | 180 | 308 | 497 | 666 | 1,118 | 1,800 | 245 |
| synthetic k4 | 9 | 19 | 30 | 48 | 74 | 95 | 155 | 300 | 38 |
| synthetic k5 | 2 | 3 | 5 | 8 | 11 | 14 | 20 | 60 | 6 |
| **synthetic 전체** | 3 | 8 | 81 | 3,017 | 8,214 | 13,074 | 21,600 | 21,600 | 2,480 |

Azure는 등급과 무관하게 같은 길이 분포(prior 규칙이니 당연). 핵심 차이: 중앙값 1,500 s vs 81 s, p99 4일 vs 6시간, 최대 30일.

### 4.3 리전별 하루 작업 수 (synthetic은 정확히 50)

| 리전 | 평균 | 표준편차 | 최소 | 최대 | 합계 |
|---|---|---|---|---|---|
| US_West | 49.97 | 9.26 | 26 | 75 | 18,238 |
| US_Central | 49.96 | 8.90 | 23 | 74 | 18,234 |
| US_East | 49.93 | 9.17 | 24 | 79 | 18,223 |
| France | 49.93 | 10.28 | 23 | 81 | 18,224 |
| Germany | 50.17 | 9.90 | 23 | 70 | 18,313 |
| Korea | 49.97 | 9.41 | 25 | 75 | 18,239 |
| India | 49.95 | 10.46 | 24 | 82 | 18,231 |
| Japan | 50.18 | 9.61 | 23 | 77 | 18,314 |

### 4.4 시각별 도착 (현지시각 = 트레이스 시계 / UTC)

| 시 | 현지 | UTC | 시 | 현지 | UTC | 시 | 현지 | UTC |
|---|---|---|---|---|---|---|---|---|
| 00 | 6,512 | 6,077 | 08 | 5,900 | 5,902 | 16 | 6,819 | 6,100 |
| 01 | 6,069 | 5,987 | 09 | 5,635 | 6,017 | 17 | 6,375 | 5,995 |
| 02 | 5,640 | 5,915 | 10 | 5,674 | 6,054 | 18 | 6,762 | 5,707 |
| 03 | 4,957 | 6,339 | 11 | 5,761 | 6,056 | 19 | 6,185 | 6,062 |
| 04 | 5,934 | 6,131 | 12 | 6,168 | 6,084 | 20 | 6,823 | 6,098 |
| 05 | 5,827 | 6,178 | 13 | 5,368 | 6,155 | 21 | 6,941 | 6,010 |
| 06 | 5,691 | 6,051 | 14 | 6,107 | 6,179 | 22 | 6,747 | 6,109 |
| 07 | 5,534 | 6,170 | 15 | 6,079 | 6,305 | 23 | 6,470 | 6,335 |

낮(현지 8–20시) 비중 49.9 % (synthetic 54.1 %). 트레이스의 일중 패턴은 골 03시(4,957) · 봉우리 21시(6,941)로 진폭이 ±15 %에 그친다 — synthetic의 13시 봉우리(10,006) / 19시 골(2,328) 같은 뚜렷한 낮밤 구조가 없다. 원 트레이스(절단 제거 후 2.37 M VM)도 같은 모양이다.

날짜별 원 트레이스 도착(절단 제거 후): 0~28일째 88,094 / 72,084 / 65,241 / 85,819 / 93,583 / 88,810 / 84,140 / 79,174 / 72,182 / 73,115 / 92,951 / 91,928 / 88,827 / 90,572 / 87,025 / 62,517 / 72,684 / 86,031 / 78,941 / 79,011 / 92,783 / 87,862 / 57,259 / 53,110 / 92,322 / 86,373 / 95,765 / 87,783 / 87,609 — 주말로 보이는 골이 1–2, 8–9, 15–16, 22–23일째에 있다(7일 주기). 타일이 29일이라 이 주기는 한 해에 걸쳐 어긋난다.

## 5. 꼭 알아야 할 한계 (flag)

1. **작업 수는 같아도 부하는 7.8배다.** 총 작업시간 787,368 h (평균 5.39 h/job) vs synthetic 100,575 h (0.69 h/job). 리전별 용량 상한을 synthetic 기준으로 잡았다면 Azure 워크로드에서는 위반이 훨씬 많이 나올 것이다. 최대 길이 30일 작업(2,589,300 s)도 있다. 작업 수 대신 작업시간으로 맞추려면 `TARGET_JOBS`를 ≈18,700으로 줄여야 한다 — 어느 쪽으로 맞출지 결정 필요.
2. **지연 허용 여부(k)는 트레이스에서 나온 것이 아니다.** 99.5 %가 synthetic 사전비율 난수다. 논문에는 "도착 과정과 실행 길이는 실측, 지연 예산은 synthetic과 같은 모형"으로 써야 한다.
3. 트레이스 시계가 UTC인지 현지인지 미확인. 일중 진폭이 작아 영향은 작다.
4. k4·k5(초 단위 작업)의 길이는 트레이스 해상도(300 s) 때문에 재현 불가 — 최소 150 s.
5. 우측 절단 제거로 긴 VM이 체계적으로 빠진다(트레이스 끝에 가까울수록). 길이 분포는 실제보다 짧은 쪽으로 치우친다.
6. 요일 주기 소실(29일 타일), 트레이스가 단일 지역이라 리전 간 차이는 전부 인위적.

## 6. 파일

| 파일 | 내용 |
|---|---|
| `gen_jobs_azure.py` | 생성기 (seed 42). `--unknown-rule {prior,duration}` `--region-rule {uniform,subscription}` `--out` |
| `jobs_azure.csv` | 146,016 행, 8열. SHA256 `bd813de2f3f11577d04bddffc45cbfb2f5a2b2c0b811ed53380e8a1ebf9f19df` |
| `jobs_azure_provenance.csv` | job_name ↔ vmid, tile, created_raw, deleted_raw, vmcategory |
| `stats_azure.txt` | 기본 규칙 통계 (위 표의 원문) |
| `stats_azure_durationrule.txt`, `jobs_azure_durationrule.csv` | 대안 k 규칙 결과 |
| `stats_azure_subscriptionrule.txt`, `jobs_azure_subscriptionrule.csv` | 대안 region 규칙 결과 |
| `vmtable.csv.gz`, `vmtable.sha256` | 원자료와 해시 |
| `V2.md`, `links_v2.txt`, `schema.csv`, `repo_README.md`, `LICENSE_repo.txt` | 받은 날(2026-10-16)의 데이터셋 문서 사본 |
| `explore.py`, `explore2.py` | 원자료 탐색 스크립트 (§2의 수치) |

## 7. 로더 검증

저장소 루트에서:

```
./.venv/bin/python -c "from scheduler import data_loader; j=data_loader.load_jobs_csv('<scratch>/azure/jobs_azure.csv'); print(len(j), j[0])"
146016 {'id': 'az_000000', 'submit_time': 0.09119444444444445, 'duration': 516.0833333333334, 'k': 1, 'L_max': 16.081333333333333, 'region': 'JP', 'carbon_region': None, 'deadline': 532.2558611111111}
```

리전 코드 변환(Japan→JP 등) 정상, k ∈ {1..5}, 최대 deadline 9,493.9 h (시뮬레이터 horizon = max(deadline)+24 h 이므로 수용).
