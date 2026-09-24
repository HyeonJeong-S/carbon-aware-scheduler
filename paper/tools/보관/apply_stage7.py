"""
apply_stage7.py — E8 통독 반영 1차(항목 1~5) 일괄 적용
작성: 2026-09-21, carbon-aware-scheduler-4d(원고 트랙). 실행은 be가 한다.

내용: paper/정리.txt [43] E8 통독 결과 1~5번, be 지시 그대로.
  1. 서론 문단96 헤드라인 62.94% 단일화 + 내부메모(코드수정 보류) 삭제.
     문단97(각주 판단 보류 메모) 삭제. 6.3절 문단626을 "경계값 예고 ->
     6.4에서 확정" 구조로 재작성(옛 65.93/59.37 반복 제거).
  2. ** 제외됨(be 지시, 2026-09-21 2차) ** — 배경지식 ⚠ 문단은 표5/§6.5
     자체가 옛 사후강제 시대 실험이라 현행 롤링 코드로 재현 불가 판정이
     났다(3d 전수대조, 정리.txt [46]). §6.5가 롤링 기준으로 재구성되는
     stage9에 묶어서 처리한다 — 지금 표5 숫자로 쓰면 stage9에서 바로
     낡는다. 참고: 롤링 기준 새 방향은 "조일수록 기여가 작아진다"로,
     원래 ⚠ 메모가 맞았던 방향이다(4d의 표5 기반 초안은 폐기).
  3. 그림2(로드밸런서) 블록을 §5.4 끝(그림4 뒤)에서 §5.4 도입 문단 바로
     뒤(그림4보다 앞)로 이동 — 그림 등장 순서를 1->2->3->4->5->6으로 교정.
  4. 서론(문단85)의 LSTM 첫 등장에 "(Long Short-Term Memory, 장단기 기억
     신경망)" 풀어쓰기 1회 추가.
  5. rels의 고아 rId39(옛 LSTM 구조도, image2.png, stage4가 놓친 것) 제거
     + word/media/image2.png 패키지에서 제외.

** 항목 6(식 9개·표 6개 산문 번호 인용 삽입)은 이번 stage7에 없다 — 범위가
너무 커서(각 식·표마다 개별 문맥 조사 필요) 별도 배치로 분리했다. be에게
이미 보고함. **

** 그림2 이동 특이사항 — 문단 diff 감사로 못 잡는 종류의 변경 **
그림2 블록(4개 문단, paraId FB000001~4)은 내용이 안 바뀌고 위치만 바뀐다.
paraId->본문 매핑 기반 diff 감사는 이런 "이동"을 수정/삭제/삽입 어느 것으로도
안 잡는다(집합 관점에서 아무 것도 안 바뀐 것과 같음) — 그래서 아래에 별도로
"이동 자체가 실제로 일어났는가"를 확인하는 위치 기반 체크를 추가했다.

사용법: python3 paper/tools/apply_stage7.py [--dry-run]
"""
import sys, os, shutil, zipfile, datetime, argparse, re
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCX = os.path.join(REPO, "paper", "CAST.docx")
VERSIONS_DIR = os.path.join(REPO, "paper", "versions")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

EXPECTED_MODIFIED = {'76E97778', '4D34B9DF', '358E43A2'}
EXPECTED_DELETED = {'2DC5778B'}
EXPECTED_INSERTED = set()
EXPECTED_PARA_DELTA = -1  # 문단97 삭제 1건, 이동은 델타 0

