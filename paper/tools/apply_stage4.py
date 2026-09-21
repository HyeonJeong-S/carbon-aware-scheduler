"""
apply_stage4.py — 그림 교체·신규 삽입 (그림1~6) 일괄 적용
작성: 2026-09-21, carbon-aware-scheduler-4d(원고 트랙). 실행은 be가 한다.

내용: paper/그림교체_실행계획.txt + paper/diagram/캡션.txt(확정본) 그대로.
  - 그림1(rId49/image3.png 재사용): fig1_architecture.png로 교체, 크기 확대,
    캡션·인용문 갱신. 전단(2단 스팬) — wp:anchor + wrapTopAndBottom 사용
    (이 문서에 처음 쓰는 기법 — 실제 Word 렌더링 미검증, 아래 참고).
  - 그림4(rId50/image4.png 재사용): fig4_pareto.png로 교체, 크기만 조정(단내
    유지), 캡션 갱신 + 인용문 신규 삽입(원래 없었음).
  - 옛 image1(탄소곡선) 삭제: 그림+캡션 제거, 인용 문단은 "그림 1은…" 도입부만
    빼고 나머지 사실 서술은 그대로 재작성(안B, be 승인 확정).
  - 옛 image5(막대그래프) 삭제: 그림+캡션 제거(표7과 내용 중복, 인용문 원래 없음).
  - 그림2·3(신규, 전단/wp:anchor), 그림5·6(신규, 단내/wp:inline) 삽입.
  - word/_rels/document.xml.rels에 rId55~58 신규 등록, word/media/에 이미지
    4개(image6~9.png) 신규 추가.

paper/A1_치환규칙.txt에 기록된 두 차례 사고(문단80~83, 505 유실) 이후 be가
세운 절차를 그대로 따른다:
  ① 문단 경계를 넘을 수 있는 정규식(.*?) 없음 — 전부 w14:paraId 로 고유하게
     앵커한 완전한 <w:p>...</w:p> 블록 단위로만 찾기/바꾸기/삽입한다.
  ② 쓰기 전에 전수 문단 diff를 자동으로 돌려, 실제로 바뀐 paraId 집합이
     의도한 집합(EXPECTED_MODIFIED/DELETED/INSERTED)과 정확히 1:1인지
     검증한다 — 하나라도 안 맞으면 아무 것도 안 쓴다.

** 이 스테이지만의 위험 — 꼭 읽을 것 **
  wp:anchor(플로팅, page 기준 중앙정렬 + wrapTopAndBottom)로 그림1·2·3을
  2단 폭 전체에 걸치게 하는 기법은 이 문서에 처음 쓴다(기존 그림 4개는
  전부 wp:inline이었다). 표준 OOXML 메커니즘이라 이론적으로는 맞지만,
  이 세션은 Word가 없어 실제 렌더링을 한 번도 못 봤다 — relativeHeight
  z-순서(1,2,3 — 이 문서 첫 플로팅 도형들이라 충돌 없음 확인함), 위치
  지정, 줄바꿈 방식이 전부 처음 쓰는 조합이다. 적용 후 Word로 열어
  ** 반드시 ** 육안 확인할 것 — 특히 그림이 실제로 2단 폭 전체를 채우는지,
  주변 본문이 위/아래로 자연스럽게 흐르는지.

사용법: python3 paper/tools/apply_stage4.py [--dry-run]
"""
import sys, os, shutil, zipfile, datetime, argparse, re
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCX = os.path.join(REPO, "paper", "CAST.docx")
VERSIONS_DIR = os.path.join(REPO, "paper", "versions")
DIAGRAM_DIR = os.path.join(REPO, "paper", "diagram")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

