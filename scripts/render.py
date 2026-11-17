# -*- coding: utf-8 -*-
"""把数据 JSON 注入 HTML 模板，生成可直接打开的报告 / 读书档案。

用法：
    python scripts/render.py report  data/samples/report.json            我的阅读报告.html
    python scripts/render.py archive data/samples/archives/31131759.json 读书档案/剑来_读书档案.html
    python scripts/render.py all     data/bundle.json                    WeReadBuddy/ [--archive-dir DIR] [--log FILE]

bundle.json 结构：{"report": {报告数据}, "archives": [档案数据, ...]}

设计要点（all 模式，统一到单一根目录）：
  - 根目录（位置参数 out）下只放三类产物：
      * 我的阅读报告_YYYYMMDD.html   ← 可保留多份，按生成日期命名
      * 读书档案/书本名称_读书档案.html ← 每本书一份，按书名命名（非法字符替换、重名加 bookId 后缀）
      * 报告及档案更新记录.md         ← 内容更新情况，最新在最上
  - 报告与档案互相写入相对路径（archiveRel / reportRel），跨目录也能正确跳转。
  - 档案每次调用存在即覆盖更新、不存在则新增；报告按日期命名，可累积多份。
"""
import argparse
import io
import json
import os
import re
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PLACEHOLDER = '__WEREAD_DATA__'
TZ = timezone(timedelta(hours=8))
# Windows 文件名非法字符（半角）+ 所有 ASCII 控制字符；全角标点（：（）等）在 NTFS 合法，保留以贴合书名
ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')
# Windows 保留设备名（大小写不敏感），这些名字不能单独作为文件名
RESERVED = {'CON', 'PRN', 'AUX', 'NUL'} | \
           {'COM%d' % i for i in range(1, 10)} | \
           {'LPT%d' % i for i in range(1, 10)}


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


def safe_bookname(title):
    """书名 → 跨平台安全文件名。

    兼容处理：
      - 半角非法字符 \\/:*?"<>| 与控制字符替换为下划线（全角标点如 ：（） 合法，保留以贴合书名）
      - 连续下划线/空白折叠、去首尾空白与点（Windows 不允许文件名以点/空格结尾）
      - 命中 Windows 保留设备名（CON/PRN/COM1...）时加前缀
      - 限长 60 字，避免长书名 + 后缀超过文件系统单文件名上限
      - 空名回退为「未命名」
    """
    s = ILLEGAL.sub('_', str(title or ''))
    s = re.sub(r'_+', '_', s)
    s = re.sub(r'\s+', ' ', s).strip().strip('. ').strip()
    if s.upper() in RESERVED:
        s = '_' + s
    return s[:60] or '未命名'


def gen_ymd(bundle):
    """从 generatedAt 取 YYYYMMDD；取不到则用当前日期。"""
    gen = str(bundle.get('generatedAt') or '')
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', gen)
    if m:
        return ''.join(m.groups())
    return datetime.now(TZ).strftime('%Y%m%d')


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

    snap = rpt.get('snapshot') or {}
    lines = ['## %s · %s' % (ts, '首次生成' if first else '更新')]
    lines.append('- 触发类型：%s' % ('首次生成（无历史快照）' if first else '常规更新（与上次快照对比）'))
    if snap:
        if snap.get('shortInterval'):
            lines.append('- 快照基准：%s（距上次生成 %s，不足24h，按同一份快照处理，仅更新最新快照）' % (
                snap.get('baselineTime', '—'), snap.get('lastGenGap', '—')))
        elif first:
            lines.append('- 快照基准：首次建立基准快照')
        else:
            lines.append('- 快照基准：%s（距上次生成 %s，已满24h，已推进为新基准）' % (
                snap.get('baselineTime', '—'), snap.get('lastGenGap', '—')))
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
    ap.add_argument('--archive-dir', default=None, help='all 模式：档案输出目录，默认 <根目录>/读书档案')
    ap.add_argument('--log', default=None, help='all 模式：更新记录路径，默认 <根目录>/报告及档案更新记录.md')
    args = ap.parse_args()

    if args.kind == 'all':
        bundle = load(args.data)
        root = os.path.abspath(args.out)
        ymd = gen_ymd(bundle)
        report_out = os.path.join(root, '我的阅读报告_%s.html' % ymd)
        report_dir = root
        archive_dir = os.path.abspath(args.archive_dir) if args.archive_dir else \
            os.path.join(root, '读书档案')
        os.makedirs(archive_dir, exist_ok=True)

        report = bundle['report']
        actions = {'new': 0, 'updated': 0, 'names': []}
        used_stems = set()
        for arc in bundle.get('archives', []):
            bid = str(arc['base'].get('bookId') or '')
            # 按书名命名，保证每本书始终只有一份档案文件；非法字符替换、重名加 bookId 后缀
            base_name = safe_bookname(arc['base']['title'])
            stem = base_name
            if stem in used_stems:
                stem = '%s_%s' % (base_name[:50], bid or 'dup')
                n = 2
                while stem in used_stems:  # 极端情况下 bookId 也撞名，再加序号
                    stem = '%s_%s_%d' % (base_name[:48], bid or 'dup', n)
                    n += 1
            used_stems.add(stem)
            fname = '%s_读书档案.html' % stem
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

        log_path = args.log or os.path.join(root, '报告及档案更新记录.md')
        append_log(log_path, bundle, actions)
    else:
        render(args.kind, load(args.data), args.out)


if __name__ == '__main__':
    main()
