#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_report.py - 多班级全景教学分析 HTML 报告生成脚本 (Pro 升级版)
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

# 导入同目录下的解析与模板模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from class_parser import build_class_mapping, clean_name
from report_template import render_html

def is_ac(result):
    return any(kw in str(result) for kw in ["Accept", "AC", "正确", "Correct"])

def parse_date(time_raw):
    if not time_raw:
        return "Unknown"
    m = re.search(r"(\d{4}-\d{2}-\d{2})", time_raw)
    if m:
        return m.group(1)
    m = re.search(r"(\d{2}-\d{2})\s+\d{2}:\d{2}", time_raw)
    if m:
        return "2026-" + m.group(1)
    return "Unknown"

def build_anon_map(rank_users, all_subs):
    rank_order = [r["user"] for r in rank_users]
    all_names = set(rank_order + [r.get("nick", "") for r in rank_users]
                    + [s["user"] for s in all_subs] + [s.get("nick", "") for s in all_subs])
    other = sorted([n for n in all_names if n and n not in rank_order])
    ordered = rank_order + other
    mapping = {}
    for idx, name in enumerate(ordered, 1):
        mapping[name] = f"Student_{idx:03d}"
    return mapping

def compute_single_stats(rank_users_subset, all_subs_subset, all_probs, roster_students_count=0):
    max_solved = max((u["solved"] for u in rank_users_subset), default=0)
    users_with_subs = set(s["user"] for s in all_subs_subset)
    
    prob_total = defaultdict(int)
    prob_ac_cnt = defaultdict(int)
    prob_users_total = defaultdict(set)
    prob_users_ac = defaultdict(set)
    daily_subs = defaultdict(int)
    daily_ac = defaultdict(int)
    daily_users = defaultdict(set)

    for s in all_subs_subset:
        p = s["prob"]
        d = parse_date(s.get("time_raw", ""))
        prob_total[p] += 1
        prob_users_total[p].add(s["user"])
        daily_subs[d] += 1
        daily_users[d].add(s["user"])
        if is_ac(s.get("result", "")):
            prob_ac_cnt[p] += 1
            prob_users_ac[p].add(s["user"])
            daily_ac[d] += 1

    total_probs_cnt = len(all_probs) if all_probs else 25

    solved_all = [u for u in rank_users_subset if u["solved"] >= total_probs_cnt]
    solved_gte_20 = [u for u in rank_users_subset if u["solved"] >= int(total_probs_cnt * 0.8)]
    solved_gte_10 = [u for u in rank_users_subset if int(total_probs_cnt * 0.4) <= u["solved"] < int(total_probs_cnt * 0.8)]
    solved_lt_10 = [u for u in rank_users_subset if 1 <= u["solved"] < int(total_probs_cnt * 0.4)]
    solved_0 = [u for u in rank_users_subset if u["solved"] == 0]

    total_subs = len(all_subs_subset)
    total_ac = sum(1 for s in all_subs_subset if is_ac(s.get("result", "")))
    ac_rate = (total_ac / max(total_subs, 1) * 100)
    actual_users_cnt = len(rank_users_subset)
    avg_solved = (sum(u["solved"] for u in rank_users_subset) / max(actual_users_cnt, 1))
    avg_subs = (total_subs / max(actual_users_cnt, 1))

    return {
        "roster_count": roster_students_count,
        "total_registered": actual_users_cnt,
        "total_with_subs": len(users_with_subs),
        "attend_rate": (actual_users_cnt / max(roster_students_count, 1) * 100) if roster_students_count > 0 else 100.0,
        "max_solved": max_solved,
        "avg_solved": round(avg_solved, 1),
        "avg_subs": round(avg_subs, 1),
        "solved_all": solved_all,
        "solved_gte_20": solved_gte_20,
        "solved_gte_10": solved_gte_10,
        "solved_lt_10": solved_lt_10,
        "solved_0": solved_0,
        "total_subs": total_subs,
        "total_ac": total_ac,
        "ac_rate": round(ac_rate, 1),
        "prob_total": dict(prob_total),
        "prob_ac": dict(prob_ac_cnt),
        "prob_users_total": {k: len(v) for k, v in prob_users_total.items()},
        "prob_users_ac": {k: len(v) for k, v in prob_users_ac.items()},
        "daily_subs": dict(daily_subs),
        "daily_ac": dict(daily_ac),
        "daily_users": {k: len(v) for k, v in daily_users.items()}
    }