NEW_IMAGE_FILES = {
    'fig1_architecture': os.path.join(DIAGRAM_DIR, 'fig1_architecture.png'),
    'fig4_pareto': os.path.join(DIAGRAM_DIR, 'fig4_pareto.png'),
    'fig3_loadbalancer': os.path.join(DIAGRAM_DIR, 'fig3_loadbalancer.png'),
    'fig4_scheduler': os.path.join(DIAGRAM_DIR, 'fig4_scheduler.png'),
    'fig5_concurrency': os.path.join(DIAGRAM_DIR, 'fig5_concurrency.png'),
    'fig6_capacity_sweep': os.path.join(DIAGRAM_DIR, 'fig6_capacity_sweep.png'),
}

EXPECTED_MODIFIED = {'597F1B57', '6DD7D073', '1199EF54', '2EEA4567', '107EBCB6', '6C753D2F'}
EXPECTED_DELETED = {'57DF1C85', '3253E759', '6614C0B5', '132AA551'}
EXPECTED_INSERTED = {'FB000001', 'FE000001', 'FB000003', 'FC000001', 'FC000004', 'FC000002', 'FD000004', 'FB000002', 'FA000001', 'FE000003', 'FA000002', 'FE000004', 'FD000003', 'FD000001', 'FE000002', 'FB000004', 'FC000003', 'FD000002'}
EXPECTED_PARA_DELTA = 14  # 삽입 18 - 삭제 4