P96_OLD = '<w:p w14:paraId="358E43A2" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>1</w:t></w:r><w:r><w:t>년치</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실측</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소집약도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>데이터를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>사용한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시뮬레이션에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>총</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>배출량이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>최대</w:t></w:r><w:r><w:t xml:space="preserve"> 65.93% </w:t></w:r><w:r><w:t>감소하였다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>다만</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>값은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단계가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>지키지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>않은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>조건에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>얻어진</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>것이다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>배치가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결정된</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>뒤에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>사후에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>강제하면</w:t></w:r><w:r><w:t xml:space="preserve"> 59.37%</w:t></w:r><w:r><w:t>가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>되며</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>실현</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가능한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>절감은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>두</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>값</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>사이에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>있다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>작업</w:t></w:r><w:r><w:t xml:space="preserve"> 146,000</w:t></w:r><w:r><w:t>건</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>전량이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>마감</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이내에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>처리되어</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>마감</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>위반은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>발생하지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>않았다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>(</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>스케줄러에도</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>용량</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>제약을</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>넣어야</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>하는데</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>코드</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>수정은</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>일단</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>하지</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>않기로</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>함</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve">. </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>향후</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>과제로</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>뺄</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>것</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>)</w:t></w:r></w:p>'
P96_NEW = '<w:p w14:paraId="358E43A2" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">1년치 실측 탄소집약도 데이터를 사용한 시뮬레이션에서 총 배출량이 62.94% 감소하였다. 공간 이동과 온라인 용량 인지 시간 이동을 결합한 결과로, 작업 146,000건 전량이 마감 이내에 처리되어 마감 위반은 발생하지 않았다.</w:t></w:r></w:p>'
P97_OLD = '<w:p w14:paraId="2DC5778B" w14:textId="77777777" w:rsidR="00126056" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr></w:rPr></w:pPr><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>(</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>발표</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>당시</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> −65.6%</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>는</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>탄소</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>회계에서</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>시각을</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>인덱스로</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>바꿀</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>때</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> round</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>를</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>쓰던</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>버전의</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>값임</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve">. 2026-08-03 </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>커밋</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> e10c8f3</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>에서</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> floor</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>로</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>통일하며</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> −65.93%</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>가</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>됨</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve">. </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>탐색은</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> floor</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>인데</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>회계만</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> round</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>여서</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>비정수</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>제출</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>시각</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>작업이</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> 1</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>시간</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>어긋나던</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>것을</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>고친</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>것이므로</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>현행</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>값이</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>옳음</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve">. </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>각주로</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>넣을지</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>판단할</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>것</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>)</w:t></w:r></w:p>'
P626_OLD = '<w:p w14:paraId="4D34B9DF" w14:textId="77777777" w:rsidR="004A6DA0" w:rsidRDefault="00000000"><w:r><w:t>공간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동만으로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>총</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>배출량이</w:t></w:r><w:r><w:t xml:space="preserve"> 56.85% </w:t></w:r><w:r><w:t>감소한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>여기에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>더하면</w:t></w:r><w:r><w:t xml:space="preserve"> 65.93%</w:t></w:r><w:r><w:t>까지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>내려가나</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>값은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단계가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>지키지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>않은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>조건에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>얻어진</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>것이다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>배치가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결정된</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>뒤에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>사후에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>강제하면</w:t></w:r><w:r><w:t xml:space="preserve"> 59.37%</w:t></w:r><w:r><w:t>가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>된다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>실현</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가능한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>절감은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>두</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>값</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>사이에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>있다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>용량을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>지키지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>않을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>때</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>무슨</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>일이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>일어나는지는</w:t></w:r><w:r><w:t xml:space="preserve"> 6.4</w:t></w:r><w:r><w:t>절에서</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>사후</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>강제의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>방법과</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결과는</w:t></w:r><w:r><w:t xml:space="preserve"> 6.5</w:t></w:r><w:r><w:t>절에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>다룬다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'
P626_NEW = '<w:p w14:paraId="4D34B9DF" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">공간 이동만으로 총 배출량이 56.85% 감소한다. 시간 이동 단계가 리전 용량을 고려하지 않으면 65.93%까지 내려가지만, 이는 실현 불가능한 반사실 상한이다. 배치가 끝난 뒤 사후적으로 용량을 강제하면 59.37%에 그치는데, 이는 아무 것도 하지 않았을 때 감수해야 할 손해의 하한이다. 이 두 경계값 사이 어디에 실제 값이 있는지는 6.4절에서 온라인 용량 인지 알고리즘으로 확정한다.</w:t></w:r></w:p>'
FIG2_BLOCK_OLD = '<w:p w14:paraId="FB000001" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p><w:p w14:paraId="FB000002" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:anchor distT="0" distB="0" distL="114300" distR="114300" simplePos="0" relativeHeight="2" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="page"><wp:align>center</wp:align></wp:positionH><wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV><wp:extent cx="5727700" cy="2438400"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapTopAndBottom/><wp:docPr id="960" name="Picture 960"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="960" name="fig3_loadbalancer.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId55"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="5727700" cy="2438400"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r></w:p><w:p w14:paraId="FB000003" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 2. 공간 이동(로드밸런서) — 슬롯마다 파레토 무릎점으로 α를 자동 결정해 리전 용량 제약 안에서 작업을 배정하는 슬롯 단위 ILP.</w:t></w:r></w:p><w:p w14:paraId="FB000004" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">그림 2는 슬롯 단위 로드밸런서가 예측·지연 행렬·직전 배정을 입력받아 α를 슬롯마다 자동으로 정하고 ILP로 작업의 실행 리전을 배정하는 과정을 나타낸다.</w:t></w:r></w:p>'
SEC54_INTRO = '<w:p w14:paraId="3248A0C4" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>공간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단계는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>매</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>슬롯마다</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>다음</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>다섯</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가지를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>수행한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>첫째</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>그</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>슬롯에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>제출된</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>작업을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>수집한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>둘째</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>예측</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>모듈로부터</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전별</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소집약도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>예측값을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>받는다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>셋째</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>탄소</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>비용과</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>지연</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>비용을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>각각</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>정규화한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>넷째</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>정수</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>계획</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>문제를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>풀어</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>배정을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>확정한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>다섯째</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>배정된</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>작업을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>동안</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>해당</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>반영한다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'
P85_OLD = '<w:p w14:paraId="76E97778" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>본</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>논문은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>인지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>스케줄링</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시스템</w:t></w:r><w:r><w:t xml:space="preserve"> CAST</w:t></w:r><w:r><w:t>를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>제안한다</w:t></w:r><w:r><w:t>. CAST</w:t></w:r><w:r><w:t>는</w:t></w:r><w:r><w:t xml:space="preserve"> LSTM</w:t></w:r><w:r><w:t>으로</w:t></w:r><w:r><w:t xml:space="preserve"> 8</w:t></w:r><w:r><w:t>개</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>향후</w:t></w:r><w:r><w:t xml:space="preserve"> 24</w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소집약도를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>예측하고</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>정수</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>선형</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>계획법</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>기반</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>로드밸런서가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결정한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>뒤</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>스케줄러가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>각</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>작업의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>마감</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이내에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시각을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결정한다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'
P85_NEW = '<w:p w14:paraId="76E97778" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>본</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>논문은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>인지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>스케줄링</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시스템</w:t></w:r><w:r><w:t xml:space="preserve"> CAST</w:t></w:r><w:r><w:t>를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>제안한다</w:t></w:r><w:r><w:t>. CAST</w:t></w:r><w:r><w:t>는</w:t></w:r><w:r><w:t xml:space="preserve"> LSTM(Long Short-Term Memory, 장단기 기억 신경망)</w:t></w:r><w:r><w:t>으로</w:t></w:r><w:r><w:t xml:space="preserve"> 8</w:t></w:r><w:r><w:t>개</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>향후</w:t></w:r><w:r><w:t xml:space="preserve"> 24</w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소집약도를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>예측하고</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>정수</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>선형</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>계획법</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>기반</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>로드밸런서가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결정한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>뒤</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>스케줄러가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>각</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>작업의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>마감</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이내에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시각을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결정한다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'
ORPHAN_REL_RID39 = '<Relationship Id="rId39" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image2.png"/>'

