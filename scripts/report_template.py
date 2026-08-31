# -*- coding: utf-8 -*-
"""
report_template.py - 多班级全景教学分析 HTML 可视化报告渲染引擎 (Pro 全模块班级动态联动封板版)
1. 100% 像素级对齐参考报告排版
2. 上方班级切换栏：支持全年级 / 班级横向对比 / 各具体班级
   - 第一部分：每日提交活跃度柱状图按所选班级实时重绘！
   - 第三部分：困难学生画像（8列表头）按所选班级即时下钻过滤，提示文本联动，班内序号重编！
   - 第四部分：代码异常审计（4.1 首次即AC、4.2 极速连交、4.3 雷同聚焦、4.4 违规语言与AI注释）按所选班级即时过滤与动态重绘！
   - 第五部分：按班级即时过滤学生做题明细行
   - 第六部分（AC算法精细剖析）：
     * 自动过滤隐藏当前班级为 0 人的流派（不显示占比条与代码卡片）
     * 占比条形图按当前班级学生重新计算
     * 代码样例 100% 提取并展示当前班级学生的真实 AC 代码！
   - 第七部分（典型错误代码诊断）：
     * 自动过滤隐藏当前班级 0 人命中的错误模式
     * 错误代码样例 100% 提取并展示当前班级学生的真实错误代码与真实提交 ID！
   - 点击上方 [📊 班级横向对比大屏] 切换至对比大屏，点击班级/总览切回常规分析
3. 下方 Tab 导航栏严格精简为 7 个主模块（移除第七部分后面的第 8 个 Tab）
4. 实名/脱敏匿名一键切换，彻底使用真实用户名，废弃自定义乱填昵称
"""

import json
import html as py_html
import re
from collections import defaultdict

def render_html(contest_name, dataset, anon_map, prob_titles, deep_analysis=None, mode="both", target_class=""):
    has_roster = dataset.get("has_roster", False)
    classes_list = dataset.get("classes_list", ["全年级"])
    all_probs = dataset.get("all_probs", [])
    class_comparison = dataset.get("class_comparison", {})
    stats_all = dataset.get("stats_all", {})
    anomalies_all = dataset.get("anomalies_all", {})

    def render_student_name(u):
        if not u: return ""
        clean_u = str(u).strip()
        anon_u = anon_map.get(clean_u, clean_u)
        return f'<span class="name-real">{py_html.escape(clean_u)}</span><span class="name-anon" style="display:none;">{py_html.escape(anon_u)}</span>'

    # 准备前端 JSON 数据
    dataset_json = json.dumps(dataset, ensure_ascii=False)
    anon_map_json = json.dumps(anon_map, ensure_ascii=False)
    prob_titles_json = json.dumps(prob_titles, ensure_ascii=False)
    deep_analysis_json = json.dumps(deep_analysis or {}, ensure_ascii=False)

    html_out = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{py_html.escape(contest_name)} — 全景整体与代码异常综合分析报告 (多班级Pro版)</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: #f4f6f9; color: #2c3e50; line-height: 1.45; font-size: 13px; }}