def filter_anomalies_for_class(anomalies, class_users_set, name_or_user_to_class):
    """针对特定班级过滤异常与雷同，并标记是否为跨班串通"""
    if not anomalies:
        return {}
    
    cls_anom = {}
    
    def matches_class(identifier):
        if not identifier:
            return False
        clean_id = clean_name(identifier)
        if clean_id in class_users_set or identifier in class_users_set:
            return True
        return False

    cls_anom["non_python"] = [x for x in anomalies.get("non_python", []) if matches_class(x.get("student"))]
    cls_anom["advanced_syntax"] = [x for x in anomalies.get("advanced_syntax", []) if matches_class(x.get("student"))]
    cls_anom["advanced_syntax_by_student"] = [x for x in anomalies.get("advanced_syntax_by_student", []) if matches_class(x.get("student"))]
    cls_anom["submission_bursts"] = [x for x in anomalies.get("submission_bursts", []) if matches_class(x.get("student"))]
    cls_anom["ai_comments"] = [x for x in anomalies.get("ai_comments", []) if matches_class(x.get("student"))]
    cls_anom["first_ac_analysis"] = anomalies.get("first_ac_analysis", {})

    orig_plag = anomalies.get("plagiarism_groups", {})
    cls_plag = {}
    for prob, groups in orig_plag.items():
        prob_groups = []
        for g in groups:
            stus = g.get("students", [])
            if any(matches_class(st) for st in stus):
                stu_details = []
                classes_in_group = set()
                for st in stus:
                    c_name = name_or_user_to_class.get(st, name_or_user_to_class.get(clean_name(st), "未知班级"))
                    classes_in_group.add(c_name)
                    stu_details.append({"student": st, "class": c_name})
                is_cross_class = (len(classes_in_group) > 1)
                
                g_copy = dict(g)
                g_copy["stu_details"] = stu_details
                g_copy["is_cross_class"] = is_cross_class
                prob_groups.append(g_copy)
        if prob_groups:
            cls_plag[prob] = prob_groups
    cls_anom["plagiarism_groups"] = cls_plag

    orig_pairs = anomalies.get("repeated_pairs", {})
    cls_pairs = {}
    for pair_key, probs in orig_pairs.items():
        parts = pair_key.split("|")
        if any(matches_class(p) for p in parts):
            cls_pairs[pair_key] = probs
    cls_anom["repeated_pairs"] = cls_pairs

    return cls_anom

