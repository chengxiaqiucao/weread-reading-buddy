# -*- coding: utf-8 -*-
"""从现有成品页面抽取数据样例，并生成与数据解耦的 HTML 模板。

用法：
    python scripts/prepare_assets.py --source-root "C:/Users/weiwe/WorkBuddy/personal"

生成：
    data/samples/report.json
    data/samples/archives/<bookId>.json
    templates/report.html
    templates/archive.html
"""
import argparse
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

REPORT_RE = re.compile(r'const D = (\{.*?\});\s*\nconst \$', re.S)
ARCHIVE_RE = re.compile(r'const D = (\{.*?\});\s*\nD\.reading=(\{.*?\});D\.readingReviews=(\[.*?\]);\s*\nconst \$', re.S)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, 'w', encoding='utf-8').write(text)


RENAMES = {
    'simulatedOldProgress': 'previousProgress',
    'simulatedOldChapterIdx': 'previousChapterIdx',
    'simulatedOldChapterTitle': 'previousChapterTitle',
}


def rename_keys(obj):
    if isinstance(obj, dict):
        return {RENAMES.get(k, k): rename_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [rename_keys(v) for v in obj]
    return obj


def build_friend_aliases(report_data):
    """按好友顺序生成 真实姓名 -> 好友-N 的映射。"""
    mapping = {}
    for i, f in enumerate(report_data.get('friends') or [], 1):
        name = f.get('name') or ''
        if name:
            mapping[name] = '好友-' + str(i)
    return mapping


def mask_review_authors(reviews):
    """脱敏公开点评：作者名 -> 读者-N，reviewId 数字前缀 -> FAKE-N_后缀。"""
    for i, rv in enumerate(reviews or [], 1):
        if isinstance(rv.get('author'), str):
            rv['author'] = '读者-' + str(i)
        rid = rv.get('reviewId')
        if isinstance(rid, str) and re.match(r'^\d+_', rid):
            rv['reviewId'] = 'FAKE-%d_%s' % (i, rid.split('_', 1)[1])
    return reviews


def mask_highlight_comment_authors(books):
    """脱敏热门划线下的评论作者：真实昵称 -> 评论者-N（按出现顺序编号）。"""
    n = 0
    for bk in books or []:
        for hl in bk.get('highlights') or []:
            for cm in hl.get('comments') or []:
                if isinstance(cm.get('author'), str):
                    n += 1
                    cm['author'] = '评论者-' + str(n)
    return books


def apply_aliases(obj, mapping, alias_name_keys=('name', 'author')):
    """递归把字符串值中出现的真实姓名替换为 好友-N（含子串，如 @某某）。"""
    if isinstance(obj, dict):
        return {k: (mapping.get(v, v) if k in alias_name_keys and isinstance(v, str) else apply_aliases(v, mapping))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [apply_aliases(v, mapping) for v in obj]
    if isinstance(obj, str):
        for real, alias in mapping.items():
            if real in obj:
                obj = obj.replace(real, alias)
        return obj
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-root', required=True)
    args = ap.parse_args()
    src = args.source_root

    report_path = os.path.join(src, '个人阅读报告_读书档案版_试跑.html')
    html = io.open(report_path, encoding='utf-8').read()
    m = REPORT_RE.search(html)
    assert m, '无法从报告页面提取数据'
    report_data = rename_keys(json.loads(m.group(1)))
    report_data.pop('simulated', None)
    aliases = build_friend_aliases(report_data)
    report_data = apply_aliases(report_data, aliases)
    # 好友 vid 属于可识别 ID，样例中一律替换为假 ID（真实数据由 collect.py 提供）
    for i, f in enumerate(report_data.get('friends') or [], 1):
        if 'vid' in f:
            f['vid'] = 'FRIEND-' + str(i)
    # 公开点评作者脱敏
    _cur = (report_data.get('notes') or {}).get('current') or {}
    if 'publicReviews' in _cur:
        mask_review_authors(_cur['publicReviews'])
    # 热门划线评论作者脱敏（禁止真实昵称进入样例）
    mask_highlight_comment_authors(report_data.get('books'))
    # 源试跑页的最近想法无 bookTitle，按书名回填（样例均为剑来，真实数据由 collect.py 提供）
    _ideas = (report_data.get('notes') or {}).get('recentIdeas') or []
    if _ideas and not _ideas[0].get('bookTitle') and report_data.get('books'):
        _src_title = report_data['books'][0]['base']['title']
        for idea in _ideas:
            idea['bookTitle'] = _src_title
    write(os.path.join(ROOT, 'data', 'samples', 'report.json'),
          json.dumps(report_data, ensure_ascii=False, indent=2))

    tpl = html[:m.start(1)] + '__WEREAD_DATA__' + html[m.end(1):]
    for old, new in RENAMES.items():
        tpl = tpl.replace(old, new)
    tpl = tpl.replace('<span class="sim">模拟</span>', '')
    tpl = tpl.replace("const fname = encodeURIComponent((NAMES[b.bookId]||b.title.slice(0,12))+'_读书档案.html');",
                      "const fname = encodeURIComponent((b.archiveFile||NAMES[b.bookId]||b.title.slice(0,12))+'_读书档案.html');")
    tpl = tpl.replace('<footer>生成于 2026-11-16 · 个人阅读报告</footer>',
                      '<footer id="gen-footer"></footer>')
    tpl = tpl.replace("const BK = () => D.books[active];",
                      "$('#gen-footer').textContent = '生成于 ' + String(D.generatedAt||'').slice(0,10) + ' · 个人阅读报告';\nconst BK = () => D.books[active];")
    # day() 需兼容 YYYY-MM-DD 字符串（archive.span.first/last），否则显示 Invalid Date
    tpl = tpl.replace("function day(ts){ if(!ts) return '—'; return new Date(ts*1000)",
                      "function day(ts){ if(!ts) return '—'; if(typeof ts==='string') return ts.replace(/-/g,'/'); return new Date(ts*1000)")
    # 最近想法：显示书名 + 正文 80 字截断（源试跑页为旧渲染，此处固化）
    tpl = tpl.replace(".idea .txt{flex:1}",
                      ".idea .txt{flex:1;min-width:0}\n.idea .bk{font-size:10.5px;color:var(--jade);font-weight:700;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}")
    tpl = tpl.replace("N.recentIdeas.map(i=>'<div class=\"idea\"><span class=\"ch\">第'+i.chapterIdx+'章</span><div class=\"txt\">'+esc(i.content)+'<div class=\"abs\">'+dt(i.createTime)+'</div></div></div>').join('')",
                      "N.recentIdeas.map(i=>{const raw=i.content||'';const txt=raw.length>80?raw.slice(0,80)+'…':raw;return '<div class=\"idea\"><span class=\"ch\">第'+i.chapterIdx+'章</span><div class=\"txt\"><div class=\"bk\">《'+esc(i.bookTitle||'—')+'》</div>'+esc(txt)+'<div class=\"abs\">'+dt(i.createTime)+'</div></div></div>';}).join('')")
    write(os.path.join(ROOT, 'templates', 'report.html'), tpl)

    for name in sorted(os.listdir(os.path.join(src, '读书档案'))):
        if not name.endswith('.html'):
            continue
        path = os.path.join(src, '读书档案', name)
        html = io.open(path, encoding='utf-8').read()
        m = ARCHIVE_RE.search(html)
        assert m, '无法从档案提取数据: ' + name
        data = json.loads(m.group(1))
        data['reading'] = json.loads(m.group(2))
        data['readingReviews'] = json.loads(m.group(3))
        data = apply_aliases(data, aliases)  # 点评作者中若含好友真名一并脱敏
        mask_review_authors(data.get('readingReviews'))  # 公开点评作者与 reviewId 脱敏
        data['base']['archiveFile'] = name[:-5].replace('_读书档案', '')
        bid = str(data['base']['bookId'])
        write(os.path.join(ROOT, 'data', 'samples', 'archives', bid + '.json'),
              json.dumps(data, ensure_ascii=False, indent=2))

        tpl = (html[:m.start(1)] + '__WEREAD_DATA__' +
               html[m.end(3):].replace('\nconst $',
                   '\nD.reading = D.reading || {};\nD.readingReviews = D.readingReviews || [];\nconst $', 1))
        tpl = re.sub(r'<title>.*?</title>', '<title>读书档案</title>', tpl, count=1)
        tpl = re.sub(r'<footer[^>]*>.*?</footer>', '<footer id="arc-footer"></footer>', tpl, count=1)
        tpl = tpl.replace('href="../个人阅读报告_读书档案版_试跑.html"',
                          'href="../个人阅读报告.html"')
        tpl = tpl.replace("const B=D.base, A=D.archive, KEY='weread_reflection_'+B.bookId;",
                          "const B=D.base, A=D.archive, KEY='weread_reflection_'+B.bookId;\ndocument.title='读书档案 · '+B.title;\n$('#arc-footer').textContent='读书档案 · '+B.title;")
        tpl = tpl.replace("function day(ts){if(!ts)return '—';return new Date(ts*1000)",
                          "function day(ts){if(!ts)return '—';if(typeof ts==='string')return ts.replace(/-/g,'/');return new Date(ts*1000)")
        write(os.path.join(ROOT, 'templates', 'archive.html'), tpl)

    report_sample = json.load(io.open(os.path.join(ROOT, 'data', 'samples', 'report.json'), encoding='utf-8'))
    archive_samples = [json.load(io.open(os.path.join(ROOT, 'data', 'samples', 'archives', n), encoding='utf-8'))
                       for n in sorted(os.listdir(os.path.join(ROOT, 'data', 'samples', 'archives')))]
    write(os.path.join(ROOT, 'data', 'bundle_sample.json'),
          json.dumps({'report': report_sample, 'archives': archive_samples},
                     ensure_ascii=False, indent=2))
    print('templates, samples and demo bundle prepared')


if __name__ == '__main__':
    main()
