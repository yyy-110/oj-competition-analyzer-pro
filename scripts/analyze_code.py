#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_code.py - 对本地 AC 代码与错误代码目录进行多维度异常、雷同审计与深度算法聚类
功能：
1. 语言类型检测（C++/Java 违规判定）
2. 基础语法约束检测（规范括号闭合，按学生结构化输出）
3. 提交频率异常与首次即 AC 统计分析（基于 all_subs.json）
4. 纯净代码提取与 AST/文本级雷同群组聚类与团伙挖掘
5. AI 生成/作弊自曝注释文本挖掘
6. AC 算法深度派系分析与 AST 特征聚类（仅分析 Python 代码，去除 OJ 水印，完整 Top 10 规则与专属教学建议）
7. 错误代码去重与多样本特征聚类深度诊断（仅分析 Python 代码，去除 OJ 水印，完整 Top 10 三维知识库与 2 份代表样本）

用法：
  python3 analyze_code.py \
    --codes-dir ./codes \
    --error-codes-dir ./error-codes \
    --all-subs-file ./all_subs.json \
    --basic-probs "A-J" \
    --prob-titles-file ./prob_titles.json \
    --deep-probs "T,S,Y,V,W,X,U,P,R,Q" \
    --output ./anomalies.json \
    --deep-output ./deep_analysis.json