FIG1_DRAWING_OLD = '<w:p w14:paraId="1199EF54" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" wp14:anchorId="3D006056" wp14:editId="527C99EF"><wp:extent cx="2651760" cy="1012404"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="951" name="Picture 1"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="951" name="cast_fig_system.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId49"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="2651760" cy="1012404"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
FIG1_DRAWING_NEW = '<w:p w14:paraId="1199EF54" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:anchor distT="0" distB="0" distL="114300" distR="114300" simplePos="0" relativeHeight="1" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="page"><wp:align>center</wp:align></wp:positionH><wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV><wp:extent cx="5727700" cy="3251200"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapTopAndBottom/><wp:docPr id="951" name="Picture 951"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="951" name="fig1_architecture.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId49"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="5727700" cy="3251200"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r></w:p>'
FIG1_CAPTION_OLD = '<w:p w14:paraId="597F1B57" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 2. CAST 시스템 구성. 예측, 공간 이동, 시간 이동의 세 단계로 구성되며 각 단계는 정해진 데이터만 주고받는다.</w:t></w:r></w:p>'
FIG1_CAPTION_NEW = '<w:p w14:paraId="597F1B57" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 1. CAST의 전체 파이프라인 — 리전별 LSTM이 예측한 탄소집약도 곡선을 공간 이동과 시간 이동이 함께 쓰며, 시간 이동은 공간 이동이 계산한 슬롯별 잔여 용량을 참조해 실행 시각을 정한다.</w:t></w:r></w:p>'
FIG1_CITATION_OLD = '<w:p w14:paraId="107EBCB6" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">그림 2는 세 단계의 연결과 각 단계가 주고받는 데이터를 나타낸다.</w:t></w:r></w:p>'
FIG1_CITATION_NEW = '<w:p w14:paraId="107EBCB6" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">그림 1은 세 단계의 연결과 각 단계가 주고받는 데이터를 나타낸다.</w:t></w:r></w:p>'
FIG4_DRAWING_OLD = '<w:p w14:paraId="2EEA4567" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:lastRenderedPageBreak/><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" wp14:anchorId="112A45BC" wp14:editId="1DC203F5"><wp:extent cx="2651760" cy="2651760"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="901" name="Picture 1"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="901" name="cast_fig_pareto.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId50"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="2651760" cy="2651760"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
FIG4_DRAWING_NEW = '<w:p w14:paraId="2EEA4567" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" wp14:anchorId="0000823A" wp14:editId="0000904F"><wp:extent cx="2730500" cy="2413000"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="901" name="Picture 901"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="901" name="fig4_pareto.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId50"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="2730500" cy="2413000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
FIG4_CAPTION_OLD = '<w:p w14:paraId="6C753D2F" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 3. 지연과 탄소의 파레토 곡선. 고정 가중치 후보와 무릎점 자동 선택의 위치를 함께 나타낸다.</w:t></w:r></w:p>'
FIG4_CAPTION_NEW = '<w:p w14:paraId="6C753D2F" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 4. 고정 α 스윕과 슬롯별 무릎점(α=auto)의 파레토 곡선 — auto는 탄소가 가장 낮은 지점이 아니라 지연 대비 탄소 한계수익이 정점을 찍는 지점(464.9 kg/ms)이다.</w:t></w:r></w:p>'
FIG4_CITATION_NEW_BLOCK = '<w:p w14:paraId="FA000001" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p><w:p w14:paraId="FA000002" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">그림 4는 고정 α 스윕과 슬롯마다 다시 계산하는 무릎점 자동 α(auto)의 위치를 지연-탄소 평면에 함께 나타낸다. auto는 절감률이 가장 높은 지점이 아니라 지연 한 단위당 탄소 한계수익이 정점을 찍는 지점이다.</w:t></w:r></w:p>'
IMG1_DRAWING_OLD = '<w:p w14:paraId="3253E759" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" wp14:anchorId="62356060" wp14:editId="34BF1BAB"><wp:extent cx="2651760" cy="1547036"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="952" name="Picture 2"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="952" name="cast_fig_daily.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId30"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="2651760" cy="1547036"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
IMG1_CAPTION_OLD = '<w:p w14:paraId="57DF1C85" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>그림</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> 1. </w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>대상</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> 8</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>개</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>리전의</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>시각별</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>평균</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>탄소집약도</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> (2025</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>년</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>실측</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">, UTC </w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>기준</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">, </w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>세로축</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>로그</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>척도</w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>).</w:t></w:r></w:p>'
IMG1_CITATION_OLD = '<w:p w14:paraId="6DD7D073" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>그림</w:t></w:r><w:r><w:t xml:space="preserve"> 1</w:t></w:r><w:r><w:t>은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>대상</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소집약도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>일주기를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>나타낸다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>인도는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>석탄</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>화력</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>의존도가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>높아</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>종일</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>높은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>수준을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>유지하는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>반면</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>프랑스는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>원자력이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>기저</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>부하를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>담당하여</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>종일</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>낮고</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>평탄하다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>캘리포니아와</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>독일은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>낮</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간대</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>태양광</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>발전이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>유입되며</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>값이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>크게</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>하락한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>뒤</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>일몰</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이후</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>회복되는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>형태를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>보인다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'
IMG1_CITATION_NEW = '<w:p w14:paraId="6DD7D073" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">인도는 석탄 화력 의존도가 높아 종일 높은 수준을 유지하는 반면, 프랑스는 원자력이 기저 부하를 담당하여 종일 낮고 평탄하다. 캘리포니아와 독일은 낮 시간대 태양광 발전이 유입되며 값이 크게 하락한 뒤 일몰 이후 회복되는 형태를 보인다.</w:t></w:r></w:p>'
IMG5_DRAWING_OLD = '<w:p w14:paraId="132AA551" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" wp14:anchorId="371E8C7F" wp14:editId="2A00AA59"><wp:extent cx="2651760" cy="1178559"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="902" name="Picture 2"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="902" name="cast_fig_region.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId51"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="2651760" cy="1178559"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
IMG5_CAPTION_OLD = '<w:p w14:paraId="6614C0B5" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 4. 공간 이동 후 리전별 부하 분포. 탄소집약도가 낮은 리전으로 부하가 이동한다.</w:t></w:r></w:p>'
SEC54_END_ANCHOR = '<w:p w14:paraId="6A07E566" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p>'
SEC55_END_ANCHOR = '<w:p w14:paraId="3C36AE72" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p>'
SEC64_END_ANCHOR = '<w:p w14:paraId="1CF83842" w14:textId="77777777" w:rsidR="004D20D1" w:rsidRDefault="00000000"><w:r><w:rPr><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>나머지 6개 리전</w:t></w:r></w:p></w:tc><w:tc><w:tcPr><w:tcW w:w="560" w:type="dxa"/></w:tcPr>'
SEC65_END_ANCHOR = '><w:sz w:val="15"/><w:szCs w:val="15"/></w:rPr></w:pPr><w:r w:rsidRPr="00FA591E"><w:rPr><w:sz w:val="15"/><w:szCs w:val="15"/></w:rPr><w:t>39,513</w:t></w:r></w:p></w:tc></w:tr><w:tr w:rsidR="004D20D1" w14:paraId="5C4BDBD2" w14:textId="77777777"><w:tc><w:tcPr><w:tcW w:w="700" w:type="dxa"/></w:tcPr>'
FIG2_BLOCK = '<w:p w14:paraId="FB000001" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p><w:p w14:paraId="FB000002" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:anchor distT="0" distB="0" distL="114300" distR="114300" simplePos="0" relativeHeight="2" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="page"><wp:align>center</wp:align></wp:positionH><wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV><wp:extent cx="5727700" cy="2438400"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapTopAndBottom/><wp:docPr id="960" name="Picture 960"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="960" name="fig3_loadbalancer.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId55"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="5727700" cy="2438400"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r></w:p><w:p w14:paraId="FB000003" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 2. 공간 이동(로드밸런서) — 슬롯마다 파레토 무릎점으로 α를 자동 결정해 리전 용량 제약 안에서 작업을 배정하는 슬롯 단위 ILP.</w:t></w:r></w:p><w:p w14:paraId="FB000004" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">그림 2는 슬롯 단위 로드밸런서가 예측·지연 행렬·직전 배정을 입력받아 α를 슬롯마다 자동으로 정하고 ILP로 작업의 실행 리전을 배정하는 과정을 나타낸다.</w:t></w:r></w:p>'
FIG3_BLOCK = '<w:p w14:paraId="FC000001" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p><w:p w14:paraId="FC000002" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:anchor distT="0" distB="0" distL="114300" distR="114300" simplePos="0" relativeHeight="3" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="page"><wp:align>center</wp:align></wp:positionH><wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV><wp:extent cx="5727700" cy="2489200"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapTopAndBottom/><wp:docPr id="961" name="Picture 961"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="961" name="fig4_scheduler.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId56"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="5727700" cy="2489200"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r></w:p><w:p w14:paraId="FC000003" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 3. 시간 이동(스케줄러) — 마감 인지 탐색 윈도우 안에서 탄소·지연 가중 점수가 최소인 실행 슬롯을 고른다.</w:t></w:r></w:p><w:p w14:paraId="FC000004" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">그림 3은 마감 인지 시간 이동이 실행 가능 윈도우 안에서 탄소·지연 가중 점수가 최소인 슬롯을 선택하는 과정을 나타낸다.</w:t></w:r></w:p>'
FIG5_BLOCK = '<w:p w14:paraId="FD000001" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p><w:p w14:paraId="FD000002" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" wp14:anchorId="00008B0B" wp14:editId="00009A14"><wp:extent cx="2730500" cy="2336800"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="962" name="Picture 962"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="962" name="fig5_concurrency.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId57"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="2730500" cy="2336800"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p><w:p w14:paraId="FD000003" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 5. 시간 이동 전후 캘리포니아 리전의 동시 실행 수 — 용량을 무시하면 상한(12건)의 3.4배인 41건까지 몰리고, 온라인 용량 인지(Algorithm 1)로 19건까지 억제된다.</w:t></w:r></w:p><w:p w14:paraId="FD000004" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">그림 5는 시간 이동을 용량 제약 없이 적용했을 때(무제약)와 온라인 용량 인지 알고리즘을 적용했을 때(온라인) 캘리포니아 리전의 시간별 동시 실행 수를 비교한 것이다. 무제약에서는 상한(12건)의 3.4배인 41건까지 몰리지만, 온라인 용량 인지는 이를 19건까지 억제한다.</w:t></w:r></w:p>'
FIG6_BLOCK = '<w:p w14:paraId="FE000001" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p><w:p w14:paraId="FE000002" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" wp14:anchorId="00008B30" wp14:editId="00009A3D"><wp:extent cx="2730500" cy="2413000"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="963" name="Picture 963"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="963" name="fig6_capacity_sweep.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId58"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="2730500" cy="2413000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p><w:p w14:paraId="FE000003" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 6. 리전 용량을 기준(η·cap_r=12)의 0.5배~무제약으로 바꿔가며 본 총배출과 강제 편입 건수 — 용량이 늘수록 둘 다 줄지만 수익은 체감하며, 전 구간에서 마감 위반은 0건이다.</w:t></w:r></w:p><w:p w14:paraId="FE000004" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">그림 6은 리전 용량을 기준값의 0.5배에서 무제약까지 바꾸어 가며 측정한 총배출량과 강제 편입 건수를 나타낸다. 용량이 늘수록 총배출은 줄지만 그 수익은 체감하며, 전 구간에서 마감 위반은 발생하지 않는다.</w:t></w:r></w:p>'
REL_ANCHOR = '</Relationships>'
NEW_REL_ENTRIES = '<Relationship Id="rId55" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image6.png"/><Relationship Id="rId56" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image7.png"/><Relationship Id="rId57" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image8.png"/><Relationship Id="rId58" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image9.png"/>'

