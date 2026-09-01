// 게시 페이지 → 네이버 어뷰징 검사기가 보는 본문 텍스트.
// ★이 추출을 명령줄에서 매번 새로 쓰다가 하루에 세 번 틀렸다(소제목 유실 → STRUCT 오탐 6/6,
//   <style> 미제거 → 키워드 "편집기" 10회 오탐, 검토용 꼬리 미절단). 추출은 여기 한 곳에만 둔다.
'use strict';
function publicText(html) {
  var body = html.split('<hr class="cut">')[0];              // 검토용 꼬리 제외
  body = body.replace(/<style[\s\S]*?<\/style>/gi, '')       // CSS 주석이 본문으로 새던 자리
             .replace(/<script[\s\S]*?<\/script>/gi, '')
             .replace(/<!--[\s\S]*?-->/g, '');
  return body
    .replace(/<h([1-4])[^>]*>/g, '\n■ ')                     // 소제목 마커 — 검사기가 이걸 본다
    .replace(/<li[^>]*>/g, '\n· ')
    .replace(/<\/(p|li|tr|div|h[1-4]|figcaption|blockquote)>/g, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ').replace(/&[a-z]+;/g, ' ');
}
function meta(html) {
  var body = html.split('<hr class="cut">')[0];
  var alts = [];                                             // alt 길이 검사용(가이드 A6)
  var re = /<img[^>]*\salt="([^"]*)"/g, m;
  while ((m = re.exec(body)) !== null) alts.push(m[1]);
  return { title: (body.match(/<h1>([^<]*)/) || ['', ''])[1],
           imageCount: (body.match(/<img /g) || []).length,
           alts: alts,
           externalCaptureCount: 0 };
}
module.exports = { publicText: publicText, meta: meta };