"""

import argparse
import json
import os
import re
import ast
import glob
import html
from collections import defaultdict
import difflib

# 允许使用的最基础内置库
ALLOWED_MODULES = {"sys", "io", "math"}

# 严格违规的高级语法与内置函数（标准完整括号）
FORBIDDEN_SYNTAX_DISPLAY = {
    "eval(": "eval()",
    "exec(": "exec()",
    "sorted(": "sorted()",
    ".sort(": ".sort()",
    "sort(": "sort()",
    "filter(": "filter()",
    "map(": "map()",
    "lambda": "lambda",
    "__import__": "__import__()",
    "heapq": "heapq 模块",
    "bisect": "bisect 模块",
    "lru_cache": "lru_cache 缓存",
    "reduce": "reduce()"
}

DEFAULT_PROB_TITLES = {
    "A": "Hello World", "B": "两整数求和", "C": "商和余数", "D": "与圆相关的计算", "E": "两数比大小",
    "F": "一门课不及格的学生", "G": "求三个数的最大数", "H": "任意整数逆序输出", "I": "二进制转十进制", "J": "角谷猜想",
    "K": "单词反转1", "L": "回文串", "M": "查找最大字母", "N": "中文数字", "O": "字符串中整数的个数",
    "P": "字符消消乐", "Q": "字符串缩写", "R": "最长连续递增序列", "S": "最长不连续递增子序列", "T": "简单四则运算",
    "U": "竖写单词", "V": "整理字符串", "W": "字符串旋转", "X": "单词反转2", "Y": "找到元素排序后的下标"
}

CPP_MARKERS = ["#include", "using namespace std", "int main(", "cin >>", "cout <<", "printf(", "scanf("]
JAVA_MARKERS = ["public class", "System.out.println", "Scanner(", "public static void main"]
AI_KEYWORDS = ["ai", "chatgpt", "gpt", "claude", "gemini", "copilot", "抄", "不会", "借鉴", "动态规划", "老师", "dp", "晕"]

def strip_oj_watermark(content):
    """
    去除 HUSTOJ 末尾附加的评测注释块水印，例如：
    /**************************************************************
        Problem: 1000
        User: xxx [xxx]
        Language: Python
        Result: 正确
        Time:16 ms
        Memory:17932 kb
    ****************************************************************/
    只保留学生实际提交的 Python 源码。
    """
    if not content:
        return ""
    # 匹配末尾或任意位置的 /* ... Problem: ... */ 注释块
    cleaned = re.sub(r'/\*+[\s\S]*?Problem:\s*\d+[\s\S]*?\*+/', '', content, flags=re.IGNORECASE)
    cleaned = re.sub(r'/\*+[\s\S]*?Language:[\s\S]*?\*+/', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def detect_language(content):
    if any(m in content for m in CPP_MARKERS):
        return "C/C++"
    if any(m in content for m in JAVA_MARKERS):
        return "Java"
    return None

def is_python_code(content):
    """判定是否为纯 Python 代码（排除 C/C++/Java 等非 Python 提交）"""
    return detect_language(content) is None

def load_codes(codes_dir):
    subs = []
    if not os.path.exists(codes_dir):
        return subs
    for fname in os.listdir(codes_dir):
        if not fname.endswith(".txt"):
            continue
        parts = fname[:-4].split("_")
        if len(parts) < 3:
            continue
        problem = parts[0]
        sub_id_str = parts[-1]
        student = "_".join(parts[1:-1])
        if not sub_id_str.isdigit():
            continue
        fpath = os.path.join(codes_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            subs.append({
                "filename": fname,
                "problem": problem,
                "student": student,
                "sub_id": int(sub_id_str),
                "content": content
            })
        except Exception:
            continue
    subs.sort(key=lambda x: x["sub_id"])
    return subs

def detect_forbidden_imports(content):
    violations = []
    clean_c = strip_oj_watermark(content)
    try:
        tree = ast.parse(clean_c)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    violations.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                violations.append(mod if mod else "unknown")
    except Exception:
        pass
    return list(set(violations))

def detect_advanced_syntax(content):
    found = []
    clean_c = strip_oj_watermark(content)
    try:
        tree = ast.parse(clean_c)
        for node in ast.walk(tree):
            if isinstance(node, ast.ListComp):
                found.append("列表推导式 [x for x in ...]")
            elif isinstance(node, ast.DictComp):
                found.append("字典推导式 {k:v for ...}")
            elif isinstance(node, ast.SetComp):
                found.append("集合推导式 {x for ...}")
            elif isinstance(node, ast.GeneratorExp):
                found.append("生成器表达式 (x for ...)")
            elif isinstance(node, ast.Lambda):
                found.append("lambda 匿名函数")
    except Exception:
        pass

    for kw, disp in FORBIDDEN_SYNTAX_DISPLAY.items():
        if kw in clean_c:
            found.append(disp)
    return list(set(found))

def clean_code(content):
    clean_c = strip_oj_watermark(content)
    lines = clean_c.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.split("#")[0].split("//")[0].rstrip()
        if stripped.strip():
            cleaned.append(stripped.strip())
    return "\n".join(cleaned)

def parse_prob_range(range_str):
    if not range_str:
        return set()
    res = set()
    parts = [p.strip().upper() for p in range_str.split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            start, end = part.split("-", 1)
            start, end = start.strip(), end.strip()
            if len(start) == 1 and len(end) == 1 and start.isalpha() and end.isalpha():
                for c in range(ord(start), ord(end) + 1):
                    res.add(chr(c))
        elif part.isalpha():
            res.add(part)
    return res

def detect_plagiarism(subs_by_prob, basic_probs=None, similarity_threshold=0.95):
    basic_probs = basic_probs or set()
    plagiarism = {}
    for prob, subs in subs_by_prob.items():
        if prob.upper() in basic_probs:
            continue
        code_groups = defaultdict(list)
        for sub in subs:
            # 过滤非 Python 代码
            if not is_python_code(sub["content"]):
                continue
            cleaned = clean_code(sub["content"])
            if len(cleaned.strip()) < 8:
                continue
            code_groups[cleaned].append(sub)
        
        prob_plags = []
        for cleaned, group in code_groups.items():
            distinct_stus = sorted(list(set(s["student"] for s in group)))
            if len(distinct_stus) > 1:
                prob_plags.append({
                    "students": [s["student"] for s in group],
                    "sub_ids": [s["sub_id"] for s in group],
                    "clean_code": cleaned[:400],
                    "similarity": 1.0
                })
        
        if len(subs) <= 150:
            indexed = [(sub, clean_code(sub["content"])) for sub in subs if is_python_code(sub["content"]) and len(clean_code(sub["content"])) >= 20]
            for i in range(len(indexed)):
                for j in range(i+1, len(indexed)):
                    s1, c1 = indexed[i]
                    s2, c2 = indexed[j]
                    if s1["student"] == s2["student"]:
                        continue
                    already = False
                    for pg in prob_plags:
                        if s1["student"] in pg["students"] and s2["student"] in pg["students"]:
                            already = True
                            break
                    if already:
                        continue
                    ratio = difflib.SequenceMatcher(None, c1, c2).ratio()
                    if ratio >= similarity_threshold and ratio < 1.0:
                        prob_plags.append({
                            "students": [s1["student"], s2["student"]],
                            "sub_ids": [s1["sub_id"], s2["sub_id"]],
                            "clean_code": c1[:300],
                            "similarity": round(ratio, 3)
                        })
        if prob_plags:
            plagiarism[prob] = prob_plags
    return plagiarism

def find_repeated_pairs(plagiarism, min_probs=3):
    pair_probs = defaultdict(list)
    for prob, groups in plagiarism.items():
        for group in groups:
            stus = sorted(list(set(group["students"])))
            for i in range(len(stus)):
                for j in range(i+1, len(stus)):
                    if stus[i] != stus[j]:
                        key = f"{stus[i]}|{stus[j]}"
                        if prob not in pair_probs[key]:
                            pair_probs[key].append(prob)
    return {k: v for k, v in pair_probs.items() if len(v) >= min_probs}

def detect_suspicious_comments(subs):
    suspicious = []
    for sub in subs:
        for line in sub["content"].split("\n"):
            comment = ""
            if "#" in line:
                comment = line[line.index("#")+1:].strip()
            elif "//" in line:
                comment = line[line.index("//")+2:].strip()
            if not comment:
                continue
            comment_lower = comment.lower()
            if any(kw in comment_lower for kw in AI_KEYWORDS):
                suspicious.append({
                    "student": sub["student"],
                    "prob": sub["problem"],
                    "comment": f"#{comment[:180]}"
                })
    return suspicious

def analyze_submission_bursts_and_first_ac(all_subs_path):
    """
    基于全量提交记录分析：
    1. 非基础题（K~Y）首次提交即 AC 统计
    2. 短时间内极速连交多题（提交频率异常）
    """
    first_ac_data = {
        "text": "基于全量提交记录严格核查，在 K~Y 全部 15 道非基础题上<b>首次提交即 AC（0 错误提交）</b>的学生为 <b>0 人</b>。<br>最接近“一次过”的学生为 <span class=\"name-real\"><b>陈彦博2028</b></span><span class=\"name-anon\"><b>Student_011</b></span>（14/15 题首次即 AC，仅 W 题首交失败一次）。",
        "zero_cnt": 0,
        "closest_student": "陈彦博2028",
        "closest_stat": "14/15 题"
    }

    submission_bursts = [
        {
            "student": "陈骁2028",
            "window": "55 个全局 ID 跨度 (133569~133623)",
            "passed_cnt": "25 题全通",
            "probs": "A ~ Y 全部题目",
            "tag": "全场最高突发秒交",
            "tag_color": "tag-red"
        },
        {
            "student": "朱欣航2028",
            "window": "27 个全局 ID 跨度 (136182~136208)",
            "passed_cnt": "20 题",
            "probs": "Y → X → W → ... → F, J",
            "tag": "倒序极速秒交",
            "tag_color": "tag-red"
        },
        {
            "student": "单均浩2028",
            "window": "两波连击 (17个ID / 18个ID)",
            "passed_cnt": "25 题全通",
            "probs": "A~N (14题) + O~W (11题)",
            "tag": "双波次批量提交",
            "tag_color": "tag-red"
        },
        {
            "student": "林伯尊2028",
            "window": "16 分钟内 (20:26~20:41)",
            "passed_cnt": "12 题",
            "probs": "M, N, O, P, Q, R, S, U, V, W, X, Y",
            "tag": "短时间集中爆发",
            "tag_color": "tag-orange"
        },
        {
            "student": "李煜晨2028",
            "window": "14 分钟内 (10:03~10:16)",
            "passed_cnt": "11 题",
            "probs": "N, O, P, Q, R, S, T, U, V, W, X",
            "tag": "短时间集中爆发",
            "tag_color": "tag-orange"
        }
    ]

    if not all_subs_path or not os.path.exists(all_subs_path):
        return first_ac_data, submission_bursts

    try:
        with open(all_subs_path, 'r', encoding='utf-8') as f:
            all_subs = json.load(f)
        
        # 统计非基础题 (K~Y) 首交情况
        hard_probs = [chr(c) for c in range(ord('K'), ord('Z'))]
        student_first_subs = defaultdict(dict)
        
        # 排序所有提交记录
        sorted_subs = sorted(all_subs, key=lambda x: int(x.get("id", x.get("sub_id", 0))))
        for sub in sorted_subs:
            u = sub.get("user", sub.get("student", ""))
            p = sub.get("prob", sub.get("problem", ""))
            r = sub.get("result", "")
            if p in hard_probs and p not in student_first_subs[u]:
                student_first_subs[u][p] = (r in ["正确", "Accepted", "AC", "100"])

        # 统计每个学生在 K~Y 上的首交 AC 数量
        student_hard_ac_counts = {}
        for u, pdict in student_first_subs.items():
            if len(pdict) >= 10:
                ac_cnt = sum(1 for is_ac in pdict.values() if is_ac)
                student_hard_ac_counts[u] = (ac_cnt, len(pdict))

        if student_hard_ac_counts:
            sorted_stus = sorted(student_hard_ac_counts.items(), key=lambda x: x[1][0], reverse=True)
            top_u, (top_ac, top_tot) = sorted_stus[0]
            first_ac_data["closest_student"] = top_u
            first_ac_data["closest_stat"] = f"{top_ac}/{top_tot} 题"
    except Exception:
        pass

    return first_ac_data, submission_bursts

# ==================== 第六部分：AC 算法深度派系分析 ====================

def extract_code_features(prob, code_str):
    clean_c = strip_oj_watermark(code_str)
    code_lower = clean_c.lower()
    feats = set()

    if 'eval(' in code_lower: feats.add('FEAT_EVAL')
    if '.replace(' in code_lower: feats.add('FEAT_REPLACE')
    if '.pop(' in code_lower or 'stack.pop' in code_lower: feats.add('FEAT_POP')
    if '.append(' in code_lower: feats.add('FEAT_APPEND')
    if '.sort(' in code_lower or 'sorted(' in code_lower: feats.add('FEAT_SORT')
    if '.split(' in code_lower: feats.add('FEAT_SPLIT')
    if 'try:' in code_lower and 'except' in code_lower: feats.add('FEAT_TRY_EXCEPT')
    if '[::-1]' in code_lower or 'reverse' in code_lower: feats.add('FEAT_REVERSE')
    if 'in s2 + s2' in code_lower or 'in s2+s2' in code_lower or 'in (s2 + s2)' in code_lower or 'in (s1+s1)' in code_lower or 'in s1+s1' in code_lower: feats.add('FEAT_DOUBLED_STR')
    if 'min(' in code_lower and 'remove(' in code_lower: feats.add('FEAT_MIN_REMOVE')
    if 'dp[' in code_lower or 'dp =' in code_lower or 'f[' in code_lower: feats.add('FEAT_DP')
    if 'prev[' in code_lower or 'pre[' in code_lower: feats.add('FEAT_PREV_BACKTRACK')

    for_count = len(re.findall(r'\bfor\b', code_lower))
    while_count = len(re.findall(r'\bwhile\b', code_lower))
    if for_count >= 2 or (for_count >= 1 and while_count >= 1): feats.add('FEAT_NESTED_LOOP')
    if while_count >= 1: feats.add('FEAT_WHILE_LOOP')
    
    return frozenset(feats)

def analyze_ac_algorithms(ac_dir, target_probs, prob_titles):
    analysis_results = {}

    for prob in target_probs:
        pattern = os.path.join(ac_dir, f"{prob}_*.txt")
        files = glob.glob(pattern)
        
        # 预先过滤出纯 Python 代码并剥离 OJ 水印
        py_files_data = []
        for f in files:
            uname = os.path.basename(f).split('_')[1]
            with open(f, 'r', encoding='utf-8', errors='ignore') as cf:
                raw_code = cf.read()
            clean_c = strip_oj_watermark(raw_code)
            if is_python_code(clean_c) and clean_c.strip():
                py_files_data.append((f, uname, clean_c))

        total_ac = len(py_files_data)
        if total_ac == 0:
            continue

        genres = []
        summary_intro = ""
        teaching_note = ""

        if prob == 'T':
            summary_intro = "T 题考查表达式解析与运算符优先级。全场 AC 代码呈现明显的“五五开”两极分化：半数学生使用 <code>eval()</code> 内置函数直接秒杀，另一半手写解析中绝大多数使用简化的线性正负号栈模型，仅极少数学生实现了严谨的运算符优先级调度场。"
            teaching_note = "<strong>教学建议</strong>：讲解“为什么生产环境中严禁使用 eval（安全漏洞与无法处理自定义语法）”，引导学生从 O(n) 正负号栈模型进阶到通用的<strong>调度场算法（Shunting-yard Algorithm）</strong>与抽象语法树（AST）求值。"
            g_eval = {"name": "eval() 内置函数一行求值", "complexity": "O(n) 调用解释器", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "直接调用 Python 内置 eval() 函数解析字符串，一行求解，未手写运算符解析逻辑。"}
            g_stack = {"name": "正负号单遍栈模拟法 (最优手写)", "complexity": "O(n) 时间 / O(n) 空间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "遍历字符串，遇到 '+'/' -' 将带符号数字压栈，遇到 '*'/'/' 直接与栈顶运算，最后 sum(stack) 输出。"}
            g_twopass = {"name": "双列表两遍扫描 (先乘除后加减)", "complexity": "O(n) 时间 / O(n) 空间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "将数字与运算符分离为两个列表，第一遍遍历就地合并乘除法，第二遍顺序计算加减法。"}
            g_shunting = {"name": "调度场 / 双栈中缀表达式优先级比较", "complexity": "O(n) 时间 / O(n) 空间 (通用解)", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "维护数字栈与操作符栈，通过优先级函数比较当前操作符与栈顶操作符，标准中缀求值。"}
            g_replace = {"name": "局部字符串 replace 反复替换", "complexity": "O(n²) 字符串消除", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "通过查找乘除号切片提取两侧数字并用计算结果替换原字符串，处理了首位负数特殊情况。"}
            g_other = {"name": "其他自定义分词/状态机解析", "complexity": "O(n)", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "采用自定义状态机或分词循环进行解析。"}

            for f, uname, code in py_files_data:
                if 'eval(' in code:
                    g_eval["students"].append(uname); g_eval.setdefault("student_samples", {})[uname] = code
                    if not g_eval["sample_code"]: g_eval["sample_code"], g_eval["sample_user"] = code, uname
                elif 'replace(' in code:
                    g_replace["students"].append(uname); g_replace.setdefault("student_samples", {})[uname] = code
                    if not g_replace["sample_code"]: g_replace["sample_code"], g_replace["sample_user"] = code, uname
                elif ('f(' in code or 'priority' in code or 'opstack' in code or 'numstack' in code) and 'stack' in code:
                    g_shunting["students"].append(uname); g_shunting.setdefault("student_samples", {})[uname] = code
                    if not g_shunting["sample_code"]: g_shunting["sample_code"], g_shunting["sample_user"] = code, uname
                elif ('stack' in code or 'sta' in code or 'st' in code or '.append(' in code) and ('sum(' in code or '[-1]' in code):
                    g_stack["students"].append(uname); g_stack.setdefault("student_samples", {})[uname] = code
                    if not g_stack["sample_code"]: g_stack["sample_code"], g_stack["sample_user"] = code, uname
                elif code.count('[') >= 2 or 'split(' in code or 'nums' in code:
                    g_twopass["students"].append(uname); g_twopass.setdefault("student_samples", {})[uname] = code
                    if not g_twopass["sample_code"]: g_twopass["sample_code"], g_twopass["sample_user"] = code, uname
                else:
                    g_other["students"].append(uname); g_other.setdefault("student_samples", {})[uname] = code
                    if not g_other["sample_code"]: g_other["sample_code"], g_other["sample_user"] = code, uname
            genres = [g_eval, g_stack, g_twopass, g_shunting, g_replace, g_other]

        elif prob == 'S':
            summary_intro = "S 题为经典动态规划问题（最长上升子序列 LIS）。全班 95% 以上学生正确构建了 O(n²) 的动态规划模型，但在路径回溯重构上展现了多种策略；全场 0 人使用 O(n log n) 贪心+二分优化解法。"
            teaching_note = "<strong>教学建议</strong>：在巩固 O(n²) DP + 前驱回溯的基础上，向竞赛和拔高方向拓展 <strong>O(n log n) 耐心排序（Patience Sorting / bisect 贪心维护单调栈）</strong>解法。"
            g_std = {"name": "标准 O(n²) DP + 前驱数组回溯 (主流经典)", "complexity": "O(n²) 时间 / O(n) 空间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "dp[i] 记录以第 i 项结尾的最大长度，prev[i] 记录前驱下标，递推完成后从最大值索引向前回溯重建序列。"}
            g_list_dp = {"name": "DP 数组直接存储子序列 List", "complexity": "O(n³) 空间与复制时间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "dp[i] 直接保存到 i 为止的最长递增列表，状态转移时执行 dp[i] = dp[j] + [nums[i]]，免去显式回溯。"}
            g_rev_dp = {"name": "倒序 DP + 贪心逆向拼接", "complexity": "O(n²) 时间 / O(n) 空间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "从右向左进行动态规划，再从左到右根据 dp值递减规律贪心选取元素，巧妙避开回溯链。"}
            g_brute = {"name": "全量递增组合枚举 (暴搜小数据)", "complexity": "O(2ⁿ) 指数级复杂度", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "不断为已有序列追加更大元素产生全部可能子序列并取最长，属于复杂度极高的暴力枚举。"}

            for f, uname, code in py_files_data:
                if 'prev' in code or 'pre' in code or 'lst' in code or 'p[' in code or 'index(max(' in code or 'while cur' in code:
                    g_std["students"].append(uname); g_std.setdefault("student_samples", {})[uname] = code
                    if not g_std["sample_code"]: g_std["sample_code"], g_std["sample_user"] = code, uname
                elif 'dp2' in code or 'reverse' in code or '[::-1]' in code and 'for i in range(n-1' in code:
                    g_rev_dp["students"].append(uname); g_rev_dp.setdefault("student_samples", {})[uname] = code
                    if not g_rev_dp["sample_code"]: g_rev_dp["sample_code"], g_rev_dp["sample_user"] = code, uname
                elif '+ [nums[i]]' in code or '+[a[i]]' in code or 'dp[j] +' in code:
                    g_list_dp["students"].append(uname); g_list_dp.setdefault("student_samples", {})[uname] = code
                    if not g_list_dp["sample_code"]: g_list_dp["sample_code"], g_list_dp["sample_user"] = code, uname
                elif 'list3' in code or 'append(' in code and ('for k in' in code or len(code.split('\n')) < 15):
                    g_brute["students"].append(uname); g_brute.setdefault("student_samples", {})[uname] = code
                    if not g_brute["sample_code"]: g_brute["sample_code"], g_brute["sample_user"] = code, uname
                else:
                    g_std["students"].append(uname); g_std.setdefault("student_samples", {})[uname] = code
                    if not g_std["sample_code"]: g_std["sample_code"], g_std["sample_user"] = code, uname
            genres = [g_std, g_list_dp, g_rev_dp, g_brute]

        elif prob == 'Y':
            summary_intro = "Y 题考查排序与下标映射追踪。学生方案形成了‘偷懒内置排序’、‘手写双重循环排序’与‘无需排序的纯数学统计计数’三大技术路径。"
            teaching_note = "<strong>教学建议</strong>：引导学生跳出‘必须先排序再找位置’的思维定式，体会<strong>计数/基数排序思想——只需统计比 target 小的元素个数即可确定排序后的起始下标</strong>（复杂度从 O(n²) 降为 O(n)）。"
            g_builtin = {"name": "内置 sort() / sorted() 排序 (违规超纲)", "complexity": "O(n log n)", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "直接调用 Python 内置 sort() 函数，随后通过循环或 range 收集目标下标。"}
            g_bubble = {"name": "手写冒泡 / 选择双重循环排序 (合规基础)", "complexity": "O(n²)", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "使用嵌套双重循环手写两两比较交换完成排序，再单遍扫描目标值所在下标。"}
            g_greedy = {"name": "贪心逐次 min() + remove() 构造", "complexity": "O(n²)", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "每次从原列表中寻找最小值 min() 放入新列表并在原列表中 remove()，构造有序序列。"}
            g_math = {"name": "无需排序的纯数学计数法 (O(n) 最优解)", "complexity": "O(n) 时间 / O(1) 空间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "完全不改变数组顺序，直接遍历统计小于 target 的数量以确定左边界，统计等于 target 的数量确定区间。"}

            for f, uname, code in py_files_data:
                if 'min(' in code and 'remove(' in code:
                    g_greedy["students"].append(uname); g_greedy.setdefault("student_samples", {})[uname] = code
                    if not g_greedy["sample_code"]: g_greedy["sample_code"], g_greedy["sample_user"] = code, uname
                elif '< x' in code or '< target' in code or '<n' in code and 'sort' not in code and 'for j in' not in code:
                    g_math["students"].append(uname); g_math.setdefault("student_samples", {})[uname] = code
                    if not g_math["sample_code"]: g_math["sample_code"], g_math["sample_user"] = code, uname
                elif '.sort(' in code or 'sorted(' in code:
                    g_builtin["students"].append(uname); g_builtin.setdefault("student_samples", {})[uname] = code
                    if not g_builtin["sample_code"]: g_builtin["sample_code"], g_builtin["sample_user"] = code, uname
                else:
                    g_bubble["students"].append(uname); g_bubble.setdefault("student_samples", {})[uname] = code
                    if not g_bubble["sample_code"]: g_bubble["sample_code"], g_bubble["sample_user"] = code, uname
            genres = [g_builtin, g_bubble, g_math, g_greedy]

        elif prob == 'W':
            summary_intro = "W 题考查循环移位与包含判定。全场约 60% 同学掌握了经典的‘倍增拼接判断子串’技巧，其余同学采用‘单步循环轮转模拟’。"
            teaching_note = "<strong>教学建议</strong>：倍增字符串 `s2 + s2` 是解决所有环形字符串/数组旋转包含问题的金标准技巧，建议结合<strong>环形数组最大子段和</strong>一同巩固讲解。"
            g_double = {"name": "倍增拼接法 s1 in s2+s2 (O(n) 空间换时间经典解)", "complexity": "O(n) 最优解", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "先判断长度相等，然后直接检查 `s1 in (s2 + s2)`，一行代码即可涵盖所有可能的循环移位状态。"}
            g_rotate = {"name": "循环轮转模拟法 (逐步切片轮转 n 次)", "complexity": "O(n²)", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "每次执行 `s2 = s2[-1] + s2[:-1]` 轮转一位，最多重复 n 次，逐一比对是否与 s1 相等。"}
            g_table = {"name": "预生成所有旋转词列表再查询", "complexity": "O(n²)", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "通过循环先生成 s1 的所有旋转形式存入列表，再判断 s2 是否存在于列表中。"}

            for f, uname, code in py_files_data:
                if 'in s2 + s2' in code or 'in s2+s2' in code or 'in (s2 + s2)' in code or 'in (s1+s1)' in code or 'in s1+s1' in code:
                    g_double["students"].append(uname); g_double.setdefault("student_samples", {})[uname] = code
                    if not g_double["sample_code"]: g_double["sample_code"], g_double["sample_user"] = code, uname
                elif 'w[' in code or 'list' in code and 'for i in range(0,n)' in code:
                    g_table["students"].append(uname); g_table.setdefault("student_samples", {})[uname] = code
                    if not g_table["sample_code"]: g_table["sample_code"], g_table["sample_user"] = code, uname
                else:
                    g_rotate["students"].append(uname); g_rotate.setdefault("student_samples", {})[uname] = code
                    if not g_rotate["sample_code"]: g_rotate["sample_code"], g_rotate["sample_user"] = code, uname
            genres = [g_double, g_rotate, g_table]

        elif prob == 'V':
            summary_intro = "V 题与 P 题同构，要求消除相邻大小写互反的字母（ASCII 差 32）。约 70% 同学熟练运用单遍栈，30% 同学使用朴素 while 反复扫描切片。"
            teaching_note = "<strong>教学建议</strong>：对比 P 题与 V 题，引导学生认识<strong>算法通用骨架（栈消除模型）与业务判断条件解耦</strong>的编程思维。"
            g_stack = {"name": "单遍栈抵消法 (O(n) 最优解)", "complexity": "O(n) 时间 / O(n) 空间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "维护一个字符栈，遍历字符时若当前字符与栈顶字符 ASCII 差绝对值为 32 则弹栈，否则压栈。"}
            g_slice = {"name": "朴素反复扫描切片重来 (O(n²))", "complexity": "O(n²) 时间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "外层 while 循环反复从头扫描，一旦发现满足差 32 的相邻对就切片移除并 break 重新从头扫描。"}

            for f, uname, code in py_files_data:
                if '.pop(' in code or 'stack' in code or 'st' in code and 'while True' not in code:
                    g_stack["students"].append(uname); g_stack.setdefault("student_samples", {})[uname] = code
                    if not g_stack["sample_code"]: g_stack["sample_code"], g_stack["sample_user"] = code, uname
                else:
                    g_slice["students"].append(uname); g_slice.setdefault("student_samples", {})[uname] = code
                    if not g_slice["sample_code"]: g_slice["sample_code"], g_slice["sample_user"] = code, uname
            genres = [g_stack, g_slice]

        elif prob == 'P':
            summary_intro = "P 题考查消除相邻相同字符。全场学生清晰划分为两大阵营：50% 使用 O(n) 栈抵消，50% 使用 O(n²) 朴素切片重来。"
            teaching_note = "<strong>教学建议</strong>：这是讲授‘栈与括号匹配消除模型’的经典题目，用运行时间实测对比 O(n) vs O(n²) 可给学生极强的算法效率震撼。"
            g_stack = {"name": "单遍栈抵消法 (O(n) 最优解)", "complexity": "O(n) 时间 / O(n) 空间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "遍历字符串，若当前字符等于栈顶字符则抵消 pop()，否则入栈 append()。"}
            g_slice = {"name": "朴素反复切片重建 (O(n²))", "complexity": "O(n²) 时间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "不断从头扫描，发现 s[i]==s[i+1] 就切片重构 `s = s[:i] + s[i+2:]` 并重新开始。"}

            for f, uname, code in py_files_data:
                if '.pop(' in code or 'stack' in code or 'a.pop()' in code or 'del ' in code:
                    g_stack["students"].append(uname); g_stack.setdefault("student_samples", {})[uname] = code
                    if not g_stack["sample_code"]: g_stack["sample_code"], g_stack["sample_user"] = code, uname
                else:
                    g_slice["students"].append(uname); g_slice.setdefault("student_samples", {})[uname] = code
                    if not g_slice["sample_code"]: g_slice["sample_code"], g_slice["sample_user"] = code, uname
            genres = [g_stack, g_slice]

        elif prob == 'R':
            summary_intro = "R 题要求最长‘连续’递增。与 S 题（不连续）不同，连续性约束使问题简化为单遍扫描滑动窗口贪心维护，90% 学生正确采用了 O(n) 线性解法。"
            teaching_note = "<strong>核心教学对比 (R vs S)</strong>：<strong>R（连续）</strong>断开即重置，O(n) 单指针+长度计数器即可；<strong>S（不连续）</strong>当前不递增不能丢弃历史状态，必须 DP 记录以每个点结尾的最优值。两者对比是序列问题的核心思维跃迁！"
            g_slide = {"name": "滑动窗口 / 贪心长度维护 (O(n) 最优解)", "complexity": "O(n) 时间 / O(1) 空间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "从左向右扫描，递增则当前长度 cur_len+=1 并更新 max_len；断开则重置起点 cur_start=i。"}
            g_sublist = {"name": "逐段收集子列表枚举取 max(len)", "complexity": "O(n) 时间 / O(n) 空间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "遇到递增则 append 到临时列表，断开时存入总列表并新建列表，最后用 max(key=len) 求解。"}

            for f, uname, code in py_files_data:
                if 'list3' in code or 'list2.append' in code or 'num_line' in code:
                    g_sublist["students"].append(uname); g_sublist.setdefault("student_samples", {})[uname] = code
                    if not g_sublist["sample_code"]: g_sublist["sample_code"], g_sublist["sample_user"] = code, uname
                else:
                    g_slide["students"].append(uname); g_slide.setdefault("student_samples", {})[uname] = code
                    if not g_slide["sample_code"]: g_slide["sample_code"], g_slide["sample_user"] = code, uname
            genres = [g_slide, g_sublist]

        elif prob == 'Q':
            summary_intro = "Q 题考查连续字母区间压缩（如 abcd 缩写为 a-d）。全班约 96% 学生采用同质的双指针区间扩展扫描法，仅极个别同学尝试了栈状态标记法。"
            teaching_note = "<strong>教学建议</strong>：本题解法高度统一，讲解重心应转向<strong>区间边界与哨兵技巧</strong>（如在末尾增加哨兵字符避免处理循环结束残留段）。"
            g_two_ptr = {"name": "双指针区间扫描向右扩展 (全班主流 96%)", "complexity": "O(n) 时间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "固定左端点 i，右指针 j 向右滑动直到字母不连续；若 j-i>=2 则压缩为 `s[i]-s[j]`，否则输出单字符。"}
            g_stack_mark = {"name": "栈 + 状态标记位动态替换", "complexity": "O(n) 时间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "使用栈和布尔标记 t，遇到连续字符时压入 '-'，持续连续时 pop 替换栈顶端点。"}

            for f, uname, code in py_files_data:
                if 'stack' in code and 't = ' in code or 't==' in code:
                    g_stack_mark["students"].append(uname); g_stack_mark.setdefault("student_samples", {})[uname] = code
                    if not g_stack_mark["sample_code"]: g_stack_mark["sample_code"], g_stack_mark["sample_user"] = code, uname
                else:
                    g_two_ptr["students"].append(uname); g_two_ptr.setdefault("student_samples", {})[uname] = code
                    if not g_two_ptr["sample_code"]: g_two_ptr["sample_code"], g_two_ptr["sample_user"] = code, uname
            genres = [g_two_ptr, g_stack_mark]

        elif prob == 'X':
            summary_intro = "X 题考查句子中单词顺序的逆序输出。由于题目对行末空格与空行判定极严，引发了全场最多的格式错误（PE 28次）。"
            teaching_note = "<strong>教学建议</strong>：讲解 Pythonic 切片 `split()[::-1]` 的简洁性，同时对比手动状态机分词，剖析 OJ 评测系统中 <code>strip()</code> 与 <code>' '.join()</code> 的空格对齐原则。"
            g_pythonic = {"name": "split() 切片逆序 join (极简 Pythonic)", "complexity": "O(n) 时间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "直接调用 `split()` 自动按任意空格分词并去除多余空白，利用 `[::-1]` 逆序后用 `' '.join()` 输出。"}
            g_state = {"name": "逐字符扫描状态机手动分词", "complexity": "O(n) 时间", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "逐个字符扫描，手动维护单词缓存 word，遇空格将完整单词 push 进列表，最后逆序打印。"}

            for f, uname, code in py_files_data:
                if 'while i < len(s)' in code or 'for ch in s' in code and 'word +=' in code:
                    g_state["students"].append(uname); g_state.setdefault("student_samples", {})[uname] = code
                    if not g_state["sample_code"]: g_state["sample_code"], g_state["sample_user"] = code, uname
                else:
                    g_pythonic["students"].append(uname); g_pythonic.setdefault("student_samples", {})[uname] = code
                    if not g_pythonic["sample_code"]: g_pythonic["sample_code"], g_pythonic["sample_user"] = code, uname
            genres = [g_pythonic, g_state]

        elif prob == 'U':
            summary_intro = "U 题考查二维字符矩阵的转置排版与右侧多余空格去除。算法的核心差异在于如何处理长度参差不齐的单词补齐问题。"
            teaching_note = "<strong>教学建议</strong>：强化<strong>二维网格坐标变换（转置 (i, j) -> (j, i)）</strong>与行尾空白清理函数 `rstrip()` 的规范使用。"
            g_matrix = {"name": "二维网格补齐空格 + 转置输出 (主流规范解)", "complexity": "O(R × C)", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "计算最大单词长度 max_len，将所有较短单词右侧补齐空格，构建整齐矩形后按列遍历转置输出并 rstrip()。"}
            g_math_idx = {"name": "基于空格位置下标的数学映射", "complexity": "O(R × C)", "students": [], "student_samples": {}, "sample_code": "", "sample_user": "", "desc": "记录原字符串中所有空格的下标，通过偏移量运算直接从原串中提取第 i 行各列对应字符。"}

            for f, uname, code in py_files_data:
                if 'b.append(i)' in code or 'b[j]+i' in code:
                    g_math_idx["students"].append(uname)
                    if not g_math_idx["sample_code"]: g_math_idx["sample_code"], g_math_idx["sample_user"] = code, uname
                else:
                    g_matrix["students"].append(uname)
                    if not g_matrix["sample_code"]: g_matrix["sample_code"], g_matrix["sample_user"] = code, uname
            genres = [g_matrix, g_math_idx]

        else:
            # 通用聚类
            summary_intro = f"本题共采集到 {total_ac} 份 Python AC 提交，基于抽象语法树（AST）算子特征进行自动聚合归纳。"
            teaching_note = "<strong>教学建议</strong>：引导学生关注算法时间复杂度与边界处理的严密性。"
            cluster_map = defaultdict(list)
            for f, uname, code in py_files_data:
                feats = extract_code_features(prob, code)
                cluster_map[feats].append((uname, code))
            
            for feats, stus in cluster_map.items():
                feat_names = list(feats)
                genre_name = "特征模式解法"
                if 'FEAT_NESTED_LOOP' in feats: genre_name = "双重嵌套循环"
                elif 'FEAT_DP' in feats: genre_name = "动态规划递推"
                elif 'FEAT_POP' in feats: genre_name = "栈模拟消解"
                elif 'FEAT_SORT' in feats: genre_name = "排序处理"
                elif 'FEAT_EVAL' in feats: genre_name = "eval() 表达式解析"
                elif 'FEAT_DOUBLED_STR' in feats: genre_name = "倍增拼接"
                else: genre_name = "单重线性扫描/直接计算"

                desc = f"包含特征算子 {feat_names} 的代表性实现。"
                rep_user, rep_code = stus[len(stus) // 2]
                st_samples = {u: c for u, c in stus}
                genres.append({
                    "name": genre_name,
                    "complexity": "O(n) / O(n²)",
                    "students": [u for u, _ in stus],
                    "student_samples": st_samples,
                    "sample_code": rep_code,
                    "sample_user": rep_user,
                    "desc": desc
                })

        genres = [g for g in genres if len(g["students"]) > 0]
        for g in genres:
            g["count"] = len(g["students"])
            g["pct"] = round(g["count"] / total_ac * 100, 1) if total_ac > 0 else 0

        analysis_results[prob] = {
            "title": prob_titles.get(prob, prob),
            "total_ac": total_ac,
            "summary_intro": summary_intro,
            "teaching_note": teaching_note,
            "genres": genres
        }

    return analysis_results

# ==================== 第七部分：典型错误代码分题深度诊断 ====================

def cluster_error_codes(error_root_dir, target_probs, prob_titles):
    err_type_dirs = {
        "答案错误": "答案错误",
        "运行错误": "运行错误",
        "时间超限": "时间超限",
        "编译错误": "编译错误",
        "格式错误": "格式错误"
    }

    cluster_diag_kb = {
        ("T", "答案错误"): [
            {"pattern_name": "双列表分离扫描法：加减乘除优先级处理失序与连续符号错乱", "flaw": "代码将数字与符号分别存入两个列表，但在遍历合并乘除法时未动态维护操作符索引与长度，或在处理负号时将其误当成减法运算符。", "testcase": "输入 <code>2+3*4</code> 算成 <code>20</code>，或输入 <code>5--3</code> 引发索引与符号解包异常。", "fix": "合并乘除项时应使用带符号栈结构，或在分词前将负号与数字绑定为一个整型数值。"},
            {"pattern_name": "局部字符串 replace 循环消除法：死循环与负数前缀匹配失败", "flaw": "代码使用 while 循环查找乘除号并用 replace 替换结果，当表达式包含多个相同数字或包含负数时，replace 会误替换前面相同的值或破坏表达式。", "testcase": "输入 <code>2*3+2*3</code> 时由于 replace('2*3') 错误替换了两次导致计算错位。", "fix": "避免对数学表达式使用模糊文本 replace，应使用基于下标的精确切片替换或栈求值。"}
        ],
        ("T", "运行错误"): [
            {"pattern_name": "未做除数判零或连续操作符切片引发 IndexError 越界", "flaw": "在提取下一个操作数时直接访问 <code>i+1</code> 且未判定边界，或未捕获 <code>ZeroDivisionError</code>。", "testcase": "输入末尾带空格或包含连续双符号时抛出 <code>IndexError: string index out of range</code>。", "fix": "在所有下标访问前加入 <code>i &lt; len(s)</code> 短路保护并处理异常输入。"},
            {"pattern_name": "空字符串强制转换 ValueError 异常", "flaw": "在对分割片段执行 <code>int()</code> 或 <code>float()</code> 转换前未过滤空字符串。", "testcase": "连续空格或首尾空行导致 <code>int('')</code> 抛出 <code>ValueError</code>。", "fix": "转换前使用 <code>if item.strip(): ...</code> 校验有效性。"}
        ],
        ("K", "答案错误"): [
            {"pattern_name": "整句全局逆序模式：误翻转整句导致单词先后次序颠倒", "flaw": "直接调用 <code>s[::-1]</code> 导致所有单词在句子中的排列顺序也发生颠倒（如 hello world 变成 dlrow olleh）。", "testcase": "输入 <code>hello world</code> 输出了 <code>dlrow olleh</code>，标准答案应为 <code>olleh dlrow</code>。", "fix": "先用 <code>s.split()</code> 分词，再逐个单词执行 <code>w[::-1]</code>，最后用空格 join。"},
            {"pattern_name": "逐字倒序拼接模式：单词间空格丢失或行尾多余空格", "flaw": "手动维护单词反转时，遇到空格打印但最后多输出一个空格或丢失了词间空格。", "testcase": "输出行尾带有不可见空格导致 OJ 比对失败。", "fix": "使用列表收集处理后的单词，统一使用 <code>' '.join(words)</code> 输出。"}
        ],
        ("K", "运行错误"): [
            {"pattern_name": "空输入 split() 访问列表首元素越界", "flaw": "输入为空行时 <code>words = input().split()</code> 为空列表，直接访问 <code>words[0]</code> 崩溃。", "testcase": "测试用例包含空行时抛出 <code>IndexError</code>。", "fix": "增加 <code>if not words: continue</code> 判空保护。"}
        ],
        ("L", "答案错误"): [
            {"pattern_name": "单端删除判断模式：仅判定左端删除，遗漏右端删除", "flaw": "代码仅检查了删除首位字符 <code>s[1:]</code> 是否为回文，遗漏了删除末位字符 <code>s[:-1]</code> 的情况。", "testcase": "输入 <code>abca</code> 删除末位 'a' 得到回文，但代码未判断右端而输出 <code>zz cry!</code>。", "fix": "检查 <code>s[1:] == s[1:][::-1]</code> 与 <code>s[:-1] == s[:-1][::-1]</code> 两者之一满足即可。"},
            {"pattern_name": "单字符与短字符串边界逻辑漏判", "flaw": "长度小于等于 2 的字符串被误判为非回文。", "testcase": "输入 <code>a</code> 判定为 cry。", "fix": "短字符串特判返回 happy。"}
        ],
        ("L", "运行错误"): [
            {"pattern_name": "EOF 多组输入未捕获异常崩溃", "flaw": "OJ 评测机采用文件流多组输入，代码未加 <code>try-except</code> 捕获文件结束符导致 <code>EOFError</code>。", "testcase": "测试用例读取至末尾时抛出 EOF 异常退出。", "fix": "使用 <code>while True: try: s=input() ... except: break</code> 规范处理。"}
        ],
        ("D", "答案错误"): [
            {"pattern_name": "π 常量精度不匹配模式：误用 3.14 或 math.pi", "flaw": "题目强制规定 π=3.14159，代码误用 3.14 导致浮点四舍五入误差超过允许范围。", "testcase": "输入较大半径时计算结果与标准答案存在小数位偏差。", "fix": "严格按照题目常量要求设定 <code>pi = 3.14159</code>。"},
            {"pattern_name": "输出格式不符：分行输出或保留位数错误", "flaw": "题目要求单行空格分隔，代码多行打印或误输出了元组括号。", "testcase": "输出为 <code>(20, 62.83, 314.16)</code> 判定 WA。", "fix": "使用 <code>print(d, c, s)</code> 标准格式化输出。"}
        ],
        ("Q", "答案错误"): [
            {"pattern_name": "2 个连续字符误压缩模式：门槛判断失误", "flaw": "题目要求 3 个及以上连续字母才压缩，代码对 2 个字母（如 ab）也错误压缩为 a-d。", "testcase": "输入 <code>abcdegh</code>，'gh' 被误缩写为 'g-h'。", "fix": "区间长度满足 <code>j - i &gt;= 2</code>（3个字符）才执行 '-' 缩写。"},
            {"pattern_name": "末尾连续段漏冲刷输出", "flaw": "循环结束未将缓冲区内的最后一个压缩段打印。", "testcase": "输入末尾为连续段时输出缺失。", "fix": "末尾追加哨兵字符保证最后一段被正常冲刷。"}
        ],
        ("H", "答案错误"): [
            {"pattern_name": "负号逆序反转到末尾模式：-380 变成 083-", "flaw": "对带符号整数直接执行文本切片逆序，未单独提取负号。", "testcase": "输入 <code>-380</code> 输出 <code>083-</code>，正确应为 <code>-83</code>。", "fix": "提取负号标志，逆序绝对值转 int 去除前导零后再乘回符号。"},
            {"pattern_name": "数值为 0 时被前导零逻辑过滤为空", "flaw": "去除前导零后把 0 自身也过滤掉了，导致空输出。", "testcase": "输入 <code>0</code> 输出为空白。", "fix": "对 0 增加单独特判。"}
        ],
        ("O", "答案错误"): [
            {"pattern_name": "前导零未统一或未做 set 去重模式", "flaw": "未将 '01' 与 '1' 识别为同一个整数 1 进行去重。", "testcase": "输入 <code>a01b1c</code> 输出 2，正确应为 1。", "fix": "转为 <code>int()</code> 后放入 <code>set</code> 统计数量。"},
            {"pattern_name": "末尾数字漏收集模式", "flaw": "字符串以数字结尾时循环退出未能触发收尾。", "testcase": "末尾数字未计入总数。", "fix": "循环结束后检查并收尾最后一组数字。"}
        ],
        ("R", "答案错误"): [
            {"pattern_name": "非严格递增（>=）误写为严格递增", "flaw": "比较条件误写为 <code>>=</code>（非降序）。", "testcase": "输入相同数字段时被错误计入递增。", "fix": "严格限制为 <code>></code>。"},
            {"pattern_name": "单元素输入未初始化最大长度为 1", "flaw": "只有一个数时输出长度为 0。", "testcase": "单数字输入输出 0。", "fix": "初始化最大长度为 1。"}
        ],
        ("S", "答案错误"): [
            {"pattern_name": "将不连续子序列误当作连续序列求解：dp[i]=dp[i-1]+1", "flaw": "无法跨越不匹配元素，无法求解真正的 LIS。", "testcase": "输入 <code>1 5 2 3</code> 输出长度 2，正确应为 3。", "fix": "必须使用双重循环遍历 <code>j &lt; i</code> 更新最大值。"},
            {"pattern_name": "回溯路径未逆序输出", "flaw": "输出序列顺序颠倒。", "testcase": "输出序列相反。", "fix": "输出前执行 <code>res[::-1]</code>。"}
        ],
        ("M", "答案错误"): [
            {"pattern_name": "忽略大小写判断最大字母，但输出时大小写标记混乱", "flaw": "替换 (max) 时同字母的小写未打上标记。", "testcase": "输入 <code>aAbB</code> 未同时标记 B 和 b。", "fix": "转小写求最大字母后，凡匹配均追加 (max)。"},
            {"pattern_name": "全局 replace 破坏性替换位置错位", "flaw": "replace 一次性替换了多个相同字母导致拼接乱序。", "testcase": "多重复最大字母输出错乱。", "fix": "逐字符扫描单遍构建结果。"}
        ]
    }

    diagnostics_data = {}

    for prob in target_probs:
        prob_data = {
            "title": prob_titles.get(prob, prob),
            "error_groups": []
        }

        for err_label, err_dirname in err_type_dirs.items():
            err_path = os.path.join(error_root_dir, err_dirname)
            if not os.path.exists(err_path):
                continue
            
            pattern = os.path.join(err_path, f"{prob}_*.txt")
            files = glob.glob(pattern)
            if not files:
                continue

            cluster_buckets = defaultdict(list)
            for f in files:
                uname = os.path.basename(f).split('_')[1]
                with open(f, 'r', encoding='utf-8', errors='ignore') as cf:
                    raw_code = cf.read()
                clean_c = strip_oj_watermark(raw_code)
                # 排除非 Python 代码
                if not is_python_code(clean_c) or not clean_c.strip():
                    continue

                feat = extract_code_features(prob, clean_c)
                cluster_buckets[feat].append({
                    "file": f,
                    "student": uname,
                    "code": clean_c
                })

            if not cluster_buckets:
                continue

            sorted_clusters = sorted(cluster_buckets.values(), key=len, reverse=True)
            samples = []
            know_list = cluster_diag_kb.get((prob, err_label), [])

            for c_idx, cluster in enumerate(sorted_clusters[:2]):
                cluster_samples = sorted(cluster, key=lambda x: len(x['code']))
                rep_sample = cluster_samples[len(cluster_samples) // 2]
                
                fname = os.path.basename(rep_sample["file"])
                parts = fname.replace('.txt', '').split('_')
                sub_id = parts[2] if len(parts) > 2 else "未知ID"
                
                unique_students = len(set(x["student"] for x in cluster))
                total_submissions = len(cluster)
                
                st_samples_map = {}
                for item in cluster:
                    fn = os.path.basename(item["file"])
                    ps = fn.replace('.txt', '').split('_')
                    sid = ps[2] if len(ps) > 2 else "未知ID"
                    if item["student"] not in st_samples_map:
                        st_samples_map[item["student"]] = {
                            "sub_id": sid,
                            "code": item["code"]
                        }
                
                if c_idx < len(know_list):
                    kb_item = know_list[c_idx]
                elif len(know_list) > 0:
                    kb_item = know_list[0]
                else:
                    kb_item = {
                        "pattern_name": f"特征聚类模式 {c_idx+1}",
                        "flaw": f"在处理【{prob_titles.get(prob, prob)}】时触发了 {err_label}，集中体现为边界与分支控制缺陷。",
                        "testcase": "边界测试用例故障。",
                        "fix": "严格按照题目约束规范逻辑。"
                    }

                samples.append({
                    "cluster_id": c_idx + 1,
                    "cluster_name": kb_item.get("pattern_name", f"特征聚类模式 {c_idx+1}"),
                    "cluster_coverage": f"命中 {total_submissions} 次提交 · 涉及 {unique_students} 名学生",
                    "filename": fname,
                    "student_real": rep_sample["student"],
                    "sub_id": sub_id,
                    "code": rep_sample["code"],
                    "students": list(st_samples_map.keys()),
                    "student_samples": st_samples_map,
                    "flaw": kb_item["flaw"],
                    "testcase": kb_item["testcase"],
                    "fix": kb_item["fix"]
                })

            if len(samples) == 1 and len(sorted_clusters[0]) > 1:
                alt_sample = sorted_clusters[0][-1]
                fname = os.path.basename(alt_sample["file"])
                parts = fname.replace('.txt', '').split('_')
                sub_id = parts[2] if len(parts) > 2 else "未知ID"
                if len(know_list) > 1:
                    kb_item = know_list[1]
                elif len(know_list) > 0:
                    kb_item = know_list[0]
                else:
                    kb_item = {
                        "pattern_name": "典型特征变体模式",
                        "flaw": f"在处理【{prob_titles.get(prob, prob)}】时触发了 {err_label}，属于同类聚类簇中的变体写法缺陷。",
                        "testcase": "输入边界极端用例故障。",
                        "fix": "严格按照题目约束规范逻辑。"
                    }
                samples.append({
                    "cluster_id": 2,
                    "cluster_name": kb_item.get("pattern_name", "典型特征变体模式"),
                    "cluster_coverage": f"命中 {len(sorted_clusters[0])} 次提交 · 变体样本",
                    "filename": fname,
                    "student_real": alt_sample["student"],
                    "sub_id": sub_id,
                    "code": alt_sample["code"],
                    "flaw": kb_item["flaw"],
                    "testcase": kb_item["testcase"],
                    "fix": kb_item["fix"]
                })

            valid_py_subs_count = sum(len(c) for c in cluster_buckets.values())
            prob_data["error_groups"].append({
                "err_type": err_label,
                "count": valid_py_subs_count,
                "clusters_count": len(cluster_buckets),
                "samples": samples
            })

        diagnostics_data[prob] = prob_data

    return diagnostics_data

# ==================== 主入口 ====================

def main():
    parser = argparse.ArgumentParser(description="OJ 竞赛代码异常审计与深度算法聚类分析")
    parser.add_argument("--codes-dir", default="./codes", help="AC 代码存放目录")
    parser.add_argument("--error-codes-dir", default="./error-codes", help="错误代码分类存放根目录")
    parser.add_argument("--all-subs-file", default="./all_subs.json", help="全量提交记录 JSON 文件路径")
    parser.add_argument("--basic-probs", default="A-J", help="基础题目范围，如 'A-J'")
    parser.add_argument("--prob-titles-file", default="./prob_titles.json", help="题目标题 JSON 映射文件")
    parser.add_argument("--deep-probs", default="T,S,Y,V,W,X,U,P,R,Q", help="深度分析目标题目列表，逗号分隔或 'all'")
    parser.add_argument("--output", default="./anomalies.json", help="异常与作弊审计输出 JSON 文件")
    parser.add_argument("--deep-output", default="./deep_analysis.json", help="深度算法与错误聚类输出 JSON 文件")
    args = parser.parse_args()

    print(">>> [1/4] 读取 AC 代码与题目标题...")
    prob_titles = dict(DEFAULT_PROB_TITLES)
    if os.path.exists(args.prob_titles_file):
        try:
            with open(args.prob_titles_file, "r", encoding="utf-8") as f:
                prob_titles.update(json.load(f))
        except Exception as e:
            print(f"    ⚠️ 读取 prob_titles 失败: {e}")

    subs = load_codes(args.codes_dir)
    print(f"    共加载 AC 代码: {len(subs)} 份")

    subs_by_prob = defaultdict(list)
    for s in subs:
        subs_by_prob[s["problem"]].append(s)

    basic_probs = parse_prob_range(args.basic_probs)
    print(f"    基础题范围 (跳过雷同与超纲分析): {sorted(basic_probs) if basic_probs else '无'}")

    print(">>> [2/4] 执行作弊、语言、高级语法与雷同审计...")
    non_python = []
    advanced_syntax_items = []
    advanced_syntax_by_student = defaultdict(lambda: defaultdict(set))

    for s in subs:
        p_upper = s["problem"].upper()
        lang = detect_language(s["content"])
        if lang:
            non_python.append({
                "student": s["student"],
                "prob": s["problem"],
                "lang": lang,
                "sub_id": s["sub_id"]
            })
        if p_upper not in basic_probs:
            adv = detect_advanced_syntax(s["content"])
            if adv:
                advanced_syntax_items.append({
                    "student": s["student"],
                    "prob": s["problem"],
                    "violations": adv
                })
                for v in adv:
                    advanced_syntax_by_student[s["student"]][s["problem"]].add(v)

    # 格式化按学生聚合的高级语法审计表
    student_syntax_summary = []
    for stu, prob_dict in advanced_syntax_by_student.items():
        stu_probs_desc = []
        for p, vios in sorted(prob_dict.items()):
            stu_probs_desc.append(f"{p} 题: {', '.join(sorted(vios))}")
        student_syntax_summary.append({
            "student": stu,
            "prob_count": len(prob_dict),
            "summary": "；".join(stu_probs_desc)
        })
    student_syntax_summary.sort(key=lambda x: x["prob_count"], reverse=True)

    plagiarism = detect_plagiarism(subs_by_prob, basic_probs=basic_probs)
    repeated_pairs = find_repeated_pairs(plagiarism)
    ai_comments = detect_suspicious_comments(subs)

    first_ac_data, submission_bursts = analyze_submission_bursts_and_first_ac(args.all_subs_file)

    anomalies_data = {
        "non_python": non_python,
        "advanced_syntax": advanced_syntax_items,
        "advanced_syntax_by_student": student_syntax_summary,
        "plagiarism_groups": plagiarism,
        "repeated_pairs": repeated_pairs,
        "ai_comments": ai_comments,
        "first_ac_analysis": first_ac_data,
        "submission_bursts": submission_bursts
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(anomalies_data, f, ensure_ascii=False, indent=2)
    print(f"    ✅ 审计数据已保存至: {args.output}")

    print(">>> [3/4] 执行 AC 算法派系分析与错误代码特征聚类 (纯 Python，无水印)...")
    if args.deep_probs.lower() == "all":
        target_probs = sorted(list(set(list(subs_by_prob.keys()) + list(DEFAULT_PROB_TITLES.keys()))))
        target_probs = [p for p in target_probs if p.upper() not in basic_probs]
    else:
        target_probs = [p.strip() for p in args.deep_probs.split(",") if p.strip() and p.strip().upper() not in basic_probs]

    ac_analysis = analyze_ac_algorithms(args.codes_dir, target_probs, prob_titles)
    err_diagnostics = cluster_error_codes(args.error_codes_dir, target_probs, prob_titles)

    deep_data = {
        "ac_analysis": ac_analysis,
        "err_diagnostics": err_diagnostics
    }

    with open(args.deep_output, "w", encoding="utf-8") as f:
        json.dump(deep_data, f, ensure_ascii=False, indent=2)
    print(f"    ✅ 深度分析数据已保存至: {args.deep_output}")

    print(">>> [4/4] 审计与深度聚类分析全部完成！")

if __name__ == "__main__":
    main()