ANCHOR_STRINGS = {
    'FIG1_DRAWING_OLD': FIG1_DRAWING_OLD,
    'FIG1_CAPTION_OLD': FIG1_CAPTION_OLD,
    'FIG1_CITATION_OLD': FIG1_CITATION_OLD,
    'FIG4_DRAWING_OLD': FIG4_DRAWING_OLD,
    'FIG4_CAPTION_OLD': FIG4_CAPTION_OLD,
    'IMG1_DRAWING_OLD': IMG1_DRAWING_OLD,
    'IMG1_CAPTION_OLD': IMG1_CAPTION_OLD,
    'IMG1_CITATION_OLD': IMG1_CITATION_OLD,
    'IMG5_DRAWING_OLD': IMG5_DRAWING_OLD,
    'IMG5_CAPTION_OLD': IMG5_CAPTION_OLD,
    'SEC54_END_ANCHOR': SEC54_END_ANCHOR,
    'SEC55_END_ANCHOR': SEC55_END_ANCHOR,
    'SEC64_END_ANCHOR': SEC64_END_ANCHOR,
    'SEC65_END_ANCHOR': SEC65_END_ANCHOR,
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


PARA_RE = re.compile(r'<w:p w14:paraId="([0-9A-Fa-f]{8})"[^>]*>(.*?)</w:p>', re.DOTALL)


def para_map(xml_str):
    """paraId -> full inner XML body, for every <w:p ...> that carries a
    w14:paraId (every paragraph we ever touch has one). Comparing the raw
    body (not just extracted <w:t> text) so that a paragraph whose only
    change is structural — a <w:drawing> image swap/resize, or formatting —
    is still detected as modified even though it has no visible text at all."""
    out = {}
    for m in PARA_RE.finditer(xml_str):
        pid, body = m.group(1), m.group(2)
        out[pid] = body
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                     help="검증만 하고 실제 파일은 하나도 안 바꾼다")
    args = ap.parse_args()

    if not os.path.isfile(DOCX):
        print(f"FATAL: not found: {DOCX}")
        sys.exit(1)
    for label, path in NEW_IMAGE_FILES.items():
        if not os.path.isfile(path):
            print(f"FATAL: 이미지 파일 없음 ({label}): {path}")
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
    if orig_rels.count(REL_ANCHOR) != 1:
        problems.append("REL_ANCHOR (</Relationships>) count != 1")
    if problems:
        print("FATAL: 앵커 검증 실패, 아무 것도 안 씀:")
        for p in problems:
            print("  -", p)
        sys.exit(2)
    print(f"앵커 검증 통과: {len(ANCHOR_STRINGS)}건 전부 count==1 (document.xml), rels 앵커도 OK")

    # ---- 2) 치환/삭제/삽입 적용 (메모리 안에서만) ----
    new_xml = orig_xml

    # 2a. 재사용 슬롯(그림1/그림4) 갱신
    new_xml = new_xml.replace(FIG1_DRAWING_OLD, FIG1_DRAWING_NEW, 1)
    new_xml = new_xml.replace(FIG1_CAPTION_OLD, FIG1_CAPTION_NEW, 1)
    new_xml = new_xml.replace(FIG1_CITATION_OLD, FIG1_CITATION_NEW, 1)
    new_xml = new_xml.replace(FIG4_DRAWING_OLD, FIG4_DRAWING_NEW, 1)
    new_xml = new_xml.replace(FIG4_CAPTION_OLD, FIG4_CAPTION_NEW + FIG4_CITATION_NEW_BLOCK, 1)

    # 2b. 옛 image1(탄소곡선): 그림+캡션 삭제, 인용문 재작성
    new_xml = new_xml.replace(IMG1_DRAWING_OLD, "", 1)
    new_xml = new_xml.replace(IMG1_CAPTION_OLD, "", 1)
    new_xml = new_xml.replace(IMG1_CITATION_OLD, IMG1_CITATION_NEW, 1)

    # 2c. 옛 image5(막대그래프): 그림+캡션 삭제
    new_xml = new_xml.replace(IMG5_DRAWING_OLD, "", 1)
    new_xml = new_xml.replace(IMG5_CAPTION_OLD, "", 1)

    # 2d. 신규 그림 2/3/5/6 삽입 (각 절 끝, 다음 절 제목 앞)
    new_xml = new_xml.replace(SEC54_END_ANCHOR, SEC54_END_ANCHOR + FIG2_BLOCK, 1)
    new_xml = new_xml.replace(SEC55_END_ANCHOR, SEC55_END_ANCHOR + FIG3_BLOCK, 1)
    new_xml = new_xml.replace(SEC64_END_ANCHOR, SEC64_END_ANCHOR + FIG5_BLOCK, 1)
    new_xml = new_xml.replace(SEC65_END_ANCHOR, SEC65_END_ANCHOR + FIG6_BLOCK, 1)

    new_rels = orig_rels.replace(REL_ANCHOR, NEW_REL_ENTRIES + REL_ANCHOR, 1)

    # ---- 3) 전수 문단 diff 감사 (be 신규 절차 규칙 ②) ----
    # "의도한 paraId만 바뀌었는가"를 자동으로 검증한다 — 쓰기 전에.
    old_map = para_map(orig_xml)
    new_map = para_map(new_xml)

    deleted_ids = set(old_map) - set(new_map)
    inserted_ids = set(new_map) - set(old_map)
    modified_ids = {pid for pid in (set(old_map) & set(new_map)) if old_map[pid] != new_map[pid]}

    diff_problems = []
    if deleted_ids != EXPECTED_DELETED:
        diff_problems.append(f"삭제된 paraId 불일치: 실제={deleted_ids} 기대={EXPECTED_DELETED}")
    if inserted_ids != EXPECTED_INSERTED:
        missing = EXPECTED_INSERTED - inserted_ids
        extra = inserted_ids - EXPECTED_INSERTED
        diff_problems.append(f"삽입된 paraId 불일치: 누락={missing} 예상외={extra}")
    if modified_ids != EXPECTED_MODIFIED:
        missing = EXPECTED_MODIFIED - modified_ids
        extra = modified_ids - EXPECTED_MODIFIED
        diff_problems.append(f"수정된 paraId 불일치: 누락={missing} 예상외={extra}")

    print()
    print("전수 문단 diff 감사 (be 절차 규칙 ②):")
    print(f"  삭제 {len(deleted_ids)}건 / 삽입 {len(inserted_ids)}건 / 수정 {len(modified_ids)}건")
    if diff_problems:
        print("FATAL: 의도하지 않은 변경이 섞여 있음 — 아무 것도 안 씀:")
        for p in diff_problems:
            print("  -", p)
        sys.exit(3)
    print("  [OK] 변경된 paraId 집합이 의도한 것과 정확히 1:1 일치")

    # ---- 4) 결과 검증 ----
    checks = []
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

    for rid in ["rId55", "rId56", "rId57", "rId58"]:
        checks.append((f"rels에 {rid} 존재", f'Id="{rid}"' in new_rels, ""))
    for rid in ["rId49", "rId50"]:
        checks.append((f"rels에 {rid} 그대로 유지", f'Id="{rid}"' in new_rels, ""))

    must_be_absent = [
        "cast_fig_daily.png",   # 옛 image1 drawing 잔재
        "cast_fig_region.png",  # 옛 image5 drawing 잔재
        "그림 1. 대상 8개 리전의 시각별",  # 옛 그림1 캡션
        "그림 4. 공간 이동 후 리전별 부하 분포",  # 옛 그림4(막대) 캡션
    ]
    for s in must_be_absent:
        checks.append((f"부재 확인: {s[:30]}", s not in new_xml, "여전히 남아있음"))

    must_be_present = [
        "fig1_architecture.png", "fig3_loadbalancer.png", "fig4_scheduler.png",
        "fig4_pareto.png", "fig5_concurrency.png", "fig6_capacity_sweep.png",
        "그림 2. 공간 이동(로드밸런서)", "그림 3. 시간 이동(스케줄러)",
        "그림 5. 시간 이동 전후", "그림 6. 리전 용량을",
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

    # ---- 5) 스냅샷 ----
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    snapshot_path = os.path.join(VERSIONS_DIR, f"CAST_{ts}_그림교체전.docx")
    shutil.copy2(DOCX, snapshot_path)
    print(f"\n스냅샷: {snapshot_path}")

    # ---- 6) 새 docx를 .new 경로에 원자적으로 조립 (document.xml + rels + 이미지 6종) ----
    new_docx_path = DOCX + ".new"
    if os.path.exists(new_docx_path):
        os.remove(new_docx_path)

    image_bytes = {}
    for label, path in NEW_IMAGE_FILES.items():
        with open(path, "rb") as f:
            image_bytes[label] = f.read()

    with zipfile.ZipFile(DOCX, "r") as src, \
         zipfile.ZipFile(new_docx_path, "w", zipfile.ZIP_DEFLATED) as dst:
        written = set()
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/document.xml":
                data = new_xml.encode("utf-8")
            elif item.filename == "word/_rels/document.xml.rels":
                data = new_rels.encode("utf-8")
            elif item.filename == "word/media/image3.png":
                data = image_bytes["fig1_architecture"]
            elif item.filename == "word/media/image4.png":
                data = image_bytes["fig4_pareto"]
            dst.writestr(item, data)
            written.add(item.filename)
        # 완전히 새로운 media 파일 4개 추가
        for target, label in [("word/media/image6.png", "fig3_loadbalancer"),
                               ("word/media/image7.png", "fig4_scheduler"),
                               ("word/media/image8.png", "fig5_concurrency"),
                               ("word/media/image9.png", "fig6_capacity_sweep")]:
            assert target not in written, f"{target} 이미 존재함 — 충돌"
            dst.writestr(target, image_bytes[label])

    # ---- 7) python-docx 로드 검증 ----
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

    # ---- 8) 원자적 교체 ----
    os.replace(new_docx_path, DOCX)
    print(f"\n완료: {DOCX} 갱신됨. 스냅샷은 {snapshot_path} 에 보존.")
    print("Word로 열어 육안 확인 필수 — 특히 그림1·2·3(전단/2단 스팬, wp:anchor 처음 씀)의")
    print("실제 레이아웃, 그림4~6(단내) 위치, image1/image5 삭제 후 본문 흐름 확인.")


if __name__ == "__main__":
    main()
