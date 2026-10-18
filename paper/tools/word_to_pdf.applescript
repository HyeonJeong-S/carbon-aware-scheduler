-- docx 를 Word 로 열어 PDF 로 내보낸다.
--
-- 2026-10-10: 전에는 /tmp/_pdf3.applescript 에 뒀다가 시스템 임시폴더 청소로
-- 통째로 사라졌다. 그걸 모르고 출력을 /dev/null 로 버린 채 돌려서, 내보내기가
-- 실패했는데도 성공한 줄 알고 어제 PDF를 재측정하는 사고가 났다.
-- 그래서 저장소 안으로 옮긴다. ** 출력을 버리지 말 것. **
--
-- 지켜야 하는 것 둘 (전에 -1708 오류로 알아낸 것):
--   · "active document" 가 아니라 "document 1" 을 쓴다.
--   · 열려 있는 문서를 전부 닫고 시작한다.
--   · 출력 경로는 프로젝트 폴더 안이어야 한다(/tmp 로 내보내면 실패한다).
--
-- 쓰기:
--   osascript paper/tools/word_to_pdf.applescript <입력.docx 절대경로> <출력.pdf 절대경로>

-- 2026-10-12: AppleEvent 기본 제한이 2분이라 그림 10장짜리 원고에서
-- -1712(시간 초과)로 끊겼다. 내보내기가 실패했는데도 returncode 는 0 이라
-- 조용히 지나갔다. with timeout 으로 10분까지 기다린다.
on run argv
  set p to item 1 of argv
  set o to item 2 of argv
  -- 2026-10-18: 셋째 인자 quiet 면 Word 를 앞으로 끌어내지 않고 끝나면 숨긴다(float_search.py 가 10초마다 창을 띄워 사용자가 물음)
  set quiet to ((count of argv) > 2) and (item 3 of argv is "quiet")
  with timeout of 600 seconds
  tell application "Microsoft Word"
    if not quiet then activate
    repeat while (count of documents) > 0
      close document 1 saving no
    end repeat
    open p
    delay 4
    -- 2026-10-10: 문서에 Word 메모가 있으면 Word 가 메모 여백을 만들려고
    -- 본문 전체를 0.69배로 줄여서 PDF 를 뽑는다(글자 7.92→5.49pt). 그걸 모르고
    -- 재면 "줄간격을 늘렸는데 오히려 줄었다" 같은 유령 결과가 나온다.
    -- 내보내기 전에 메모 표시를 끈다.
    try
      set view type of view of active window of document 1 to print view
      set show comments of view of active window of document 1 to false
      set show insertions and deletions of view of active window of document 1 to false
      set show format changes of view of active window of document 1 to false
    end try
    delay 1
    save as document 1 file name o file format format PDF
    delay 3
    close document 1 saving no
  end tell
  if quiet then
    try
      tell application "System Events" to set visible of process "Microsoft Word" to false
    end try
  end if
  end timeout
end run