def build_full_dataset(rank_users, all_subs, anomalies, deep_analysis, prob_titles, class_mapping):
    user_class_map = class_mapping["user_class_map"]
    name_or_user_to_class = class_mapping.get("name_or_user_to_class", user_class_map)
    class_students_map = class_mapping["class_students_map"]
    classes_list = class_mapping["classes_list"]
    roster_counts = {c: len(sts) for c, sts in class_mapping.get("roster_class_to_students", {}).items()}

    all_probs = sorted(list(set([s["prob"] for s in all_subs] + list(prob_titles.keys()))), key=lambda x: (len(x), x))
    if not all_probs:
        all_probs = [chr(ord('A') + i) for i in range(25)]

    user_stats = {}
    for r in rank_users:
        u = r["user"]
        user_stats[u] = {
            "rank": r["rank"], "user": u, "nick": r.get("nick", u),
            "class": user_class_map.get(u, "未分班"),
            "solved": r["solved"], "penalty": r.get("penalty", "0"),
            "tot": 0, "ac": 0, "first_time": "无", "last_time": "无"
        }

    for s in all_subs:
        u = s["user"]
        if u not in user_stats:
            user_stats[u] = {
                "rank": "未上榜", "user": u, "nick": s.get("nick", u),
                "class": user_class_map.get(u, "未分班"),
                "solved": 0, "penalty": "0",
                "tot": 0, "ac": 0, "first_time": "无", "last_time": "无"
            }
        st = user_stats[u]
        st["tot"] += 1
        t_raw = s.get("time_raw", "").split("[")[0].strip()
        if st["first_time"] == "无":
            st["first_time"] = t_raw
        st["last_time"] = t_raw
        if is_ac(s.get("result", "")):
            st["ac"] += 1

    for st in user_stats.values():
        st["wa"] = st["tot"] - st["ac"]
        st["ac_rate"] = round((st["ac"] / st["tot"] * 100), 1) if st["tot"] > 0 else 0.0

    for cls_name, u_list in class_students_map.items():
        cls_sts = [user_stats[u] for u in u_list if u in user_stats]
        cls_sts.sort(key=lambda x: (
            -x["solved"],
            int(x["rank"]) if str(x["rank"]).isdigit() else 9999,
            -x["tot"]
        ))
        for idx, st in enumerate(cls_sts, 1):
            st["class_rank"] = idx

    total_roster_count = sum(roster_counts.values()) if roster_counts else len(user_stats)
    stats_all = compute_single_stats(list(user_stats.values()), all_subs, all_probs, total_roster_count)
    stats_all["user_stats"] = user_stats
    stats_all["struggling"] = sorted(
        [st for st in user_stats.values() if st["tot"] >= 20 and st["ac_rate"] < 50],
        key=lambda x: (x["ac_rate"], -x["tot"])
    )

    stats_by_class = {}
    anomalies_by_class = {}

    for cls_name in classes_list:
        cls_u_set = set(class_students_map.get(cls_name, []))
        # 补充真实姓名
        cls_names_and_users = set(cls_u_set)
        for u in cls_u_set:
            if u in user_stats:
                cls_names_and_users.add(user_stats[u]["nick"])
                cls_names_and_users.add(clean_name(user_stats[u]["nick"]))

        cls_rank_users = [st for u, st in user_stats.items() if u in cls_u_set]
        cls_subs = [s for s in all_subs if s["user"] in cls_u_set]
        cls_roster_cnt = roster_counts.get(cls_name, len(cls_rank_users))

        c_stat = compute_single_stats(cls_rank_users, cls_subs, all_probs, cls_roster_cnt)
        c_stat["user_stats"] = {u: user_stats[u] for u in cls_u_set if u in user_stats}
        c_stat["struggling"] = sorted(
            [st for st in c_stat["user_stats"].values() if st["tot"] >= 20 and st["ac_rate"] < 50],
            key=lambda x: (x["ac_rate"], -x["tot"])
        )
        stats_by_class[cls_name] = c_stat
        anomalies_by_class[cls_name] = filter_anomalies_for_class(anomalies, cls_names_and_users, name_or_user_to_class)

    comparison_summary = []
    for cls_name in classes_list:
        c_st = stats_by_class[cls_name]
        c_anom = anomalies_by_class[cls_name]
        
        anom_users = set()
        for item in c_anom.get("non_python", []): anom_users.add(item.get("student"))
        for item in c_anom.get("advanced_syntax_by_student", []): anom_users.add(item.get("student"))
        for item in c_anom.get("submission_bursts", []): anom_users.add(item.get("student"))
        for item in c_anom.get("ai_comments", []): anom_users.add(item.get("student"))
        for p_list in c_anom.get("plagiarism_groups", {}).values():
            for g in p_list:
                for st in g.get("students", []):
                    if st in class_students_map.get(cls_name, []) or st in [user_stats.get(u, {}).get("nick") for u in class_students_map.get(cls_name, [])]:
                        anom_users.add(st)

        prob_pass_rates = {}
        for p in all_probs:
            ac_u = c_st["prob_users_ac"].get(p, 0)
            pass_rate = round((ac_u / max(c_st["total_registered"], 1)) * 100, 1)
            prob_pass_rates[p] = pass_rate

        full_cnt = len(c_st["solved_all"])
        full_rate = round((full_cnt / max(c_st["total_registered"], 1)) * 100, 1)

        comparison_summary.append({
            "class_name": cls_name,
            "roster_count": c_st["roster_count"],
            "actual_count": c_st["total_registered"],
            "attend_rate": c_st["attend_rate"],
            "avg_solved": c_st["avg_solved"],
            "full_cnt": full_cnt,
            "full_rate": full_rate,
            "avg_subs": c_st["avg_subs"],
            "ac_rate": c_st["ac_rate"],
            "anomaly_users_cnt": len(anom_users),
            "anomaly_rate": round((len(anom_users) / max(c_st["total_registered"], 1)) * 100, 1),
            "prob_pass_rates": prob_pass_rates
        })

    cross_class_plagiarism = []
    if anomalies and "plagiarism_groups" in anomalies:
        for p, grps in anomalies["plagiarism_groups"].items():
            for g in grps:
                stus = g.get("students", [])
                classes_involved = set(name_or_user_to_class.get(st, name_or_user_to_class.get(clean_name(st), "未知")) for st in stus)
                if len(classes_involved) > 1:
                    cross_class_plagiarism.append({
                        "prob": p,
                        "prob_title": prob_titles.get(p, f"题目 {p}"),
                        "classes": list(classes_involved),
                        "students": [f"{st} ({name_or_user_to_class.get(st, '未知')})" for st in stus],
                        "similarity": g.get("similarity", 1.0)
                    })

    class_comparison = {
        "classes": classes_list,
        "summary": comparison_summary,
        "all_probs": all_probs,
        "cross_class_plagiarism": cross_class_plagiarism
    }

    return {
        "all_probs": all_probs,
        "stats_all": stats_all,
        "stats_by_class": stats_by_class,
        "anomalies_all": anomalies,
        "anomalies_by_class": anomalies_by_class,
        "class_comparison": class_comparison,
        "classes_list": classes_list,
        "has_roster": class_mapping["has_roster"]
    }