ANCHOR_STRINGS = {
    'P96_OLD': P96_OLD,
    'P97_OLD': P97_OLD,
    'P626_OLD': P626_OLD,
    'FIG2_BLOCK_OLD': FIG2_BLOCK_OLD,
    'SEC54_INTRO': SEC54_INTRO,
    'P85_OLD': P85_OLD,
}

def read_docx_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def read_docx_rels(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/_rels/document.xml.rels").decode("utf-8")


def root_open_tag(xml_str):
    start = xml_str.index("<w:document")
    end = xml_str.index(">", start) + 1
    return xml_str[start:end]


# 빈 문단은 <w:p .../> 로 자체닫힘(self-closing)될 수 있다 — 이 경우 뒤에
# 짝이 되는 </w:p>가 따로 없으므로, 예전 패턴(항상 열림+</w:p> 짝을 찾음)은
# 자체닫힘 문단의 "몸통"을 다음 문단 전체까지로 잘못 삼켜버린다(실제로
# stage7 개발 중 paraId 7B6AD9DC에서 이 버그로 인접 문단이 통째로 안
# 잡히는 사고가 났다 — 반드시 self-closing 분기를 먼저 시도해야 함).
PARA_RE = re.compile(
    r'<w:p w14:paraId="([0-9A-Fa-f]{8})"[^>]*?(?:/>|(?<!/)>(.*?)</w:p>)', re.DOTALL)


def para_map(xml_str):
    out = {}
    for m in PARA_RE.finditer(xml_str):
        pid, body = m.group(1), m.group(2)
        out[pid] = body or ""
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                     help="검증만 하고 실제 파일은 하나도 안 바꾼다")
    args = ap.parse_args()

    if not os.path.isfile(DOCX):
        print(f"FATAL: not found: {DOCX}")
        sys.exit(1)

    print(f"대상: {DOCX}")
    orig_xml = read_docx_xml(DOCX)
    orig_rels = read_docx_rels(DOCX)
    orig_root_open = root_open_tag(orig_xml)

    # ---- 1) 앵커 유일성(count==1) 사전 검증 ----
    problems = []
    for name, s in ANCHOR_STRINGS.items():
        c = orig_xml.count(s)
        if c != 1:
            problems.append(f"{name}: count != 1 (got {c})")
    if orig_rels.count(ORPHAN_REL_RID39) != 1:
        problems.append("ORPHAN_REL_RID39: count != 1")
    if problems:
        print("FATAL: 앵커 검증 실패, 아무 것도 안 씀:")
        for p in problems:
            print("  -", p)
        sys.exit(2)
    print(f"앵커 검증 통과: {len(ANCHOR_STRINGS)}건 + rels 앵커 전부 count==1")

    # ---- 2) 적용 ----
    new_xml = orig_xml
    new_xml = new_xml.replace(P96_OLD, P96_NEW, 1)
    new_xml = new_xml.replace(P97_OLD, "", 1)
    new_xml = new_xml.replace(P626_OLD, P626_NEW, 1)
    # 그림2 이동: 옛 자리에서 제거 후 §5.4 도입 문단 뒤에 재삽입
    assert new_xml.count(FIG2_BLOCK_OLD) == 1
    new_xml = new_xml.replace(FIG2_BLOCK_OLD, "", 1)
    assert new_xml.count(SEC54_INTRO) == 1
    new_xml = new_xml.replace(SEC54_INTRO, SEC54_INTRO + FIG2_BLOCK_OLD, 1)
    new_xml = new_xml.replace(P85_OLD, P85_NEW, 1)

    new_rels = orig_rels.replace(ORPHAN_REL_RID39, "", 1)

    # ---- 3) 그림2 이동 자체를 위치 기반으로 검증(diff 감사가 못 잡는 종류) ----
    move_checks = []
    # 두 체크를 합치면 충분하다: 그림2 블록이 "문서 전체에 딱 1번"만 있고,
    # 그 1번이 "SEC54_INTRO 바로 뒤"라면 -- 옛 자리(§5.4 끝)에는 더 이상
    # 없고 새 자리(§5.4 도입부 뒤)에만 있다는 뜻이 논리적으로 확정된다.
    move_checks.append(("그림2 블록이 새 위치(§5.4 도입부 뒤)에 정확히 1번 존재",
                         new_xml.count(SEC54_INTRO + FIG2_BLOCK_OLD) == 1, ""))
    move_checks.append(("그림2 블록이 문서 전체에 정확히 1번만 존재(중복/누락 없음)",
                         new_xml.count(FIG2_BLOCK_OLD) == 1, ""))

    # ---- 4) 전수 문단 diff 감사(이동으로는 안 바뀌는 paraId 집합만 검사) ----
    old_map = para_map(orig_xml)
    new_map = para_map(new_xml)
    deleted_ids = set(old_map) - set(new_map)
    inserted_ids = set(new_map) - set(old_map)
    modified_ids = {pid for pid in (set(old_map) & set(new_map)) if old_map[pid] != new_map[pid]}

    diff_problems = []
    if deleted_ids != EXPECTED_DELETED:
        diff_problems.append(f"삭제된 paraId 불일치: 실제={deleted_ids} 기대={EXPECTED_DELETED}")
    if inserted_ids != EXPECTED_INSERTED:
        diff_problems.append(f"삽입된 paraId 불일치: 실제={inserted_ids} 기대={EXPECTED_INSERTED}")
    if modified_ids != EXPECTED_MODIFIED:
        missing = EXPECTED_MODIFIED - modified_ids
        extra = modified_ids - EXPECTED_MODIFIED
        diff_problems.append(f"수정된 paraId 불일치: 누락={missing} 예상외={extra}")

    print()
    print("전수 문단 diff 감사 (그림2 이동은 아래 별도 위치 체크로 검증):")
    print(f"  삭제 {len(deleted_ids)}건 / 삽입 {len(inserted_ids)}건 / 수정 {len(modified_ids)}건")
    if diff_problems:
        print("FATAL: 의도하지 않은 변경이 섞여 있음 — 아무 것도 안 씀:")
        for p in diff_problems:
            print("  -", p)
        sys.exit(3)
    print("  [OK] 변경된 paraId 집합이 의도한 것과 정확히 1:1 일치")

    # ---- 5) 결과 검증 ----
    checks = list(move_checks)
    try:
        new_root = ET.fromstring(new_xml)
        checks.append(("well-formed XML (document.xml)", True, ""))
    except Exception as e:
        checks.append(("well-formed XML (document.xml)", False, str(e)))
        new_root = None
    try:
        ET.fromstring(new_rels)
        checks.append(("well-formed XML (document.xml.rels)", True, ""))
    except Exception as e:
        checks.append(("well-formed XML (document.xml.rels)", False, str(e)))

    new_root_open = root_open_tag(new_xml)
    checks.append(("루트 <w:document> 태그 불변", new_root_open == orig_root_open, ""))

    if new_root is not None:
        old_root = ET.fromstring(orig_xml)
        old_count = len(list(old_root.iter("{%s}p" % W_NS)))
        new_count = len(list(new_root.iter("{%s}p" % W_NS)))
        delta = new_count - old_count
        checks.append((f"문단 수 델타 == {EXPECTED_PARA_DELTA} (실제 {old_count}->{new_count}, delta {delta})",
                        delta == EXPECTED_PARA_DELTA, ""))
    else:
        checks.append(("문단 수 델타 확인", False, "well-formed 실패로 건너뜀"))

    checks.append(('rels에서 고아 rId39 제거됨', 'Id="rId39"' not in new_rels, "여전히 남아있음"))

    must_be_absent = [
        "코드 수정은 일단 하지 않기로",
        "각주로 넣을지 판단할 것",
        "총 배출량이 최대 65.93% 감소하였다",  # 서론 옛 헤드라인
    ]
    for s in must_be_absent:
        checks.append((f"부재 확인: {s[:30]}", s not in new_xml, "여전히 남아있음"))
    # 참고: "⚠ 이 가설은 용량 스윕..." 문단(75)은 이번 stage7에서 안 건드린다
    # (be 지시로 stage9로 이관 — 표5/§6.5가 롤링 기준으로 재구성된 뒤 처리).
    # 그러니 그 문구는 지금 문서에 ** 그대로 남아있어야 정상 **이라 부재
    # 확인 목록에서 뺐다 — 넣으면 매번 FAIL 나는 잘못된 체크가 된다.

    must_be_present = [
        "총 배출량이 62.94% 감소하였다",
        "6.4절에서 온라인 용량 인지 알고리즘으로 확정한다",
        "Long Short-Term Memory, 장단기 기억 신경망",
    ]
    for s in must_be_present:
        checks.append((f"존재 확인: {s[:30]}", s in new_xml, "안 보임"))

    all_ok = all(ok for _, ok, _ in checks)
    print()
    print("결과 검증:")
    for name, ok, detail in checks:
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not ok else ""))

    if not all_ok:
        print("\nFATAL: 검증 실패, 아무 파일도 안 씀.")
        sys.exit(4)

    if args.dry_run:
        print("\n--dry-run 이므로 여기서 멈춘다. 실제 파일은 하나도 안 바뀜.")
        sys.exit(0)

    # ---- 6) 스냅샷 ----
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    snapshot_path = os.path.join(VERSIONS_DIR, f"CAST_{ts}_E8통독1차전.docx")
    shutil.copy2(DOCX, snapshot_path)
    print(f"\n스냅샷: {snapshot_path}")

    # ---- 7) 원자적 쓰기 (document.xml + rels + image2.png 제외) ----
    new_docx_path = DOCX + ".new"
    if os.path.exists(new_docx_path):
        os.remove(new_docx_path)

    with zipfile.ZipFile(DOCX, "r") as src, \
         zipfile.ZipFile(new_docx_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if item.filename == "word/media/image2.png":
                continue
            data = src.read(item.filename)
            if item.filename == "word/document.xml":
                data = new_xml.encode("utf-8")
            elif item.filename == "word/_rels/document.xml.rels":
                data = new_rels.encode("utf-8")
            dst.writestr(item, data)

    with zipfile.ZipFile(new_docx_path) as check_zip:
        assert "word/media/image2.png" not in check_zip.namelist(), "image2.png 정리 안 됨"
    print("image2.png 패키지에서 제거 확인 — OK")

    # ---- 8) python-docx 로드 검증 ----
    try:
        import docx
        docx.Document(new_docx_path)
        print("python-docx 로드: OK")
    except ImportError:
        print("python-docx 미설치 — 이 검증은 건너뜀")
    except Exception as e:
        print(f"FATAL: python-docx 로드 실패: {e}")
        os.remove(new_docx_path)
        sys.exit(5)

    # ---- 9) 원자적 교체 ----
    os.replace(new_docx_path, DOCX)
    print(f"\n완료: {DOCX} 갱신됨. 스냅샷은 {snapshot_path} 에 보존.")
    print("Word로 열어 육안 확인 권장 — 특히 그림2가 §5.4 앞쪽, 그림4보다 먼저 오는지.")


if __name__ == "__main__":
    main()
