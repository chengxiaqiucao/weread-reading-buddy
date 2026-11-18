# -*- coding: utf-8 -*-
"""模板渲染冒烟测试：不依赖 API Key。"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'scripts')


class RenderTest(unittest.TestCase):
    def test_render_all(self):
        with tempfile.TemporaryDirectory() as td:
            root = os.path.join(td, 'WeReadBuddy')
            cmd = [sys.executable, os.path.join(SCRIPTS, 'render.py'), 'all',
                   os.path.join(ROOT, 'data', 'bundle_sample.json'), root]
            subprocess.run(cmd, check=True, cwd=ROOT, capture_output=True)

            reports = [f for f in os.listdir(root)
                       if re.match(r'^我的阅读报告_\d{8}\.html$', f)]
            self.assertTrue(reports, '应生成按日期命名的阅读报告')
            report = os.path.join(root, sorted(reports)[-1])
            archive_dir = os.path.join(root, '读书档案')
            log = os.path.join(root, '报告及档案更新记录.md')
            self.assertTrue(os.path.exists(report))
            self.assertTrue(os.path.exists(log))
            archives = [f for f in os.listdir(archive_dir) if f.endswith('_读书档案.html')]
            self.assertTrue(archives)
            self.assertTrue(all(not re.match(r'^\d+_读书档案\.html$', f) for f in archives),
                            '档案应按书名命名，不应为纯 bookId')

            with io.open(report, encoding='utf-8') as f:
                html = f.read()
            self.assertNotIn('__WEREAD_DATA__', html)
            self.assertIn('previousProgress', html)
            self.assertIn('展开其余', html)
            self.assertNotIn('数据说明', html)
            self.assertNotIn('账号全局', html)
            self.assertIn('archiveRel', html)  # 报告持有指向档案目录的相对路径
            self.assertIn('ix-scroll', html)   # 明细长列表固定高度容器

            arc_file = os.path.join(archive_dir, archives[0])
            with io.open(arc_file, encoding='utf-8') as f:
                arc = f.read()
            self.assertNotIn('__WEREAD_DATA__', arc)
            self.assertIn('refl-mask', arc)
            self.assertIn('开始编写', arc)
            self.assertIn('reportRel', arc)  # 档案持有指回报告的相对路径
            self.assertIn('我的点评', arc)  # 档案笔记明细含点评标签页
            self.assertNotIn('口径说明', arc)

            with io.open(log, encoding='utf-8') as f:
                log_text = f.read()
            self.assertIn('内容更新记录', log_text)
            self.assertIn('档案更新', log_text)

    def test_safe_bookname(self):
        sys.path.insert(0, SCRIPTS)
        import render
        self.assertEqual(render.safe_bookname('剑来（1-54 完结精校版）'), '剑来（1-54 完结精校版）')
        self.assertEqual(render.safe_bookname('A/B:C?D'), 'A_B_C_D')  # 半角非法字符
        self.assertEqual(render.safe_bookname('飘：Gone with the wind'), '飘：Gone with the wind')  # 全角冒号保留
        self.assertEqual(render.safe_bookname('A\x00B\x01C'), 'A_B_C')  # 控制字符
        self.assertEqual(render.safe_bookname('CON'), '_CON')  # Windows 保留名
        self.assertEqual(render.safe_bookname('com1'), '_com1')
        self.assertEqual(render.safe_bookname('  ...  '), '未命名')
        self.assertLessEqual(len(render.safe_bookname('书' * 200)), 60)  # 限长

    def test_samples_valid(self):
        with io.open(os.path.join(ROOT, 'data', 'samples', 'report.json'), encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(len(data['books']), 3)
        self.assertIn('recentIdeas', data['notes'])
        for p in os.listdir(os.path.join(ROOT, 'data', 'samples', 'archives')):
            with io.open(os.path.join(ROOT, 'data', 'samples', 'archives', p), encoding='utf-8') as f:
                arc = json.load(f)
            self.assertIn('reading', arc)
            self.assertIn('readingReviews', arc)


if __name__ == '__main__':
    unittest.main()