def main():
    parser = argparse.ArgumentParser(description="多班级全景教学分析 HTML 报告生成器 (Pro)")
    parser.add_argument("--rank", required=True, help="rank_users.json 路径")
    parser.add_argument("--subs", required=True, help="all_subs.json 路径")
    parser.add_argument("--anomalies", default="", help="anomalies.json 路径")
    parser.add_argument("--prob-titles-file", default="", help="prob_titles.json 路径")
    parser.add_argument("--deep-analysis", default="", help="deep_analysis.json 路径 (可选)")
    parser.add_argument("--roster", default="", help="班级名单 Excel 文件路径 (可选)")
    parser.add_argument("--mode", default="both", choices=["all", "class", "both"], help="分析模式: all(全年级), class(仅班级), both(全景二者)")
    parser.add_argument("--target-class", default="", help="仅分析指定班级 (可选)")
    parser.add_argument("--contest-name", default="OJ 竞赛教学全景分析", help="竞赛名称")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    args = parser.parse_args()

    with open(args.rank, "r", encoding="utf-8") as f:
        rank_users = json.load(f)
    with open(args.subs, "r", encoding="utf-8") as f:
        all_subs = json.load(f)

    anomalies = {}
    if args.anomalies and os.path.exists(args.anomalies):
        with open(args.anomalies, "r", encoding="utf-8") as f:
            anomalies = json.load(f)

    prob_titles = {}
    if args.prob_titles_file and os.path.exists(args.prob_titles_file):
        with open(args.prob_titles_file, "r", encoding="utf-8") as f:
            prob_titles = json.load(f)

    deep_analysis = {}
    deep_path = args.deep_analysis if args.deep_analysis else os.path.join(args.output_dir, "deep_analysis.json")
    if deep_path and os.path.exists(deep_path):
        with open(deep_path, "r", encoding="utf-8") as f:
            deep_analysis = json.load(f)

    print(f"\n[1/4] 解析班级名单与学生归属映射...")
    class_mapping = build_class_mapping(rank_users, all_subs, args.roster)
    if class_mapping["has_roster"]:
        print(f"  ✅ 成功加载班级名单，发现 {len(class_mapping['classes_list'])} 个班级分类:")
        for c in class_mapping['classes_list']:
            st_cnt = len(class_mapping['class_students_map'].get(c, []))
            print(f"     - {c}: {st_cnt} 人参赛")
        if class_mapping['unmatched_users']:
            print(f"  ⚠️ 未在名单中的参赛学员共 {len(class_mapping['unmatched_users'])} 人，已归入「未分班」")
    else:
        print("  ℹ️ 未提供班级名单，将默认按【全年级】整体维度进行分析。")

    print(f"\n[2/4] 构建多维度聚合指标（年级总览、各班级分片、横向对比矩阵）...")
    dataset = build_full_dataset(rank_users, all_subs, anomalies, deep_analysis, prob_titles, class_mapping)

    print(f"[3/4] 生成全局学生匿名代号映射字典...")
    anon_map = build_anon_map(rank_users, all_subs)

    print(f"[4/4] 渲染单页集成式全景交互 HTML 报告...")
    os.makedirs(args.output_dir, exist_ok=True)
    
    html_content = render_html(
        contest_name=args.contest_name,
        dataset=dataset,
        anon_map=anon_map,
        prob_titles=prob_titles,
        deep_analysis=deep_analysis,
        mode=args.mode,
        target_class=args.target_class
    )

    out_file = os.path.join(args.output_dir, "report.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ 全景 HTML 报告已生成: {out_file}")

    anon_path = os.path.join(args.output_dir, "student_anon_mapping.json")
    with open(anon_path, "w", encoding="utf-8") as f:
        json.dump(anon_map, f, ensure_ascii=False, indent=2)
    print(f"✅ 匿名代号索引表已保存: {anon_path}")

    if dataset["has_roster"]:
        summary_path = os.path.join(args.output_dir, "class_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(dataset["class_comparison"], f, ensure_ascii=False, indent=2)
        print(f"✅ 班级横向对比数据已保存: {summary_path}")

    print(f"\n🎉 报告生成完毕！可以在浏览器中直接双击打开查看。")

if __name__ == "__main__":
    main()
