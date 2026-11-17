# -*- coding: utf-8 -*-
"""把数据 JSON 注入 HTML 模板，生成可直接打开的报告 / 读书档案。

用法：
    python scripts/render.py report  data/samples/report.json            out/个人阅读报告.html
    python scripts/render.py archive data/samples/archives/31131759.json out/读书档案/剑来_读书档案.html
    python scripts/render.py all     data/bundle.json                    out/ [--archive-dir DIR] [--log FILE]

bundle.json 结构：{"report": {报告数据}, "archives": [档案数据, ...]}

设计要点（all 模式）：
  - 报告输出到 out/ 下的日期目录；档案固定输出到 --archive-dir（默认 out 的同级“读书档案”目录），
    保证档案目录稳定、每本书按 bookId 只有一份文件、每次调用新增或覆盖更新。
  - 报告与档案互相写入相对路径（archiveRel / reportRel），跨目录也能正确跳转。
  - 每次 all 渲染向 --log（默认档案目录下的 更新记录.md）追加一条内容更新记录。
"""
import argparse
import io
import json
import os
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PLACEHOLDER = '__WEREAD_DATA__'
TZ = timezone(timedelta(hours=8))


def load(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def render(kind, data, out):
    tpl_path = os.path.join(ROOT, 'templates', kind + '.html')
    with io.open(tpl_path, encoding='utf-8') as f:
        tpl = f.read()
    assert tpl.count(PLACEHOLDER) == 1, '模板数据占位符异常: ' + tpl_path
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    html = tpl.replace(PLACEHOLDER, payload)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(out)


def _rel(target, start_dir):
    return os.path.relpath(target, start_dir).replace('\\', '/')


def append_log(log_path, bundle, actions):
    """把本次报告 + 档案的内容更新情况追加到一份 Markdown 记录（最新在最上）。"""
    rpt = bundle.get('report') or {}
    notes = rpt.get('notes') or {}
    cur, prev = notes.get('current') or {}, notes.get('previous') or {}
    books = rpt.get('books') or []
    first = notes.get('firstRun', False)
    ts = bundle.get('generatedAt') or datetime.now(TZ).strftime('%Y-%m-%d %H:%M')

    def diff(k):
        now, old = cur.get(k, 0), prev.get(k, 0)
        d = int(now) - int(old)
        return '%s（%s）' % (now, ('±0' if d == 0 else ('+%d' % d if d > 0 else str(d))))

    lines = ['## %s · %s' % (ts, '首次生成' if first else '更新')]
    lines.append('- 触发类型：%s' % ('首次生成（无历史快照）' if first else '常规更新（与上次快照对比）'))
    lines.append('- 在读书目：%d 本 · %s' % (
        len(books), '、'.join(b['base']['title'][:16] for b in books[:10])))
    prog_bits = []
    for b in books[:10]:
        bs = b['base']
        prog_bits.append('%s %s%%→%s%%（第%s→%s章）' % (
            bs['title'][:12], bs.get('previousProgress'), bs.get('progress'),
            bs.get('previousChapterIdx'), bs.get('currentChapterIdx')))
    if prog_bits:
        lines.append('- 进度变化：' + '；'.join(prog_bits))
    lines.append('- 笔记互动：笔记总数 %s · 想法 %s · 划线 %s · 在读最热点评 %d 条' % (
        diff('totalNotes'), diff('reviewSum'), diff('bookmarkSum'), len(cur.get('publicReviews') or [])))
    lines.append('- 好友在读：%d 位 · 最近想法 %d 条' % (
        len(rpt.get('friends') or []), len(notes.get('recentIdeas') or [])))
    lines.append('- 档案更新：新增 %d 份 · 更新 %d 份' % (actions.get('new', 0), actions.get('updated', 0)))
    for name in actions.get('names', [])[:12]:
        lines.append('    - %s' % name)
    lines.append('')

    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    old_text = ''
    if os.path.exists(log_path):
        with io.open(log_path, encoding='utf-8') as f:
            old_text = f.read()
    header = '# 阅读报告与档案 · 内容更新记录\n\n'
    rest = old_text[len(header):] if old_text.startswith(header) else (old_text + '\n' if old_text else '')
    with io.open(log_path, 'w', encoding='utf-8') as f:
        f.write(header + '\n'.join(lines) + '\n' + rest)
    print(log_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['report', 'archive', 'all'])
    ap.add_argument('data')
    ap.add_argument('out')
    ap.add_argument('--archive-dir', default=None, help='all 模式：档案固定输出目录')
    ap.add_argument('--log', default=None, help='all 模式：内容更新记录 Markdown 路径')
    args = ap.parse_args()

    if args.kind == 'all':
        bundle = load(args.data)
        out_dir = os.path.abspath(args.out)
        report_out = os.path.join(out_dir, '个人阅读报告.html')
        report_dir = os.path.dirname(report_out)
        # 档案固定目录：默认放在报告输出目录的同级，保证跨日期/跨次调用稳定
        archive_dir = os.path.abspath(args.archive_dir) if args.archive_dir else \
            os.path.join(os.path.dirname(out_dir), '读书档案')
        os.makedirs(archive_dir, exist_ok=True)

        report = bundle['report']
        actions = {'new': 0, 'updated': 0, 'names': []}
        for arc in bundle.get('archives', []):
            bid = str(arc['base'].get('bookId') or '')
            # 按 bookId 命名，保证每本书始终只有一份档案文件
            fname = '%s_读书档案.html' % (bid or arc['base']['title'][:12])
            apath = os.path.join(archive_dir, fname)
            existed = os.path.exists(apath)
            arc['reportRel'] = _rel(report_out, archive_dir)
            for b in report.get('books', []):
                if str(b['base'].get('bookId')) == bid:
                    b['base']['archiveRel'] = _rel(apath, report_dir)
            render('archive', arc, apath)
            actions['updated' if existed else 'new'] += 1
            actions['names'].append('%s → %s' % (arc['base']['title'][:16], fname))

        render('report', report, report_out)

        log_path = args.log or os.path.join(archive_dir, '更新记录.md')
        append_log(log_path, bundle, actions)
    else:
        render(args.kind, load(args.data), args.out)


if __name__ == '__main__':
    main()
