"""
apply_stage18b.py — 투고본에 남아있던 인라인 URL 3건 제거.
작성: 2026-09-22, carbon-aware-scheduler-4d(원고 트랙). 실행은 be가 한다.

** paper/CAST_투고본.docx에만 적용한다 — paper/CAST.docx(원본)는
전혀 안 건드린다. ** stage18이 지운 건 파란(1155CC) 인용 장치뿐이었는데,
이 3건은 stage8(근거 필요 해소)에서 검정 글자 그대로 괄호 안에 넣은
URL이라 색상 필터에 안 걸렸다 — be가 재검증하다 찾아냈다.

검증도 강화했다: 'https://' 문자열이 문서 전체에 0건인지까지 확인한다
(1155CC 색상 검사만으로는 이런 검정-텍스트 URL을 못 잡는다는 게
이번에 증명됐다).
"""
import sys, os, shutil, zipfile, datetime, argparse, re
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCX = os.path.join(REPO, "paper", "CAST_투고본.docx")  # 원본(CAST.docx) 아님
VERSIONS_DIR = os.path.join(REPO, "paper", "versions")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

REPLACEMENTS = [  # (paraid, old_frag, new_frag)
    ('52F7E9F4', '<w:p w14:paraId="52F7E9F4" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:r><w:t>작업</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>집합을</w:t></w:r><w:r><w:t xml:space="preserve"> J, </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>집합을</w:t></w:r><w:r><w:t xml:space="preserve"> R, </w:t></w:r><w:r><w:t>슬롯</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>집합을</w:t></w:r><w:r><w:t xml:space="preserve"> T</w:t></w:r><w:r><w:t>로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>둔다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>슬롯</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>길이는</w:t></w:r><w:r><w:t xml:space="preserve"> 1</w:t></w:r><w:r><w:t>시간이며</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>탄소집약도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>데이터의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>해상도와</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>일치시킨</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>값이다</w:t></w:r><w:r><w:t>(Electricity Maps</w:t></w:r><w:r><w:t>는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단위로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소집약도를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>제공한다</w:t></w:r><w:r><w:t xml:space="preserve">, https://www.electricitymaps.com/data/methodology). </w:t></w:r><w:r><w:t>작업</w:t></w:r><w:r><w:t xml:space="preserve"> j</w:t></w:r><w:r><w:t>는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>출발</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> o_j, </w:t></w:r><w:r><w:t>제출</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시각</w:t></w:r><w:r><w:t xml:space="preserve"> s_j, </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> d_j, </w:t></w:r><w:r><w:t>지연</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>등급</w:t></w:r><w:r><w:t xml:space="preserve"> k_j, </w:t></w:r><w:r><w:t>지연</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>예산</w:t></w:r><w:r><w:t xml:space="preserve"> L_j</w:t></w:r><w:r><w:t>를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>갖는다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>작업의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>마감은</w:t></w:r><w:r><w:t xml:space="preserve"> D_j = s_j + L_j + d_j</w:t></w:r><w:r><w:t>다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>', '<w:p w14:paraId="52F7E9F4" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:r><w:t>작업</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>집합을</w:t></w:r><w:r><w:t xml:space="preserve"> J, </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>집합을</w:t></w:r><w:r><w:t xml:space="preserve"> R, </w:t></w:r><w:r><w:t>슬롯</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>집합을</w:t></w:r><w:r><w:t xml:space="preserve"> T</w:t></w:r><w:r><w:t>로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>둔다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>슬롯</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>길이는</w:t></w:r><w:r><w:t xml:space="preserve"> 1</w:t></w:r><w:r><w:t>시간이며</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>탄소집약도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>데이터의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>해상도와</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>일치시킨</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t><w:t>값이다</w:t></w:t></w:r><w:r><w:t xml:space="preserve"><w:t xml:space="preserve">. </w:t></w:t></w:r><w:r><w:t>작업</w:t></w:r><w:r><w:t xml:space="preserve"> j</w:t></w:r><w:r><w:t>는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>출발</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> o_j, </w:t></w:r><w:r><w:t>제출</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시각</w:t></w:r><w:r><w:t xml:space="preserve"> s_j, </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> d_j, </w:t></w:r><w:r><w:t>지연</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>등급</w:t></w:r><w:r><w:t xml:space="preserve"> k_j, </w:t></w:r><w:r><w:t>지연</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>예산</w:t></w:r><w:r><w:t xml:space="preserve"> L_j</w:t></w:r><w:r><w:t>를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>갖는다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>작업의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>마감은</w:t></w:r><w:r><w:t xml:space="preserve"> D_j = s_j + L_j + d_j</w:t></w:r><w:r><w:t>다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'),
    ('4FD55E2D', '<w:p w14:paraId="4FD55E2D" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:r><w:t>평가는</w:t></w:r><w:r><w:t xml:space="preserve"> 8</w:t></w:r><w:r><w:t>개</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전의</w:t></w:r><w:r><w:t xml:space="preserve"> 2025</w:t></w:r><w:r><w:t>년</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실측</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소집약도</w:t></w:r><w:r><w:t xml:space="preserve"> 1</w:t></w:r><w:r><w:t>년치</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>위에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>수행한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>탄소집약도는</w:t></w:r><w:r><w:t xml:space="preserve"> Electricity Maps API</w:t></w:r><w:r><w:t>를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>통해</w:t></w:r><w:r><w:t xml:space="preserve"> 1</w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>해상도로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>수집하였다</w:t></w:r><w:r><w:t xml:space="preserve"> — </w:t></w:r><w:r><w:t>발전과</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>설비를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>모두</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>포함하는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>전과정</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>배출계수</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>체계를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>쓰는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>공식</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>방법론이다</w:t></w:r><w:r><w:t>(https://www.electricitymaps.com/data/methodology).</w:t></w:r></w:p>', '<w:p w14:paraId="4FD55E2D" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:r><w:t>평가는</w:t></w:r><w:r><w:t xml:space="preserve"> 8</w:t></w:r><w:r><w:t>개</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전의</w:t></w:r><w:r><w:t xml:space="preserve"> 2025</w:t></w:r><w:r><w:t>년</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실측</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소집약도</w:t></w:r><w:r><w:t xml:space="preserve"> 1</w:t></w:r><w:r><w:t>년치</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>위에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>수행한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>탄소집약도는</w:t></w:r><w:r><w:t xml:space="preserve"> Electricity Maps API</w:t></w:r><w:r><w:t>를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>통해</w:t></w:r><w:r><w:t xml:space="preserve"> 1</w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>해상도로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>수집하였다</w:t></w:r><w:r><w:t xml:space="preserve"> — </w:t></w:r><w:r><w:t>발전과</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>설비를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>모두</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>포함하는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>전과정</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>배출계수</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>체계를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>쓰는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>공식</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t><w:t>방법론이다</w:t></w:t></w:r><w:r><w:t><w:t>.</w:t></w:t></w:r></w:p>'),
    ('60C0E1E4', '<w:p w14:paraId="60C0E1E4" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:r><w:t>네트워크</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>지연은</w:t></w:r><w:r><w:t xml:space="preserve"> 8×8 </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>왕복</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>지연</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실측</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>행렬을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>사용하며</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>최댓값은</w:t></w:r><w:r><w:t xml:space="preserve"> 244ms, </w:t></w:r><w:r><w:t>비대각</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>최솟값은</w:t></w:r><w:r><w:t xml:space="preserve"> 12ms</w:t></w:r><w:r><w:t>다</w:t></w:r><w:r><w:t xml:space="preserve"> — Azure </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>왕복</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>지연</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>통계다</w:t></w:r><w:r><w:t xml:space="preserve">(https://learn.microsoft.com/en-us/azure/networking/azure-network-latency). </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량은</w:t></w:r><w:r><w:t xml:space="preserve"> 8</w:t></w:r><w:r><w:t>개</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>균일하게</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>부여한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>기준</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>배정에서의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전별</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>최대</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>동시</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>수에</w:t></w:r><w:r><w:t xml:space="preserve"> 1.2</w:t></w:r><w:r><w:t>를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>곱해</w:t></w:r><w:r><w:t xml:space="preserve"> 16</w:t></w:r><w:r><w:t>을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>얻고</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>여기에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>여유율</w:t></w:r><w:r><w:t xml:space="preserve"> 0.8</w:t></w:r><w:r><w:t>을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>적용하여</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>유효</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>상한</w:t></w:r><w:r><w:t xml:space="preserve"> 12</w:t></w:r><w:r><w:t>를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>사용한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>정수</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>계획</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>문제는</w:t></w:r><w:r><w:t xml:space="preserve"> PuLP </w:t></w:r><w:r><w:t>인터페이스를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>통해</w:t></w:r><w:r><w:t xml:space="preserve"> CBC </w:t></w:r><w:r><w:t>솔버로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>푼다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>', '<w:p w14:paraId="60C0E1E4" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:r><w:t>네트워크</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>지연은</w:t></w:r><w:r><w:t xml:space="preserve"> 8×8 </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>왕복</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>지연</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실측</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>행렬을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>사용하며</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>최댓값은</w:t></w:r><w:r><w:t xml:space="preserve"> 244ms, </w:t></w:r><w:r><w:t>비대각</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>최솟값은</w:t></w:r><w:r><w:t xml:space="preserve"> 12ms</w:t></w:r><w:r><w:t>다</w:t></w:r><w:r><w:t xml:space="preserve"> — Azure </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>왕복</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>지연</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t><w:t>통계다</w:t></w:t></w:r><w:r><w:t xml:space="preserve"><w:t xml:space="preserve">. </w:t></w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량은</w:t></w:r><w:r><w:t xml:space="preserve"> 8</w:t></w:r><w:r><w:t>개</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>균일하게</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>부여한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>기준</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>배정에서의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전별</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>최대</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>동시</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>수에</w:t></w:r><w:r><w:t xml:space="preserve"> 1.2</w:t></w:r><w:r><w:t>를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>곱해</w:t></w:r><w:r><w:t xml:space="preserve"> 16</w:t></w:r><w:r><w:t>을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>얻고</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>여기에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>여유율</w:t></w:r><w:r><w:t xml:space="preserve"> 0.8</w:t></w:r><w:r><w:t>을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>적용하여</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>유효</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>상한</w:t></w:r><w:r><w:t xml:space="preserve"> 12</w:t></w:r><w:r><w:t>를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>사용한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>정수</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>계획</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>문제는</w:t></w:r><w:r><w:t xml:space="preserve"> PuLP </w:t></w:r><w:r><w:t>인터페이스를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>통해</w:t></w:r><w:r><w:t xml:space="preserve"> CBC </w:t></w:r><w:r><w:t>솔버로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>푼다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'),
]