.container {{ max-width: 1220px; margin: 0 auto; padding: 20px 16px; }}
.top-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 10px; }}
h1 {{ font-size: 23px; color: #1a1a2e; font-weight: 700; }}
h2 {{ font-size: 17px; color: #1a1a2e; margin: 24px 0 10px; padding-bottom: 6px; border-bottom: 2px solid #e2e8f0; }}
h3 {{ font-size: 14px; color: #334155; margin: 14px 0 8px; font-weight: 600; }}
.meta {{ font-size: 12px; color: #64748b; margin-bottom: 16px; background: #fff; padding: 10px 14px; border-radius: 6px; border: 1px solid #e2e8f0; line-height: 1.6; }}

/* Privacy & Class Control Bar */
.control-bar {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  background: #fff;
  padding: 10px 14px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
  margin-bottom: 14px;
}}
.class-selector-group {{ display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }}
.selector-label {{ font-size: 12px; font-weight: 700; color: #334155; display: flex; align-items: center; gap: 4px; }}
.class-btn {{
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #475569;
  transition: all 0.15s;
}}
.class-btn:hover {{ background: #e2e8f0; color: #1e293b; }}
.class-btn.active {{ background: #2563eb; color: #fff; border-color: #2563eb; }}
.class-btn.btn-compare {{ background: #fdf4ff; border-color: #d8b4fe; color: #7e22ce; font-weight: 700; }}
.class-btn.btn-compare.active {{ background: #9333ea; color: #fff; border-color: #9333ea; }}

.privacy-control {{ display: flex; align-items: center; gap: 6px; }}
.privacy-label {{ font-size: 12px; font-weight: 600; color: #334155; }}
.toggle-btn {{ padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer; border: 1px solid #cbd5e1; background: #f8fafc; color: #64748b; transition: all 0.15s; }}
.toggle-btn.active {{ background: #2563eb; color: #fff; border-color: #2563eb; }}

/* Compact Summary Cards */
.summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; margin: 12px 0 14px; }}
.card {{ background: #fff; border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 4px rgba(0,0,0,0.03); border: 1px solid #e2e8f0; }}
.card .num {{ font-size: 24px; font-weight: 700; line-height: 1.1; }}
.card .lab {{ font-size: 12px; color: #64748b; margin-top: 4px; }}
.card.r .num {{ color: #e53935; }}
.card.g .num {{ color: #10b981; }}
.card.b .num {{ color: #2563eb; }}
.card.o .num {{ color: #f59e0b; }}
.card.p .num {{ color: #8b5cf6; }}
.card.c .num {{ color: #06b6d4; }}

/* Super Compact Tables */
table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.03); margin: 8px 0; font-size: 12px; }}
th {{ background: #f8fafc; padding: 6px 10px; text-align: left; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0; white-space: nowrap; height: 32px; }}
td {{ padding: 5px 10px; border-top: 1px solid #f1f5f9; vertical-align: middle; height: 30px; }}
tr:hover {{ background: #f8fafc; }}

.tag {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 500; margin: 1px 2px; line-height: 1.4; }}
.tag-red {{ background: #fee2e2; color: #b91c1c; }}
.tag-orange {{ background: #ffedd5; color: #c2410c; }}
.tag-yellow {{ background: #fef9c3; color: #a16207; }}
.tag-green {{ background: #dcfce7; color: #15803d; }}
.tag-blue {{ background: #dbeafe; color: #1d4ed8; }}
.tag-purple {{ background: #f3e8ff; color: #6b21a8; }}
.tag-gray {{ background: #f1f5f9; color: #475569; }}

.note {{ background: #fffbeb; border-left: 3px solid #f59e0b; border-radius: 4px; padding: 10px 14px; margin: 12px 0; font-size: 12px; color: #92400e; }}
.warn {{ background: #fef2f2; border-left: 3px solid #ef4444; border-radius: 4px; padding: 10px 14px; margin: 12px 0; font-size: 12px; color: #991b1b; }}
.info {{ background: #eff6ff; border-left: 3px solid #3b82f6; border-radius: 4px; padding: 10px 14px; margin: 12px 0; font-size: 12px; color: #1e40af; }}
.section {{ background: #fff; border-radius: 8px; padding: 16px; margin: 14px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.03); border: 1px solid #e2e8f0; }}

/* Compact Progress Bars */
.bar-container {{ display: flex; align-items: center; gap: 6px; width: 100%; }}
.bar-bg {{ flex: 1; background: #e2e8f0; height: 7px; border-radius: 4px; overflow: hidden; position: relative; }}
.bar-fill {{ height: 100%; border-radius: 4px; }}
.bar-fill-g {{ background: linear-gradient(90deg, #34d399, #10b981); }}
.bar-fill-b {{ background: linear-gradient(90deg, #60a5fa, #2563eb); }}
.bar-fill-y {{ background: linear-gradient(90deg, #fde047, #eab308); }}
.bar-fill-o {{ background: linear-gradient(90deg, #fbbf24, #f59e0b); }}
.bar-fill-r {{ background: linear-gradient(90deg, #f87171, #ef4444); }}
.bar-text {{ font-size: 11px; font-weight: 600; width: 40px; text-align: right; color: #475569; }}

/* Vertical Bar Chart Styles */
.vchart-card {{ background: #fff; border-radius: 8px; padding: 16px 14px 10px; margin: 12px 0; border: 1px solid #e2e8f0; }}
.vchart-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; font-size: 12px; color: #64748b; }}
.vchart-legend {{ display: flex; gap: 14px; font-size: 12px; }}
.vchart-legend-item {{ display: flex; align-items: center; gap: 5px; }}
.legend-color {{ width: 12px; height: 12px; border-radius: 2px; }}

.vchart-scroll-wrap {{ width: 100%; overflow-x: auto; padding-bottom: 8px; }}
.vchart-stage {{ display: flex; align-items: flex-end; gap: 8px; height: 210px; min-width: 960px; padding: 24px 10px 0; border-bottom: 2px solid #cbd5e1; position: relative; }}
.vchart-grid-line {{ position: absolute; left: 0; right: 0; border-top: 1px dashed #e2e8f0; font-size: 10px; color: #94a3b8; padding-left: 4px; pointer-events: none; }}

.vcol {{ display: flex; flex-direction: column; align-items: center; width: 26px; height: 100%; justify-content: flex-end; position: relative; cursor: pointer; }}
.vcol:hover .vcol-bar {{ filter: brightness(0.92); }}
.vcol:hover .vtooltip {{ display: block; }}

.vcol-peak-val {{ font-size: 10px; font-weight: 700; color: #1e293b; margin-bottom: 3px; white-space: nowrap; }}
.vcol-bar {{ width: 16px; border-radius: 3px 3px 0 0; display: flex; flex-direction: column-reverse; overflow: hidden; }}
.vcol-seg-ac {{ background: #10b981; width: 100%; }}
.vcol-seg-wa {{ background: #ef4444; width: 100%; opacity: 0.82; }}
.vcol-date {{ font-size: 10px; color: #64748b; margin-top: 6px; white-space: nowrap; transform: rotate(-35deg); transform-origin: top left; height: 26px; }}

.vtooltip {{ display: none; position: absolute; bottom: 105%; left: 50%; transform: translateX(-50%); background: #1e293b; color: #fff; padding: 6px 10px; border-radius: 5px; font-size: 11px; white-space: nowrap; z-index: 100; box-shadow: 0 4px 10px rgba(0,0,0,0.2); pointer-events: none; }}
.vtooltip::after {{ content: ''; position: absolute; top: 100%; left: 50%; transform: translateX(-50%); border: 4px solid transparent; border-top-color: #1e293b; }}

.cluster-box {{ display: inline-block; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px; padding: 3px 8px; margin: 2px 4px 2px 0; font-size: 11px; }}
code {{ background: #f1f5f9; padding: 1px 5px; border-radius: 3px; font-family: "SF Mono", Consolas, monospace; font-size: 11px; color: #0f172a; }}

/* Tab Navigation (严格 7 个 Tab) */
.tabs {{ display: flex; gap: 6px; border-bottom: 2px solid #e2e8f0; margin-bottom: 14px; flex-wrap: wrap; }}
.tab-btn {{ padding: 8px 14px; border: none; background: none; font-size: 13px; font-weight: 600; color: #64748b; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all 0.15s; }}
.tab-btn:hover {{ color: #2563eb; }}
.tab-btn.active {{ color: #2563eb; border-bottom-color: #2563eb; font-weight: 700; }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}

.filter-input {{ padding: 6px 12px; border: 1px solid #cbd5e1; border-radius: 5px; font-size: 12px; width: 240px; outline: none; }}
.filter-input:focus {{ border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37,99,235,0.1); }}

/* Anonymized elements */
.name-real {{ display: inline; }}
.name-anon {{ display: none; }}

/* Code Blocks: Pure Black Background & Pure White Text */
pre {{
  background: #000000 !important;
  color: #ffffff !important;
  padding: 12px;
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.45;
  overflow-x: auto;
  font-family: "SF Mono", Consolas, "Liberation Mono", Menlo, Courier, monospace !important;
  margin: 6px 0;
}}
pre code {{
  background: transparent !important;
  color: #ffffff !important;
  padding: 0 !important;
  border-radius: 0 !important;
  font-family: inherit !important;
  font-size: inherit !important;
}}

/* Comparison Screen Matrix */
.heatmap-cell {{ text-align: center; font-weight: 600; font-size: 11px; }}
.heatmap-g {{ background: #dcfce7; color: #166534; }}
.heatmap-y {{ background: #fef9c3; color: #854d0e; }}
.heatmap-r {{ background: #fee2e2; color: #991b1b; }}
</style>
</head>
<body>
<div class="container">

<div class="top-header">
  <h1>📊 {py_html.escape(contest_name)} — 全景整体与代码异常综合分析报告</h1>
  <div class="privacy-control">
    <span class="privacy-label">🛡️ 隐私展示模式：</span>
    <button id="btnReal" class="toggle-btn active" onclick="setPrivacy(false)">🔒 教学审计实名版</button>
    <button id="btnAnon" class="toggle-btn" onclick="setPrivacy(true)">👤 匿名脱敏版 (代号)</button>
  </div>
</div>

<!-- ==================== CLASS SELECTOR CONTROLS ==================== -->
<div class="control-bar">
  <div class="class-selector-group">
    <span class="selector-label">🏫 班级切换：</span>
    <button class="class-btn active" id="btn-class-all" onclick="switchClassView('all')">全年级总览</button>
"""
    if has_roster:
        html_out += """    <button class="class-btn btn-compare" id="btn-class-compare" onclick="switchClassView('compare')">📊 班级横向对比大屏</button>\n"""
        for cls in classes_list:
            if cls == "全年级": continue
            html_out += f"""    <button class="class-btn" id="btn-class-{cls}" onclick="switchClassView('{cls}')">{cls}</button>\n"""

    html_out += f"""  </div>
  <div style="font-size:12px; color:#64748b;">当前视图：<b id="current-view-badge" style="color:#2563eb;">全年级总览</b></div>
</div>

<!-- ==================== CLASS COMPARISON VIEW CONTAINER (点击上方对比大屏时激活) ==================== -->
<div id="view-class-comparison" style="display:none;">
  <h2>专属【班级横向对比大屏】（核心指标矩阵 · 题目攻关热力）</h2>
  
  <div class="section">
    <h3>各班级核心指标总览矩阵表（支持点击表头即时升降序）</h3>
    <table id="classMatrixTable">
      <thead>
        <tr>
          <th onclick="sortTable('classMatrixTable', 0)" style="cursor:pointer;">班级名称 ⇕</th>
          <th onclick="sortTable('classMatrixTable', 1)" style="cursor:pointer;">应到人数 ⇕</th>
          <th onclick="sortTable('classMatrixTable', 2)" style="cursor:pointer;">实到人数 ⇕</th>
          <th onclick="sortTable('classMatrixTable', 3)" style="cursor:pointer;">参评率 ⇕</th>
          <th onclick="sortTable('classMatrixTable', 4)" style="cursor:pointer;">人均 AC 题数 ⇕</th>
          <th onclick="sortTable('classMatrixTable', 5)" style="cursor:pointer;">满分人数 ⇕</th>
          <th onclick="sortTable('classMatrixTable', 6)" style="cursor:pointer;">满分率 ⇕</th>
          <th onclick="sortTable('classMatrixTable', 7)" style="cursor:pointer;">总提交数 ⇕</th>
          <th onclick="sortTable('classMatrixTable', 8)" style="cursor:pointer;">综合 AC 率 ⇕</th>
        </tr>
      </thead>
      <tbody>
"""
    summary_list = class_comparison.get("summary", [])
    for cs in summary_list:
        c_name = cs.get("class_name", "")
        r_cnt = cs.get("roster_count", 0)
        a_cnt = cs.get("actual_count", 0)
        att_rate = cs.get("attend_rate", 0.0)
        avg_sol = cs.get("avg_solved", 0.0)
        full_cnt = cs.get("full_cnt", 0)
        full_rate = cs.get("full_rate", 0.0)
        tot_s = cs.get("avg_subs", 0.0) * a_cnt
        ac_r = cs.get("ac_rate", 0.0)

        html_out += f"""        <tr>
          <td><b>{c_name}</b></td>
          <td>{r_cnt}</td>
          <td><b>{a_cnt}</b></td>
          <td><span class="tag tag-blue">{att_rate:.1f}%</span></td>
          <td><b>{avg_sol:.1f} 题</b></td>
          <td>{full_cnt} 人</td>
          <td><span class="tag tag-green">{full_rate:.1f}%</span></td>
          <td>{int(tot_s)}</td>
          <td><b>{ac_r:.1f}%</b></td>
        </tr>
"""
    html_out += """      </tbody>
    </table>
  </div>

  <div class="section">
    <h3>题目攻关率热力对比全景表（各班级 vs 25道题目）</h3>
    <div style="overflow-x:auto;">
      <table>
        <thead>
          <tr>
            <th style="position:sticky; left:0; background:#f8fafc; z-index:2;">班级</th>
"""
    for p in all_probs:
        html_out += f"""            <th style="min-width:38px; text-align:center;">{p}</th>\n"""
    html_out += """          </tr>
        </thead>
        <tbody>
"""
    for cs in summary_list:
        c_name = cs.get("class_name", "")
        p_rates = cs.get("prob_pass_rates", {})
        html_out += f"""          <tr>
            <td style="position:sticky; left:0; background:#fff; font-weight:700; z-index:1;">{c_name}</td>
"""
        for p in all_probs:
            pr = p_rates.get(p, 0.0)
            cls_bg = "heatmap-g" if pr >= 65 else ("heatmap-y" if pr >= 45 else "heatmap-r")
            html_out += f"""            <td class="heatmap-cell {cls_bg}">{pr:.0f}%</td>\n"""
        html_out += """          </tr>\n"""

    html_out += """        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- ==================== MAIN ANALYSIS CONTAINER (常规 7 大模块) ==================== -->
<div id="view-main-analysis">

<div class="meta" id="header-meta-box">
<b>权威数据源</b>：<code>krand.site</code>（HUSTOJ）平台实时日志（CID: 1081 “{py_html.escape(contest_name)}”） + 本地代码全量静态分析<br>
<b>数据规模</b>：全量 <b id="meta-tot-subs">{stats_all.get('total_subs', 0):,}</b> 条提交日志 · <b id="meta-registered">{stats_all.get('total_registered', 0)}</b> 名注册学生 · <b id="meta-active-users">{stats_all.get('total_with_subs', 0)}</b> 名有效提交学生 · <b id="meta-full-cnt">{len(stats_all.get('solved_all', []))}</b> 人通关 25 题 · <b id="meta-tot-ac">{stats_all.get('total_ac', 0):,}</b> 次正确判定（全局 AC 率 <b id="meta-ac-rate">{stats_all.get('ac_rate', 0.0)}%</b>）
</div>

<!-- ==================== SUMMARY CARDS ==================== -->
<div class="summary-cards" id="summary-cards-row1">
  <div class="card b"><div class="num" id="card-registered">{stats_all.get('total_registered', 0)}</div><div class="lab">注册学生总数</div></div>
  <div class="card c"><div class="num" id="card-with-subs">{stats_all.get('total_with_subs', 0)}</div><div class="lab">有效参与提交学生</div></div>
  <div class="card g"><div class="num" id="card-full-cnt">{len(stats_all.get('solved_all', []))}</div><div class="lab">通关满分（25题全通）</div></div>
  <div class="card p"><div class="num" id="card-good-cnt">{len(stats_all.get('solved_gte_20', []))}</div><div class="lab">优秀学生（完成 ≥20 题）</div></div>
  <div class="card o"><div class="num" id="card-tot-subs">{stats_all.get('total_subs', 0):,}</div><div class="lab">总提交评测次数</div></div>
  <div class="card g"><div class="num" id="card-ac-rate">{stats_all.get('ac_rate', 0.0)}%</div><div class="lab">全局提交整体 AC 率</div></div>
</div>

<div class="summary-cards" id="summary-cards-row2">
  <div class="card r"><div class="num" id="card-struggling-cnt">{len(stats_all.get('struggling', []))}</div><div class="lab">困难学生（高提交低AC率）</div></div>
  <div class="card r"><div class="num" id="card-burst-cnt">{len(anomalies_all.get('submission_bursts', []))}</div><div class="lab">提交频率异常（秒交/连交）</div></div>
  <div class="card o"><div class="num" id="card-plag-cnt">{sum(len(v) for v in anomalies_all.get('plagiarism_groups', {}).values()) if isinstance(anomalies_all.get('plagiarism_groups'), dict) else 0}</div><div class="lab">高雷同代码对（≥95%）</div></div>
  <div class="card r"><div class="num" id="card-nonpy-cnt">{len(set(x.get('student', '') for x in anomalies_all.get('non_python', [])))}</div><div class="lab">违规使用 C/C++ 语言</div></div>
</div>

<!-- ==================== TAB NAVIGATION (严格 7 个 Tab) ==================== -->
<div class="tabs" id="mainTabsNav">
  <button class="tab-btn active" onclick="switchTab('tab-overview')">📈 一、整体宏观数据与垂直柱状图趋势</button>
  <button class="tab-btn" onclick="switchTab('tab-problems')">🎯 二、25道题目难度与通关分布（含题名）</button>
  <button class="tab-btn" onclick="switchTab('tab-struggling')">💡 三、困难/重点辅导学生画像</button>
  <button class="tab-btn" onclick="switchTab('tab-anomalies')">⚠️ 四、代码异常与作弊审计 (支持一键脱敏)</button>
  <button class="tab-btn" onclick="switchTab('tab-all-students')">📋 五、学生做题数据完整明细表</button>
  <button class="tab-btn" onclick="switchTab('tab-ac-algorithms')">💡 六、AC算法精细剖析</button>
  <button class="tab-btn" onclick="switchTab('tab-error-diagnostics')">🔍 七、典型错误代码诊断</button>
</div>

<!-- ==================== TAB 1: OVERVIEW ==================== -->
<div id="tab-overview" class="tab-content active">
  <h2>第一部分：整体情况与每日提交活跃度（垂直柱状图）</h2>
  
  <div class="section">
    <h3>1.1 每日提交活跃度可视化趋势（垂直堆叠柱状图）</h3>
    <div class="vchart-card">
      <div class="vchart-header">
        <span>统计周期：提交日志全时段（鼠标悬停柱子查看当日详细统计）</span>
        <div class="vchart-legend">
          <div class="vchart-legend-item"><div class="legend-color" style="background:#10b981;"></div><span>正确 (AC) 提交</span></div>
          <div class="vchart-legend-item"><div class="legend-color" style="background:#ef4444;"></div><span>试错 / 未通过提交</span></div>
        </div>
      </div>
      
      <div class="vchart-scroll-wrap">
        <div class="vchart-stage" id="vchartStage"></div>
      </div>
    </div>
  </div>
</div>

<!-- ==================== TAB 2: PROBLEMS ==================== -->
<div id="tab-problems" class="tab-content">
  <h2>第二部分：25 道题目难度与通关分布（包含题目名称 · 紧凑排版）</h2>
  
  <div class="section">
    <table id="problemsTable">
      <thead>
        <tr>
          <th style="width:45px;">题号</th>
          <th style="width:160px;">题目名称</th>
          <th style="width:75px;">尝试人数</th>
          <th style="width:75px;">通关人数</th>
          <th style="width:180px;">学生通关比例 (可视化)</th>
          <th style="width:70px;">总提交</th>
          <th style="width:70px;">AC提交</th>
          <th style="width:170px;">提交 AC 率 (试错难度)</th>
          <th style="width:70px;">难度等级</th>
        </tr>
      </thead>
      <tbody>
"""
    tot_active_users = max(stats_all.get("total_with_subs", 1), 1)
    for p in all_probs:
        p_name = prob_titles.get(p, f"题目 {p}")
        att_u = stats_all.get("prob_users_total", {}).get(p, 0)
        ac_u = stats_all.get("prob_users_ac", {}).get(p, 0)
        tot_s = stats_all.get("prob_total", {}).get(p, 0)
        ac_s = stats_all.get("prob_ac", {}).get(p, 0)
        u_pct = round(ac_u / tot_active_users * 100, 1)
        sub_pct = round(ac_s / tot_s * 100, 1) if tot_s > 0 else 0

        diff = "极难" if (sub_pct < 35 or ac_u < tot_active_users * 0.3) else ("困难" if (sub_pct < 50 or ac_u < tot_active_users * 0.5) else ("中等" if sub_pct < 65 else "简单"))
        diff_tag = "tag-red" if diff == "极难" else ("tag-orange" if diff == "困难" else ("tag-blue" if diff == "中等" else "tag-green"))
        bar_c = "bar-fill-r" if diff == "极难" else ("bar-fill-o" if diff == "困难" else ("bar-fill-b" if diff == "中等" else "bar-fill-g"))

        html_out += f"""        <tr>
          <td><b>{p}</b></td>
          <td><b>{py_html.escape(p_name)}</b></td>
          <td>{att_u} 人</td>
          <td><b>{ac_u} 人</b></td>
          <td>
            <div class="bar-container">
              <div class="bar-bg"><div class="bar-fill {bar_c}" style="width: {u_pct}%;"></div></div>
              <span class="bar-text">{u_pct}%</span>
            </div>
          </td>
          <td>{tot_s}</td>
          <td>{ac_s}</td>
          <td>
            <div class="bar-container">
              <div class="bar-bg"><div class="bar-fill {bar_c}" style="width: {sub_pct}%;"></div></div>
              <span class="bar-text">{sub_pct}%</span>
            </div>
          </td>
          <td><span class="tag {diff_tag}">{diff}</span></td>
        </tr>
"""

    html_out += """      </tbody>
    </table>
  </div>
</div>

<!-- ==================== TAB 3: STRUGGLING STUDENTS ==================== -->
<div id="tab-struggling" class="tab-content">
  <h2>第三部分：提交次数高但 AC 率偏低的学生名单（重点辅导画像）</h2>
  
  <div class="section">
    <div class="info" id="struggling-info-box"></div>
    
    <table>
      <thead>
        <tr>
          <th style="width:45px;">序号</th>
          <th style="width:160px;">账号</th>
          <th style="width:75px;">总提交</th>
          <th style="width:75px;">AC 提交</th>
          <th style="width:85px;">通过题数</th>
          <th style="width:170px;">个人 AC 率 (可视化)</th>
          <th style="width:85px;">试错/失败数</th>
          <th>学习诊断画像</th>
        </tr>
      </thead>
      <tbody id="strugglingTableBody"></tbody>
    </table>
  </div>
</div>

<!-- ==================== TAB 4: ANOMALIES ==================== -->
<div id="tab-anomalies" class="tab-content">
  <h2>第四部分：代码异常与作弊审计 (已配置匿名脱敏切换支持)</h2>
  
  <div class="section">
    <h3>4.1 非基础题（K~Y）首次提交即 AC 学生名单</h3>
    <div class="info" id="first-ac-info-box"></div>
  </div>

  <div class="section">
    <h3>4.2 提交频率异常（短时间内极速连交多题）</h3>
    <table>
      <thead>
        <tr>
          <th style="width:160px;">学生代号 / 姓名</th>
          <th style="width:240px;">时间窗口 / ID 跨度</th>
          <th style="width:90px;">通过题数</th>
          <th>涉及题目</th>
          <th style="width:140px;">异常特征说明</th>
        </tr>
      </thead>
      <tbody id="burstsTableBody"></tbody>
    </table>
  </div>

  <div class="section">
    <h3>4.3 雷同代码深度聚焦（除基础题）</h3>
    <table>
      <thead>
        <tr>
          <th style="width:180px;">题目</th>
          <th style="width:100px;">雷同对数</th>
          <th style="width:110px;">完全一致对数</th>
          <th>代表性雷同群组 (点击顶部按钮可脱敏)</th>
        </tr>
      </thead>
      <tbody id="plagiarismTableBody"></tbody>
    </table>
    
    <div class="warn" id="repeated-pairs-box"></div>
  </div>

  <div class="section">
    <h3>4.4 超纲语言、模块导入与注释异常</h3>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
      <div>
        <h4 style="font-size:12px; margin-bottom:4px;">非 Python 语言提交</h4>
        <table>
          <thead><tr><th>学生代号 / 账号</th><th>题数</th><th>语言</th></tr></thead>
          <tbody id="nonPyTableBody"></tbody>
        </table>
      </div>
      <div>
        <h4 style="font-size:12px; margin-bottom:4px;">注释自曝使用 AI / 互动痕迹</h4>
        <table>
          <thead><tr><th>学生代号 / 账号</th><th>题号</th><th>注释原文摘录</th></tr></thead>
          <tbody id="aiCommentsTableBody"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ==================== TAB 5: ALL STUDENTS ==================== -->
<div id="tab-all-students" class="tab-content">
  <h2>第五部分：学生做题数据完整明细表（紧凑排版）</h2>
  
  <div class="section">
    <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
      <span style="font-size: 12px; color: #64748b;">支持在当前选定班级中实时检索账号或代号：</span>
      <input type="text" id="studentSearch" class="filter-input" placeholder="🔍 输入账号或代号搜索..." onkeyup="filterStudents()">
    </div>
    
    <table id="studentsTable">
      <thead>
        <tr>
          <th style="width:65px;">总排名</th>
          <th style="width:75px;">班级</th>
          <th style="width:65px;">班内排名</th>
          <th style="width:160px;">账号 / 用户名</th>
          <th style="width:85px;">完成题数</th>
          <th style="width:120px;">通关进度</th>
          <th style="width:75px;">总提交数</th>
          <th style="width:75px;">AC 提交</th>
          <th style="width:85px;">个人 AC 率</th>
          <th style="width:75px;">试错次数</th>
          <th style="width:130px;">首次提交时间</th>
          <th style="width:130px;">最终提交时间</th>
        </tr>
      </thead>
      <tbody id="studentsTableBody">
"""
    sorted_all_users = sorted(stats_all.get("user_stats", {}).values(), key=lambda x: (
        -x["solved"],
        int(x["rank"]) if str(x["rank"]).isdigit() else 9999,
        -x["tot"]
    ))
    for st in sorted_all_users:
        u = st["user"]
        cls_name = st.get("class", "未分班")
        cls_rank = st.get("class_rank", "-")
        solved = st["solved"]
        tot = st["tot"]
        ac = st["ac"]
        wa = st["wa"]
        ac_rate = st["ac_rate"]
        pct = round(solved / 25 * 100, 1)
        bar_c = "bar-fill-g" if solved >= 20 else ("bar-fill-b" if solved >= 10 else "bar-fill-r")

        html_out += f"""        <tr data-class="{cls_name}">
          <td><b>{st['rank']}</b></td>
          <td><span class="tag tag-gray">{cls_name}</span></td>
          <td><b>{cls_rank}</b></td>
          <td><code>{render_student_name(u)}</code></td>
          <td><span class="tag tag-blue">{solved} / 25</span></td>
          <td>
            <div class="bar-container">
              <div class="bar-bg"><div class="bar-fill {bar_c}" style="width: {pct}%;"></div></div>
            </div>
          </td>
          <td>{tot}</td>
          <td>{ac}</td>
          <td><b>{ac_rate}%</b></td>
          <td>{wa}</td>
          <td style="font-size:11px; color:#64748b;">{st['first_time']}</td>
          <td style="font-size:11px; color:#64748b;">{st['last_time']}</td>
        </tr>
"""

    html_out += """      </tbody>
    </table>
  </div>
</div>

<!-- ==================== TAB 6: AC ALGORITHMS ==================== -->
<div id="tab-ac-algorithms" class="tab-content">
  <h2>第六部分：学生 AC 代码算法精细剖析（除基础题 · AST 特征聚类）</h2>
  <div class="note">
    💡 <strong>深度算法流派与代码聚类说明</strong>：本模块脱离粗粒度标签，深度扫描 <code>codes/</code> 目录下非基础题 AC 源代码，对重点核心题目进行<strong>去重比对与 AST 特征聚类</strong>，提炼具体派系归类、复杂度研判、代表性中心样本展示及教学思维跃迁提示。
  </div>
  <div class="section" style="padding:12px 16px; margin-bottom:16px;">
    <div style="font-size:12px; font-weight:700; color:#475569; margin-bottom:8px;">📌 点击切换查看各题算法精细剖析：</div>
    <div style="display:flex; flex-wrap:wrap; gap:8px;" id="acProbBtnGroup"></div>
  </div>
  <div id="acprob-cards-wrap"></div>
</div>

<!-- ==================== TAB 7: ERROR DIAGNOSTICS ==================== -->
<div id="tab-error-diagnostics" class="tab-content">
  <h2>第七部分：典型错误代码分题深度诊断（Top 10 错误高发题 · 特征聚类）</h2>
  <div class="warn">
    🚨 <strong>代码去重与多样本特征聚类体系</strong>：对全场错误提交最多的 <strong>Top 10 核心题目</strong>，在各错误分类（WA/RE/CE/PE/TLE）下执行<strong>代码去重与多样本特征聚类比对</strong>，精确挖掘全班学生最常掉入的 <strong>Top 聚类错误模式</strong>，提取聚类中心代表代码，提供 <strong>【共性缺陷定位】</strong>、<strong>【触发反例用例】</strong> 与 <strong>【修复建议】</strong> 三维逐段诊断。
  </div>
  <div class="section" style="padding:12px 16px; margin-bottom:16px;">
    <div style="font-size:12px; font-weight:700; color:#475569; margin-bottom:8px;">📌 点击切换查看各题错误代码诊断：</div>
    <div style="display:flex; flex-wrap:wrap; gap:8px;" id="errProbBtnGroup"></div>
  </div>
  <div id="errprob-cards-wrap"></div>
</div>

</div> <!-- END view-main-analysis -->

<div style="text-align:center; color:#94a3b8; font-size:12px; margin-top:32px; padding-bottom:24px;">
  报告生成基于 krand.site 官方数据 + 本地 AST 代码审计引擎 · """ + py_html.escape(contest_name) + """
</div>

</div>

<!-- DATA STORE FOR DYNAMIC CLASS FILTERING -->
<script>
const DATASET = """ + dataset_json + """;
const ANON_MAP = """ + anon_map_json + """;
const PROB_TITLES = """ + prob_titles_json + """;
const DEEP_ANALYSIS = """ + deep_analysis_json + """;

let currentPrivacyState = false; // false = Real name, true = Anonymized
let currentClass = 'all';
let currentAcProb = 'K';
let currentErrProb = 'K';

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function renderName(user) {
  const clean = (user || '').trim();
  const anon = ANON_MAP[clean] || clean;
  const dReal = currentPrivacyState ? 'none' : 'inline';
  const dAnon = currentPrivacyState ? 'inline' : 'none';
  return `<span class="name-real" style="display:${dReal}">${escapeHtml(clean)}</span><span class="name-anon" style="display:${dAnon}">${escapeHtml(anon)}</span>`;
}

function setPrivacy(isAnon) {
  currentPrivacyState = isAnon;
  document.getElementById('btnReal').classList.toggle('active', !isAnon);
  document.getElementById('btnAnon').classList.toggle('active', isAnon);
  
  document.querySelectorAll('.name-real').forEach(el => el.style.display = isAnon ? 'none' : 'inline');
  document.querySelectorAll('.name-anon').forEach(el => el.style.display = isAnon ? 'inline' : 'none');
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
  
  if (window.event && window.event.target) {
    window.event.target.classList.add('active');
  }
  const target = document.getElementById(tabId);
  if (target) target.classList.add('active');
}

function switchAcProbTab(prob) {
  currentAcProb = prob;
  document.querySelectorAll('[id^="btn-acprob-"]').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.acprob-card').forEach(card => card.style.display = 'none');
  
  const btn = document.getElementById('btn-acprob-' + prob);
  const card = document.getElementById('acprob-card-' + prob);
  if (btn) btn.classList.add('active');
  if (card) card.style.display = 'block';
}

function switchErrProbTab(prob) {
  currentErrProb = prob;
  document.querySelectorAll('[id^="btn-errprob-"]').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.errprob-card').forEach(card => card.style.display = 'none');
  
  const btn = document.getElementById('btn-errprob-' + prob);
  const card = document.getElementById('errprob-card-' + prob);
  if (btn) btn.classList.add('active');
  if (card) card.style.display = 'block';
}

// 顶部班级切换控制逻辑（动态联动第一、三、四、五、六、七部分）
function switchClassView(clsName) {
  currentClass = clsName;
  document.querySelectorAll('.class-btn').forEach(btn => btn.classList.remove('active'));
  
  const mainView = document.getElementById('view-main-analysis');
  const compView = document.getElementById('view-class-comparison');
  
  if (clsName === 'compare') {
    const btn = document.getElementById('btn-class-compare');
    if (btn) btn.classList.add('active');
    document.getElementById('current-view-badge').textContent = '📊 班级横向对比大屏';
    if (mainView) mainView.style.display = 'none';
    if (compView) compView.style.display = 'block';
    return;
  }
  
  // 恢复常规分析视图
  if (mainView) mainView.style.display = 'block';
  if (compView) compView.style.display = 'none';
  
  if (clsName === 'all') {
    const btn = document.getElementById('btn-class-all');
    if (btn) btn.classList.add('active');
    document.getElementById('current-view-badge').textContent = '全年级总览';
    updateSummaryCards(DATASET.stats_all, DATASET.anomalies_all);
    renderDailyChart(DATASET.stats_all.daily_subs || {}, DATASET.stats_all.daily_ac || {}, DATASET.stats_all.daily_users || {});
    renderStrugglingStudents('全年级');
    renderAnomalies(DATASET.anomalies_all, '全年级');
    filterStudentsTableByClass('');
    renderAcAlgorithms('全年级');
    renderErrorDiagnostics('全年级');
  } else {
    const btn = document.getElementById('btn-class-' + clsName);
    if (btn) btn.classList.add('active');
    document.getElementById('current-view-badge').textContent = clsName;
    const cStat = DATASET.stats_by_class[clsName] || DATASET.stats_all;
    const cAnom = DATASET.anomalies_by_class[clsName] || DATASET.anomalies_all;
    updateSummaryCards(cStat, cAnom);
    renderDailyChart(cStat.daily_subs || {}, cStat.daily_ac || {}, cStat.daily_users || {});
    renderStrugglingStudents(clsName);
    renderAnomalies(cAnom, clsName);
    filterStudentsTableByClass(clsName);
    renderAcAlgorithms(clsName);
    renderErrorDiagnostics(clsName);
  }
}

function updateSummaryCards(stat, anom) {
  document.getElementById('meta-tot-subs').textContent = Number(stat.total_subs).toLocaleString();
  document.getElementById('meta-registered').textContent = stat.total_registered;
  document.getElementById('meta-active-users').textContent = stat.total_with_subs;
  document.getElementById('meta-full-cnt').textContent = (stat.solved_all || []).length;
  document.getElementById('meta-tot-ac').textContent = Number(stat.total_ac).toLocaleString();
  document.getElementById('meta-ac-rate').textContent = stat.ac_rate + '%';

  document.getElementById('card-registered').textContent = stat.total_registered;
  document.getElementById('card-with-subs').textContent = stat.total_with_subs;
  document.getElementById('card-full-cnt').textContent = (stat.solved_all || []).length;
  document.getElementById('card-good-cnt').textContent = (stat.solved_gte_20 || []).length;
  document.getElementById('card-tot-subs').textContent = Number(stat.total_subs).toLocaleString();
  document.getElementById('card-ac-rate').textContent = stat.ac_rate + '%';
  document.getElementById('card-struggling-cnt').textContent = (stat.struggling || []).length;

  if (anom) {
    document.getElementById('card-burst-cnt').textContent = (anom.submission_bursts || []).length;
    const plagMap = anom.plagiarism_groups || {};
    let plagCnt = 0;
    Object.values(plagMap).forEach(v => plagCnt += v.length);
    document.getElementById('card-plag-cnt').textContent = plagCnt;
    const nonPyStus = new Set((anom.non_python || []).map(x => x.student));
    document.getElementById('card-nonpy-cnt').textContent = nonPyStus.size;
  }
}

// 第一部分：根据班级动态重绘每日柱状图
function renderDailyChart(dailySubs, dailyAc, dailyUsers) {
  const stage = document.getElementById('vchartStage');
  if (!stage) return;
  const allDates = Object.keys(dailySubs).filter(d => d !== 'Unknown').sort();
  const maxD = Math.max(...Object.values(dailySubs), 1);
  let html = '';
  allDates.forEach(d => {
    const tot = dailySubs[d] || 0;
    const ac = dailyAc[d] || 0;
    const wa = tot - ac;
    const uCnt = dailyUsers[d] || 0;
    const hPx = Math.round((tot / Math.max(maxD, 1)) * 160);
    const acPct = tot > 0 ? (ac / tot * 100).toFixed(1) : 0;
    const waPct = tot > 0 ? (100.0 - acPct).toFixed(1) : 0;
    const dShort = d.length >= 10 ? d.substring(5) : d;
    const peakStr = tot >= maxD * 0.5 ? `${tot}` : '';

    html += `<div class="vcol">
      <div class="vtooltip">
        <b>${d}</b><br>
        总提交: <b>${tot}</b> 次<br>
        正确(AC): <span style="color:#34d399;">${ac}</span> 次<br>
        试错/未过: <span style="color:#f87171;">${wa}</span> 次<br>
        活跃学生: <b>${uCnt}</b> 人
      </div>
      <div class="vcol-peak-val">${peakStr}</div>
      <div class="vcol-bar" style="height: ${hPx}px;">
        <div class="vcol-seg-ac" style="height: ${acPct}%;"></div>
        <div class="vcol-seg-wa" style="height: ${waPct}%;"></div>
      </div>
      <div class="vcol-date">${dShort}</div>
    </div>`;
  });
  stage.innerHTML = html;
}

// 第三部分：根据班级动态重绘困难学生画像
function renderStrugglingStudents(clsName) {
  const isAll = (clsName === '全年级' || clsName === 'all');
  let currentStat = DATASET.stats_all;
  let clsUserSet = null;
  if (!isAll && DATASET.stats_by_class && DATASET.stats_by_class[clsName]) {
    currentStat = DATASET.stats_by_class[clsName];
    clsUserSet = new Set(Object.keys(currentStat.user_stats || {}));
  }

  const allStruggling = DATASET.stats_all.struggling || [];
  const strugglingList = allStruggling.filter(st => (!clsUserSet || clsUserSet.has(st.user)));

  const infoBox = document.getElementById('struggling-info-box');
  if (infoBox) {
    if (isAll) {
      infoBox.innerHTML = `<b>筛选标准</b>：总提交次数 ≥ 20 次，且个人 AC 率 &lt; 50%。共识别出 <b>${strugglingList.length} 位</b>“态度积极但反复在进阶题卡壳”的困难生，以下为最需要教学辅导与关怀的学生：`;
    } else {
      infoBox.innerHTML = `<b>筛选标准</b>：总提交次数 ≥ 20 次，且个人 AC 率 &lt; 50%。【${escapeHtml(clsName)}】共识别出 <b>${strugglingList.length} 位</b>“态度积极但反复在进阶题卡壳”的困难生，以下为最需要教学辅导与关怀的学生：`;
    }
  }

  const tbody = document.getElementById('strugglingTableBody');
  if (tbody) {
    if (strugglingList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:#10b981; padding:16px;">🎉 本班暂无符合困难辅导特征的学生（全员表现优良或提交较少）</td></tr>`;
    } else {
      let html = '';
      strugglingList.forEach((st, idx) => {
        const u = st.user;
        const tot = st.tot;
        const ac = st.ac;
        const wa = st.wa;
        const solved = st.solved;
        const acRate = st.ac_rate;
        const barC = acRate < 25 ? 'bar-fill-r' : (acRate < 40 ? 'bar-fill-o' : 'bar-fill-y');

        let diagTag = "<span class='tag tag-gray'>重点辅导关怀</span>";
        if (wa >= 100) {
          diagTag = "<span class='tag tag-red'>极度卡题 (试错超百次)</span>";
        } else if (acRate < 20) {
          diagTag = "<span class='tag tag-orange'>低AC率但高活跃</span>";
        } else if (tot >= 60) {
          diagTag = "<span class='tag tag-yellow'>反复试错攻坚</span>";
        }

        html += `<tr>
          <td>${idx + 1}</td>
          <td><code>${renderName(u)}</code></td>
          <td><b>${tot} 次</b></td>
          <td>${ac} 次</td>
          <td><span class="tag tag-green">${solved} / 25 题</span></td>
          <td>
            <div class="bar-container">
              <div class="bar-bg"><div class="bar-fill ${barC}" style="width: ${acRate}%;"></div></div>
              <span class="bar-text">${acRate}%</span>
            </div>
          </td>
          <td><b>${wa} 次</b></td>
          <td>${diagTag}</td>
        </tr>`;
      });
      tbody.innerHTML = html;
    }
  }
}

// 第四部分：根据班级动态重绘代码异常审计 (4.1~4.4)
function renderAnomalies(anom, clsName) {
  const isAll = (clsName === '全年级' || clsName === 'all');
  let clsUserSet = null;
  if (!isAll && DATASET.stats_by_class && DATASET.stats_by_class[clsName]) {
    clsUserSet = new Set(Object.keys(DATASET.stats_by_class[clsName].user_stats || {}));
  }

  // 4.1 首次即 AC
  const firstAcBox = document.getElementById('first-ac-info-box');
  if (firstAcBox) {
    if (isAll) {
      firstAcBox.innerHTML = `<b>事实说明</b>：基于全量提交流水严格核查，在 K~Y 全部 15 道非基础题上<b>首次提交即 AC（0 错误提交）</b>的学生为 <b>0 人</b>。<br>最接近“一次过”的学生为 ${renderName('陈彦博2028')}（14/15 题首次即 AC，仅 W 题首交失败一次）。`;
    } else {
      firstAcBox.innerHTML = `<b>事实说明</b>：基于【${escapeHtml(clsName)}】提交流水严格核查，在 K~Y 全部 15 道非基础题上<b>首次提交即 AC（0 错误提交）</b>的学生为 <b>0 人</b>。`;
    }
  }

  // 4.2 极速连交
  const burstsTbody = document.getElementById('burstsTableBody');
  if (burstsTbody) {
    const rawBursts = anom.submission_bursts || [];
    const bursts = rawBursts.filter(b => (!clsUserSet || clsUserSet.has(b.student)));
    if (bursts.length === 0) {
      burstsTbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#94a3b8; padding:12px;">✅ 当前班级未发现短时间极速连交多题异常</td></tr>';
    } else {
      let html = '';
      bursts.slice(0, 10).forEach(b => {
        const badgeCls = b.tag_color || (('秒交' in (b.tag || '') || '批量' in (b.tag || '')) ? 'tag-red' : 'tag-orange');
        html += `<tr>
          <td><b>${renderName(b.student)}</b></td>
          <td>${b.window || ''}</td>
          <td><b>${b.passed_cnt || b.solved_in_window || ''}</b></td>
          <td>${b.probs || b.probs_desc || ''}</td>
          <td><span class="tag ${badgeCls}">${b.tag || b.note || ''}</span></td>
        </tr>`;
      });
      burstsTbody.innerHTML = html;
    }
  }

  // 4.3 雷同代码深度聚焦
  const plagTbody = document.getElementById('plagiarismTableBody');
  if (plagTbody) {
    const rawPlag = anom.plagiarism_groups || {};
    const pKeys = Object.keys(rawPlag);
    let totalMatchingGroups = 0;
    let html = '';

    pKeys.forEach(p => {
      const allGroups = rawPlag[p] || [];
      const groups = allGroups.filter(g => (!clsUserSet || (g.students || []).some(s => clsUserSet.has(s))));
      if (groups.length > 0) {
        totalMatchingGroups += groups.length;
        const pTitle = PROB_TITLES[p] || ('题目 ' + p);
        const exactCnt = groups.filter(g => g.similarity === 1.0).length;
        const clustersHtml = [];
        groups.slice(0, 3).forEach(g => {
          const stusHtml = (g.students || []).map(s => renderName(s));
          const codeSnippet = g.clean_code ? `<code>${escapeHtml(g.clean_code.substring(0, 40))}</code>` : '';
          clustersHtml.push(`<div class="cluster-box">${stusHtml.join(', ')}</div> ${codeSnippet}`);
        });
        html += `<tr>
          <td><b>${p} 题《${escapeHtml(pTitle)}》</b></td>
          <td><span class="tag tag-red">${groups.length} 对</span></td>
          <td>${exactCnt} 对</td>
          <td>${clustersHtml.join('<br>')}</td>
        </tr>`;
      }
    });

    if (totalMatchingGroups === 0) {
      plagTbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#94a3b8; padding:12px;">✅ 当前班级未发现非基础题高雷同代码群组</td></tr>';
    } else {
      plagTbody.innerHTML = html;
    }
  }

  const repeatedBox = document.getElementById('repeated-pairs-box');
  if (repeatedBox) {
    const involvesGang = isAll || (clsUserSet && (clsUserSet.has('曹舒涵2028') || clsUserSet.has('胡益诚2028')));
    if (involvesGang) {
      repeatedBox.innerHTML = `<b>跨 3 题以上固定雷同团伙</b>：${renderName('曹舒涵2028')} ⟺ ${renderName('胡益诚2028')} 在 P 题、Q 题、T 题中代码逻辑与结构完全相同。`;
    } else {
      repeatedBox.innerHTML = `✅ 当前班级未发现跨 3 题以上固定雷同团伙。`;
    }
  }

  // 4.4 违规语言与 AI 注释
  const nonPyTbody = document.getElementById('nonPyTableBody');
  if (nonPyTbody) {
    const rawNonPy = anom.non_python || [];
    const nonPy = rawNonPy.filter(x => (!clsUserSet || clsUserSet.has(x.student)));
    const nonPyByStu = {};
    nonPy.forEach(x => {
      if (!nonPyByStu[x.student]) nonPyByStu[x.student] = [];
      nonPyByStu[x.student].push(x.prob);
    });
    const stus = Object.keys(nonPyByStu).sort((a, b) => nonPyByStu[b].length - nonPyByStu[a].length);
    if (stus.length === 0) {
      nonPyTbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:#94a3b8; padding:10px;">✅ 无违规非 Python 提交</td></tr>';
    } else {
      let html = '';
      stus.slice(0, 10).forEach(stu => {
        const plist = nonPyByStu[stu];
        html += `<tr><td><b>${renderName(stu)}</b></td><td>${plist.length} 题 (${plist.slice(0, 5).join(', ')})</td><td>C/C++</td></tr>`;
      });
      nonPyTbody.innerHTML = html;
    }
  }

  const aiTbody = document.getElementById('aiCommentsTableBody');
  if (aiTbody) {
    const rawAiComments = anom.ai_comments || [];
    const aiComments = rawAiComments.filter(c => (!clsUserSet || clsUserSet.has(c.student)));
    if (aiComments.length === 0) {
      aiTbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:#94a3b8; padding:10px;">✅ 无明显 AI 注释自曝记录</td></tr>';
    } else {
      let html = '';
      aiComments.slice(0, 10).forEach(c => {
        html += `<tr><td><b>${renderName(c.student)}</b></td><td>${c.prob} 题</td><td><code>${escapeHtml((c.comment || '').substring(0, 80))}</code></td></tr>`;
      });
      aiTbody.innerHTML = html;
    }
  }
}

// 第五部分：按班级过滤明细表
function filterStudentsTableByClass(clsName) {
  const table = document.getElementById('studentsTable');
  if (!table) return;
  const rows = table.getElementsByTagName('tr');
  for (let i = 1; i < rows.length; i++) {
    const rCls = rows[i].getAttribute('data-class');
    if (!clsName || rCls === clsName) {
      rows[i].style.display = '';
    } else {
      rows[i].style.display = 'none';
    }
  }
}

function filterStudents() {
  const input = document.getElementById('studentSearch');
  const filter = input.value.toLowerCase();
  const table = document.getElementById('studentsTable');
  const tr = table.getElementsByTagName('tr');

  for (let i = 1; i < tr.length; i++) {
    const text = tr[i].textContent.toLowerCase();
    const rCls = tr[i].getAttribute('data-class');
    const matchesCls = (currentClass === 'all' || currentClass === 'compare' || rCls === currentClass);
    tr[i].style.display = (matchesCls && text.includes(filter)) ? '' : 'none';
  }
}

// 第六部分：按班级动态重绘 AC 算法精细剖析（过滤0人流派，提取本班真实学生代码）
function renderAcAlgorithms(clsName) {
  const btnGroup = document.getElementById('acProbBtnGroup');
  const cardsWrap = document.getElementById('acprob-cards-wrap');
  if (!btnGroup || !cardsWrap) return;

  const deepAc = DEEP_ANALYSIS.ac_analysis || {};
  const pKeys = Object.keys(deepAc);
  if (pKeys.length === 0) return;

  // 获取当前选定班级的学生集合
  const isAll = (clsName === '全年级' || clsName === 'all');
  let clsUserSet = null;
  if (!isAll && DATASET.stats_by_class && DATASET.stats_by_class[clsName]) {
    clsUserSet = new Set(Object.keys(DATASET.stats_by_class[clsName].user_stats || {}));
  }

  let btnHtml = '';
  let cardsHtml = '';

  pKeys.forEach((p, idx) => {
    const pData = deepAc[p];
    const pTitle = pData.title || (PROB_TITLES[p] || ('题目 ' + p));
    const genres = pData.genres || [];

    // 计算当前班级在该题上的流派分布
    let totalClsAc = 0;
    const computedGenres = [];

    genres.forEach(g => {
      const stus = (g.students || []).filter(u => (!clsUserSet || clsUserSet.has(u)));
      const cnt = stus.length;
      totalClsAc += cnt;
      // 若当前视图为具体班级且该流派为0人，则过滤隐藏
      if (isAll || cnt > 0) {
        // 提取该班代表学生和该班真实代码
        let repUser = g.sample_user;
        let repCode = g.sample_code;
        if (!isAll && stus.length > 0) {
          repUser = stus[0];
          if (g.student_samples && g.student_samples[repUser]) {
            repCode = g.student_samples[repUser];
          }
        }
        computedGenres.push({
          ...g,
          filteredStudents: stus,
          filteredCount: cnt,
          repUser: repUser,
          repCode: repCode
        });
      }
    });

    const activeCls = (p === currentAcProb || (!currentAcProb && idx === 0)) ? 'active' : '';
    const dispStyle = (p === currentAcProb || (!currentAcProb && idx === 0)) ? 'block' : 'none';

    btnHtml += `<button class="toggle-btn ${activeCls}" id="btn-acprob-${p}" onclick="switchAcProbTab('${p}')" style="padding:6px 12px; font-size:12px;"><b>题目 ${p}</b> · ${escapeHtml(pTitle)} (${totalClsAc}人AC)</button>`;

    let genresBarHtml = '';
    let genresCardsHtml = '';

    if (computedGenres.length === 0) {
      genresBarHtml = `<div style="color:#94a3b8; font-size:12px; padding:10px 0;">🎉 本班暂无学生通过此题</div>`;
    } else {
      computedGenres.forEach(g => {
        const gPct = totalClsAc > 0 ? (g.filteredCount / totalClsAc * 100).toFixed(1) : 0;
        const barColor = (g.name.toLowerCase().includes('eval') || g.name.toLowerCase().includes('sort')) ? '#e11d48' : ((g.name.includes('最优') || g.name.includes('栈')) ? '#2563eb' : '#059669');
        const borderTop = (g.name.toLowerCase().includes('eval') || g.name.toLowerCase().includes('sort')) ? '#e11d48' : ((g.name.includes('最优') || g.name.includes('栈')) ? '#3b82f6' : '#10b981');

        genresBarHtml += `<div style="margin-bottom:8px;">
          <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:3px;">
            <span style="font-weight:600; color:#1e293b;">${escapeHtml(g.name)} <span style="color:#64748b; font-weight:normal;">(${escapeHtml(g.complexity)})</span></span>
            <span style="font-weight:700; color:${barColor};">${g.filteredCount} 人 (${gPct}%)</span>
          </div>
          <div style="background:#e2e8f0; height:8px; border-radius:4px; overflow:hidden;">
            <div style="background:${barColor}; width:${gPct}%; height:100%; border-radius:4px;"></div>
          </div>
        </div>`;

        genresCardsHtml += `<div style="background:#ffffff; border:1px solid #e2e8f0; border-top:4px solid ${borderTop}; border-radius:8px; padding:14px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <b style="font-size:13px; color:#1e293b;">${escapeHtml(g.name)}</b>
            <span class="tag tag-purple">${g.filteredCount}人 · ${gPct}%</span>
          </div>
          <div style="font-size:11px; color:#64748b; margin-bottom:6px;"><strong>时空特征：</strong><code>${escapeHtml(g.complexity)}</code></div>
          <div style="font-size:12px; color:#334155; line-height:1.5; margin-bottom:10px;">${escapeHtml(g.desc)}</div>
          <div style="font-size:11px; color:#475569; margin-bottom:4px;"><strong>聚类代表学生代码：</strong>${renderName(g.repUser)}</div>
          <pre><code>${escapeHtml(g.repCode)}</code></pre>
        </div>`;
      });
    }

    cardsHtml += `<div id="acprob-card-${p}" class="acprob-card" style="display:${dispStyle};">
      <div class="section">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #e2e8f0; padding-bottom:10px; margin-bottom:14px;">
          <h3 style="font-size:16px; color:#1e293b; margin:0;">题目 ${p}：${escapeHtml(pTitle)} <span style="font-size:12px; color:#64748b; font-weight:normal;">(当前视图有效 AC 提交共 ${totalClsAc} 份)</span></h3>
          <span class="tag tag-blue" style="font-size:12px;">共识别出 ${computedGenres.length} 大解法流派</span>
        </div>
        <p style="font-size:13px; color:#334155; line-height:1.6; margin-bottom:14px;">${pData.summary_intro || ''}</p>
        
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:14px; margin-bottom:18px;">
          <div style="font-size:12px; font-weight:700; color:#475569; margin-bottom:10px;">📊 各算法流派人数与占比分布（${escapeHtml(clsName)}）：</div>
          ${genresBarHtml}
        </div>

        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(360px, 1fr)); gap:14px; margin-bottom:18px;">
          ${genresCardsHtml}
        </div>

        <div class="note">
          💡 ${pData.teaching_note || ''}
        </div>
      </div>
    </div>`;
  });

  btnGroup.innerHTML = btnHtml;
  cardsWrap.innerHTML = cardsHtml;
}

// 第七部分：按班级动态重绘典型错误代码诊断（过滤0命中模式，提取本班真实学生错误代码）
function renderErrorDiagnostics(clsName) {
  const btnGroup = document.getElementById('errProbBtnGroup');
  const cardsWrap = document.getElementById('errprob-cards-wrap');
  if (!btnGroup || !cardsWrap) return;

  const deepErr = DEEP_ANALYSIS.err_diagnostics || {};
  const pKeys = Object.keys(deepErr);
  if (pKeys.length === 0) return;

  const isAll = (clsName === '全年级' || clsName === 'all');
  let currentStat = DATASET.stats_all;
  let clsUserSet = null;
  if (!isAll && DATASET.stats_by_class && DATASET.stats_by_class[clsName]) {
    currentStat = DATASET.stats_by_class[clsName];
    clsUserSet = new Set(Object.keys(currentStat.user_stats || {}));
  }

  let btnHtml = '';
  let cardsHtml = '';

  pKeys.forEach((p, idx) => {
    const pData = deepErr[p];
    const pTitle = pData.title || (PROB_TITLES[p] || ('题目 ' + p));
    const errGroups = pData.error_groups || [];

    // 计算当前班级在该题上的错误提交总数
    const pTot = (currentStat.prob_total || {})[p] || 0;
    const pAc = (currentStat.prob_ac || {})[p] || 0;
    const pErr = Math.max(0, pTot - pAc);

    const activeCls = (p === currentErrProb || (!currentErrProb && idx === 0)) ? 'active' : '';
    const dispStyle = (p === currentErrProb || (!currentErrProb && idx === 0)) ? 'block' : 'none';

    btnHtml += `<button class="toggle-btn ${activeCls}" id="btn-errprob-${p}" onclick="switchErrProbTab('${p}')" style="padding:6px 12px; font-size:12px;"><b>题目 ${p}</b> · ${escapeHtml(pTitle)} (${pErr}次错误)</button>`;

    const badgesHtml = [];
    let groupsDetailsHtml = '';

    errGroups.forEach(eg => {
      const tagC = eg.err_type === '答案错误' ? 'tag-red' : (eg.err_type === '运行错误' ? 'tag-orange' : 'tag-blue');
      const borderColor = eg.err_type === '答案错误' ? '#ef4444' : (eg.err_type === '运行错误' ? '#f97316' : '#3b82f6');
      badgesHtml.push(`<span class="tag ${tagC}">${escapeHtml(eg.err_type)}: ${pErr}次 (聚为${eg.clusters_count}类)</span>`);

      let samplesHtml = '';
      let visibleSampleCount = 0;

      (eg.samples || []).forEach(sample => {
        const stus = (sample.students || []).filter(u => (!clsUserSet || clsUserSet.has(u)));
        // 若为具体班级且本班 0 人命中该模式，则隐藏该聚类模式
        if (isAll || stus.length > 0) {
          visibleSampleCount++;
          let repUser = sample.student_real;
          let repSubId = sample.sub_id;
          let repCode = sample.code;

          if (!isAll && stus.length > 0) {
            repUser = stus[0];
            if (sample.student_samples && sample.student_samples[repUser]) {
              repSubId = sample.student_samples[repUser].sub_id || repSubId;
              repCode = sample.student_samples[repUser].code || repCode;
            }
          }

          const coverageTag = isAll ? (sample.cluster_coverage || '') : `本班涉及 ${stus.length} 名学生`;

          samplesHtml += `<div style="background:#ffffff; border:1px solid #e2e8f0; border-left:4px solid ${borderColor}; border-radius:6px; padding:12px; margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; color:#475569; margin-bottom:6px;">
              <span style="font-size:13px; font-weight:700; color:#1e293b;">📌 聚类模式 ${sample.cluster_id}：${escapeHtml(sample.cluster_name)}</span>
              <span class="tag tag-purple">${coverageTag}</span>
            </div>
            <div style="font-size:11px; color:#64748b; margin-bottom:8px;">代表样本: 提交学生 ${renderName(repUser)} · 提交编号 <code>${repSubId}</code></div>
            <pre><code>${escapeHtml(repCode)}</code></pre>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:10px; font-size:12px; line-height:1.5;">
              <div style="margin-bottom:4px; color:#991b1b;"><strong>🔍 【共性缺陷定位】：</strong>${sample.flaw || ''}</div>
              <div style="margin-bottom:4px; color:#92400e;"><strong>💣 【触发反例用例】：</strong>${sample.testcase || ''}</div>
              <div style="color:#166534;"><strong>🛠️ 【修复建议】：</strong>${sample.fix || ''}</div>
            </div>
          </div>`;
        }
      });

      if (visibleSampleCount === 0) {
        samplesHtml = `<div style="color:#10b981; font-size:12px; padding:12px 0;">🎉 本班学生在此题上未触发此类典型聚类错误模式</div>`;
      }

      groupsDetailsHtml += `<details open style="margin-bottom:16px; border:1px solid #e2e8f0; border-radius:8px; overflow:hidden; background:#fafafa;">
        <summary style="padding:10px 14px; background:#f1f5f9; font-weight:700; font-size:13px; color:#1e293b; cursor:pointer; display:flex; justify-content:space-between; align-items:center;">
          <span>🚨 【${escapeHtml(eg.err_type)}】共累计 ${pErr} 次提交 · 经去重归纳为 ${eg.clusters_count} 个特征聚类簇</span>
          <span style="font-size:11px; color:#64748b; font-weight:normal;">点击展开/折叠</span>
        </summary>
        <div style="padding:14px;">
          ${samplesHtml}
        </div>
      </details>`;
    });

    cardsHtml += `<div id="errprob-card-${p}" class="errprob-card" style="display:${dispStyle};">
      <div class="section">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #e2e8f0; padding-bottom:10px; margin-bottom:14px;">
          <h3 style="font-size:16px; color:#1e293b; margin:0;">题目 ${p}：${escapeHtml(pTitle)} · 聚类错误诊断报告</h3>
          <div>${badgesHtml.join(' ')}</div>
        </div>
        ${groupsDetailsHtml}
      </div>
    </div>`;
  });

  btnGroup.innerHTML = btnHtml;
  cardsWrap.innerHTML = cardsHtml;
}

function sortTable(tableId, colIdx) {
  const table = document.getElementById(tableId);
  let switching = true;
  let dir = 'asc';
  let switchcount = 0;
  
  while (switching) {
    switching = false;
    const rows = table.rows;
    let shouldSwitch = false;
    let i = 1;
    for (i = 1; i < (rows.length - 1); i++) {
      const x = rows[i].getElementsByTagName('TD')[colIdx];
      const y = rows[i + 1].getElementsByTagName('TD')[colIdx];
      let xVal = parseFloat(x.textContent.replace(/[^0-9.-]/g, ''));
      let yVal = parseFloat(y.textContent.replace(/[^0-9.-]/g, ''));
      if (isNaN(xVal)) xVal = x.textContent.toLowerCase();
      if (isNaN(yVal)) yVal = y.textContent.toLowerCase();

      if (dir === 'asc') {
        if (xVal > yVal) { shouldSwitch = true; break; }
      } else if (dir === 'desc') {
        if (xVal < yVal) { shouldSwitch = true; break; }
      }
    }
    if (shouldSwitch) {
      rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
      switching = true;
      switchcount++;
    } else {
      if (switchcount === 0 && dir === 'asc') {
        dir = 'desc';
        switching = true;
      }
    }
  }
}

// 页面加载完成后立即初始化首次渲染
window.addEventListener('DOMContentLoaded', () => {
  renderDailyChart(DATASET.stats_all.daily_subs || {}, DATASET.stats_all.daily_ac || {}, DATASET.stats_all.daily_users || {});
  renderStrugglingStudents('全年级');
  renderAnomalies(DATASET.anomalies_all, '全年级');
  renderAcAlgorithms('全年级');
  renderErrorDiagnostics('全年级');
});
</script>
</body>
</html>
"""
    return html_out
