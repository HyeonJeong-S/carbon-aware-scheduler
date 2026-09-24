# -*- coding: utf-8 -*-
"""압축본 끝에 참고문헌 절을 붙인다.

압축본에는 서지 목록이 아예 없다(본문 인용 표시도 0건). 학술지 투고본으로는
성립하지 않는다. 서지 자체는 paper/문서/참고문헌_초안.txt 에 KTCP·JKIICE 두
서식으로 이미 완성·대조돼 있으므로, 여기서는 그 목록을 문서에 넣기만 한다.

서식은 KTCP(학회비교.txt 1순위, DOI 없음, Vol./No. 대문자)를 기본으로 한다.
JKIICE 로 바꾸려면 FORMAT 을 "jkiice" 로 두면 된다 — 두 서식의 차이는
DOI 유무와 vol/no 대소문자뿐이다.

본문 [n] 삽입은 이 스크립트가 하지 않는다. 그 위치 대조는 별도 작업이다.
"""
import shutil
import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"

# paper/문서/참고문헌_초안.txt A절(KTCP 서식) 그대로. 줄바꿈은 뺀다.
# 번호는 **압축본에서의 첫 등장 순서**다 — paper/문서/인용위치_대조.txt(fd) 기준.
# 서지 자체는 paper/문서/참고문헌_초안.txt A절(KTCP 서식, DOI 없음)에서 옮겼고,
# 압축본이 인용하지 않는 셋(Google 24/7 CFE · Asadov 리뷰 · CarbonCast 확장판)은
# 뺐다 — 인용되지 않는 항목을 목록에 두는 것은 서식 오류다.
KTCP = [
 # [1]
 "International Energy Agency, Energy and AI, World Energy Outlook Special Report, "
 "IEA, Paris, 2025.",
 # [2]
 "European Parliament and Council, Directive (EU) 2023/1791 of the European Parliament "
 "and of the Council of 13 September 2023 on Energy Efficiency (recast), Official "
 "Journal of the European Union, 2023.",
 # [3] CICS
 "A. Radovanović, R. Koningstein, I. Schneider, B. Chen, A. Duarte, B. Roy, D. Xiao, "
 "M. Haridasan, P. Hung, N. Care, S. Talukdar, E. Mullen, K. Smith, M. Cottman, and "
 "W. Cirne, “Carbon-Aware Computing for Datacenters,” IEEE Transactions on "
 "Power Systems, Vol. 38, No. 2, pp. 1270-1280, Mar. 2023.",
 # [4] CASPER
 "A. Souza, S. Jasoria, B. Chakrabarty, A. Bridgwater, A. Lundberg, F. Skogh, D. Irwin, "
 "P. Shenoy, and A. Ali-Eldin, “CASPER: Carbon-Aware Scheduling and Provisioning "
 "for Distributed Web Services,” Proc. of the 14th Int. Green and Sustainable "
 "Computing Conf. (IGSC), Toronto, Canada, 2023.",
 # [5] VMware GSLB
 "D. Maji, B. Pfaff, V. P R, R. Sreenivasan, V. Firoiu, S. Iyer, C. Josephson, Z. Pan, "
 "and R. K. Sitaraman, “Bringing Carbon Awareness to Multi-Cloud Application "
 "Delivery,” Proc. of the 2nd Workshop on Sustainable Computer Systems "
 "(HotCarbon), Boston, USA, pp. 1-6, Jul. 2023.",
 # [6] Sukprasert
 "T. Sukprasert, A. Souza, N. Bashir, D. Irwin, and P. Shenoy, “On the Limitations "
 "of Carbon-Aware Temporal and Spatial Workload Shifting in the Cloud,” Proc. of "
 "the 19th European Conf. on Computer Systems (EuroSys), Athens, Greece, pp. 924-941, "
 "Apr. 2024.",
 # [7] CarbonFlex
 "W. A. Hanafy, L. Wu, D. Irwin, and P. Shenoy, “CarbonFlex: Enabling Carbon-aware "
 "Provisioning and Scheduling for Cloud Clusters,” arXiv:2505.18357, 2025.",
 # [8] Attenni
 "G. Attenni, Y. Moawad, N. Bartolini, and L. Thamsen, “Spatio-Temporal Shifting "
 "to Reduce Carbon, Water, and Land-Use Footprints of Cloud Workloads,” "
 "arXiv:2512.08725, 2025.",
 # [9] Caspian
 "T. Bahreini, A. N. Tantawi, and O. Tardieu, “Caspian: A Carbon-aware Workload "
 "Scheduler in Multi-Cluster Kubernetes Environments,” Proc. of the 32nd IEEE Int. "
 "Symp. on Modeling, Analysis, and Simulation of Computer and Telecommunication Systems "
 "(MASCOTS), Krakow, Poland, pp. 1-8, Oct. 2024.",
 # [10]
 "Electricity Maps. (2026, Sep. 22). Data Portal [Online]. Available: "
 "https://www.electricitymaps.com/data-portal",
 # [11]
 "Electricity Maps. (2026, Sep. 22). Methodology [Online]. Available: "
 "https://www.electricitymaps.com/data/methodology",
 # [12]
 "Microsoft. (2026, Sep. 22). Azure Network Round-Trip Latency Statistics [Online]. "
 "Available: https://learn.microsoft.com/en-us/azure/networking/azure-network-latency",
 # [13] DACF
 "D. Maji, R. K. Sitaraman, and P. Shenoy, “DACF: Day-Ahead Carbon Intensity "
 "Forecasting of Power Grids using Machine Learning,” Proc. of the 13th ACM Int. "
 "Conf. on Future Energy Systems (e-Energy), pp. 188-192, Jun.-Jul. 2022.",
 # [14] CarbonCast
 "D. Maji, P. Shenoy, and R. K. Sitaraman, “CarbonCast: Multi-Day Forecasting of "
 "Grid Carbon Intensity,” Proc. of the 9th ACM Int. Conf. on Systems for "
 "Energy-Efficient Buildings, Cities, and Transportation (BuildSys), Boston, USA, "
 "pp. 198-207, Nov. 2022.",
]

def add(doc, entries, size=8.0):
    body = doc.element.body
    sect = body.find(qn("w:sectPr"))

    h = doc.add_paragraph()
    hr = h.add_run("참고문헌")
    hr.bold = True
    hr.font.size = Pt(13)
    h.paragraph_format.space_before = Pt(12)
    h.paragraph_format.space_after = Pt(4)

    for i, e in enumerate(entries, 1):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Pt(16)          # 내어쓰기 — 번호가 왼쪽으로 튀어나온다
        pf.first_line_indent = Pt(-16)
        pf.space_after = Pt(1.5)
        pf.line_spacing = 1.05
        r = p.add_run(f"[{i}] {e}")
        r.font.size = Pt(size)

    if sect is not None:                  # 구역 속성은 항상 본문 맨 끝에 있어야 한다
        body.remove(sect)
        body.append(sect)


def main():
    out = DOC
    if len(sys.argv) > 1:                 # 쪽수만 재보려면 사본 경로를 준다
        out = sys.argv[1]
        shutil.copy2(DOC, out)
    doc = docx.Document(out)
    before = len(doc.paragraphs)
    add(doc, KTCP)
    doc.save(out)
    d2 = docx.Document(out)
    print(f"{out}: 문단 {before} → {len(d2.paragraphs)} "
          f"(참고문헌 {len(KTCP)}항목 + 제목)")


if __name__ == "__main__":
    main()