EXPECTED_MODIFIED = set(['4FD55E2D', '52F7E9F4', '60C0E1E4'])
EXPECTED_DELETED = set()
EXPECTED_INSERTED = set()
EXPECTED_PARA_DELTA = 0

def read_docx_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def root_open_tag(xml_str):
    start = xml_str.index("<w:document")
    end = xml_str.index(">", start) + 1
    return xml_str[start:end]


PARA_RE = re.compile(
    r'<w:p w14:paraId="([0-9A-Za-z]{8})"[^>]*?(?:/>|(?<!/)>(.*?)</w:p>)', re.DOTALL)


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

    print(f"대상(투고본만, 원본 CAST.docx 아님): {DOCX}")
    orig_xml = read_docx_xml(DOCX)
    orig_root_open = root_open_tag(orig_xml)

    # ---- 1) 앵커 검증 ----
    problems = []
    for pid, old_frag, new_frag in REPLACEMENTS:
        c = orig_xml.count(old_frag)
        if c != 1:
            problems.append(f"{pid}: count != 1 (got {c})")
    if problems:
        print("FATAL: 앵커 검증 실패, 아무 것도 안 씀:")
        for p in problems:
            print("  -", p)
        sys.exit(2)
    print(f"앵커 검증 통과: {len(REPLACEMENTS)}건")

    # ---- 2) 적용 ----
    new_xml = orig_xml
    for pid, old_frag, new_frag in REPLACEMENTS:
        assert new_xml.count(old_frag) == 1, f"{pid}: 치환 도중 앵커가 사라짐/중복됨"
        new_xml = new_xml.replace(old_frag, new_frag, 1)

    # ---- 3) 전수 문단 diff 감사 ----
    old_map = para_map(orig_xml)
    new_map = para_map(new_xml)
    deleted_ids = set(old_map) - set(new_map)
    inserted_ids = set(new_map) - set(old_map)
    modified_ids = {pid for pid in (set(old_map) & set(new_map)) if old_map[pid] != new_map[pid]}

    diff_problems = []
    if deleted_ids != EXPECTED_DELETED:
        diff_problems.append(f"삭제된 paraId 불일치: {deleted_ids}")
    if inserted_ids != EXPECTED_INSERTED:
        diff_problems.append(f"삽입된 paraId 불일치: {inserted_ids}")
    if modified_ids != EXPECTED_MODIFIED:
        diff_problems.append(f"수정된 paraId 불일치: 실제={modified_ids} 기대={EXPECTED_MODIFIED}")

    print()
    print("전수 문단 diff 감사:")
    print(f"  삭제 {len(deleted_ids)}건 / 삽입 {len(inserted_ids)}건 / 수정 {len(modified_ids)}건")
    if diff_problems:
        print("FATAL: 의도하지 않은 변경이 섞여 있음 — 아무 것도 안 씀:")
        for p in diff_problems:
            print("  -", p)
        sys.exit(3)
    print(f"  [OK] 의도한 3건만 수정, 삭제/삽입 0건")

    # ---- 4) 결과 검증(강화판 — https:// 전수 검사 포함) ----
    checks = []
    try:
        new_root = ET.fromstring(new_xml)
        checks.append(("well-formed XML", True, ""))
    except Exception as e:
        checks.append(("well-formed XML", False, str(e)))
        new_root = None

    new_root_open = root_open_tag(new_xml)
    checks.append(("루트 <w:document> 태그 불변", new_root_open == orig_root_open, ""))

    # ** 강화된 검증: 색상(1155CC)뿐 아니라 https:// 문자열 자체가 전무한지 **
    new_text_all = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", new_xml))
    remaining_urls = re.findall(r"https?://\S+", new_text_all)
    checks.append((f"본문에 http(s):// URL 문자열 완전 부재 (검색된 것: {len(remaining_urls)}건)",
                    len(remaining_urls) == 0, str(remaining_urls[:5])))
    checks.append(("파란 인용 색상(1155CC) 여전히 없음", "1155CC" not in new_xml, ""))

    if new_root is not None:
        old_root = ET.fromstring(orig_xml)
        old_count = len(list(old_root.iter("{%s}p" % W_NS)))
        new_count = len(list(new_root.iter("{%s}p" % W_NS)))
        delta = new_count - old_count
        checks.append((f"문단 수 델타 == {EXPECTED_PARA_DELTA} (실제 {old_count}->{new_count}, delta {delta})",
                        delta == EXPECTED_PARA_DELTA, ""))
    else:
        checks.append(("문단 수 델타 확인", False, "well-formed 실패로 건너뜀"))

    for pid, old_frag, new_frag in REPLACEMENTS:
        new_text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", new_frag))
        checks.append((f"{pid}: 더블스페이스 없음", "  " not in new_text, repr(new_text)))

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
    snapshot_path = os.path.join(VERSIONS_DIR, f"CAST_투고본_{ts}_stage18b전.docx")
    shutil.copy2(DOCX, snapshot_path)
    print(f"\n스냅샷: {snapshot_path}")

    # ---- 6) 원자적 쓰기 ----
    new_docx_path = DOCX + ".new"
    if os.path.exists(new_docx_path):
        os.remove(new_docx_path)

    with zipfile.ZipFile(DOCX, "r") as src, \
         zipfile.ZipFile(new_docx_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/document.xml":
                data = new_xml.encode("utf-8")
            dst.writestr(item, data)

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

    os.replace(new_docx_path, DOCX)
    print(f"\n완료: {DOCX} 갱신됨(투고본만). 원본 CAST.docx는 전혀 안 건드림.")
    print(f"스냅샷은 {snapshot_path} 에 보존.")


if __name__ == "__main__":
    main()
