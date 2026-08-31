#!/usr/bin/env python3
"""
fetch_data.py - krand.site (HUSTOJ) 专用数据抓取与源码下载脚本
功能：
1. 抓取竞赛榜单 (contestrank.php) 并自动从表头提取题目中文名与竞赛名称
2. 全量分页抓取所有提交记录 (status.php)
3. 自动根据提交记录从 showsource.php 下载全部 AC 源码文件至 codes/ 目录

用法：
  python3 fetch_data.py --cid 1081 --cookie "PHPSESSID=xxx" --output-dir ./2026新高二暑假作业 --download-codes
"""

import argparse
import json
import os
import re
import sys
import time
import ssl
from urllib.request import urlopen, Request
from urllib.error import URLError
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://krand.site"

ssl_ctx = ssl._create_unverified_context()

def make_request(url, cookie, timeout=25):
    req = Request(url, headers={
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    })
    with urlopen(req, timeout=timeout, context=ssl_ctx) as r:
        return r.read().decode("utf-8", errors="ignore")

def detect_login_page(html):
    return "<title>登录" in html or "login.php" in html or "请先登录" in html or "您没有权限" in html

def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()

def parse_contest_page(html):
    """
    从 contest.php 提取准确的竞赛名称和各题目的中文题名
    """
    contest_name = "OJ 竞赛"
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    if title_match:
        t = title_match.group(1).replace("OnlineJudge", "").replace("HUSTOJ", "").replace("krand", "").strip("- ")
        # Also remove 'Contest1081 - ' prefix if present
        t = re.sub(r"^Contest\d+\s*[-—:]\s*", "", t).strip("- ")
        if t:
            contest_name = t

    prob_titles = {}
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
    for r in rows:
        tds = re.findall(r"<td[^>]*>(.*?)</td>", r, re.DOTALL | re.IGNORECASE)
        if len(tds) >= 3:
            cleaned = [strip_tags(x) for x in tds]
            # Pattern: ['Y', 'A', 'Hello World✦', '168', '260'] or ['A', 'Hello World', ...]
            prob_label = None
            prob_name = None
            for idx, c in enumerate(cleaned):
                if re.match(r"^[A-Z]$", c):
                    prob_label = c
                    if idx + 1 < len(cleaned):
                        prob_name = cleaned[idx + 1].rstrip("✦* ").strip()
                    break
            if prob_label and prob_name:
                prob_titles[prob_label] = prob_name

    return contest_name, prob_titles

def parse_rank_page(html):
    """
    解析 contestrank.php:
    1. 提取竞赛名称
    2. 提取题目名称字典 { 'A': 'Hello World', ... }
    3. 提取学生列表
    """
    # 提取竞赛标题
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    contest_name = "OJ 竞赛"
    if title_match:
        t = title_match.group(1).replace("- OnlineJudge", "").replace("- krand", "").replace("- HUSTOJ", "").strip()
        t = re.sub(r"^Contest\s*RankList\s*[-—:]+\s*", "", t, flags=re.IGNORECASE).strip("- ")
        if t:
            contest_name = t
    
    DEFAULT_TITLES = {
        "A": "Hello World", "B": "两整数求和", "C": "商和余数", "D": "与圆相关的计算", "E": "两数比大小",
        "F": "一门课不及格的学生", "G": "求三个数的最大数", "H": "任意整数逆序输出", "I": "二进制转十进制", "J": "角谷猜想",
        "K": "单词反转1", "L": "回文串", "M": "查找最大字母", "N": "中文数字", "O": "字符串中整数的个数",
        "P": "字符消消乐", "Q": "字符串缩写", "R": "最长连续递增序列", "S": "最长不连续递增子序列", "T": "简单四则运算",
        "U": "竖写单词", "V": "整理字符串", "W": "字符串旋转", "X": "单词反转2", "Y": "找到元素排序后的下标"
    }

    # 提取表头中的题目名称
    prob_titles = dict(DEFAULT_TITLES)
    th_matches = re.findall(r"<th[^>]*>(.*?)</th>", html, re.DOTALL | re.IGNORECASE)
    for th in th_matches:
        txt = strip_tags(th)
        # Match pattern like "A: Hello World" or "A - Hello World" or "Problem A: ..."
        m = re.search(r"([A-Z])[\s:：\-]+(.+)", txt)
        if m:
            prob_titles[m.group(1)] = m.group(2).strip()
        elif len(txt) == 1 and txt.isalpha() and txt.isupper() and txt not in prob_titles:
            prob_titles[txt] = f"题目 {txt}"
            
    # 提取所有排名学生行
    users = []
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
        if not cells or len(cells) < 4:
            continue
        cleaned = [strip_tags(c) for c in cells]
        if not cleaned[0].isdigit():
            continue
        try:
            users.append({
                "rank": cleaned[0],
                "user": cleaned[1],
                "nick": cleaned[1],  # 统一使用真实用户名 user，避免自定义昵称
                "solved": int(cleaned[3]) if cleaned[3].isdigit() else 0,
                "penalty": cleaned[4] if len(cleaned) > 4 else "0"
            })
        except Exception:
            pass
            
    return contest_name, prob_titles, users

def parse_status_rows(html):
    subs = []
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
        if len(cells) < 8:
            continue
        c_text = [strip_tags(c) for c in cells]
        if not c_text[0].isdigit():
            continue
        try:
            sub_id = int(c_text[0])
            user = c_text[1]
            prob = ""
            result = ""
            for item in c_text[2:]:
                if re.match(r"^[A-Z]$", item) or re.match(r"^\d+$", item):
                    prob = item
                elif any(kw in item for kw in ["Accept", "Wrong", "Time", "Runtime", "Compile", "正确", "错误", "AC", "WA", "TLE", "RE", "CE", "Presentation"]):
                    result = item
            
            time_raw = ""
            for item in c_text:
                if re.search(r"\d{2}-\d{2}\s+\d{2}:\d{2}|\d{4}-\d{2}-\d{2}", item):
                    time_raw = item
                    break
                    
            nick = user  # 统一使用用户名 user
            if prob and result:
                subs.append({
                    "sub_id": sub_id,
                    "user": user,
                    "nick": nick,
                    "prob": prob,
                    "result": result,
                    "time_raw": time_raw,
                    "lang": c_text[7] if len(c_text) > 7 else ""
                })
        except Exception:
            pass
    return subs

def fetch_all_subs(cid, cookie):
    all_subs = []
    seen_ids = set()
    page = 0
    last_top = None
    print("[2/4] 正在抓取全量提交日志（翻页中）...")
    while True:
        url = f"{BASE_URL}/status.php?cid={cid}" + (f"&top={last_top}" if last_top else "")
        try:
            html = make_request(url, cookie)
        except Exception as e:
            print(f"  ⚠️ 请求第 {page+1} 页失败: {e}，停止翻页")
            break
            
        if detect_login_page(html):
            print("  ❌ Cookie 已失效或无权限")
            break
            
        rows = parse_status_rows(html)
        if not rows:
            break
        new_rows = [r for r in rows if r["sub_id"] not in seen_ids]
        if not new_rows:
            break
            
        all_subs.extend(new_rows)
        seen_ids.update(r["sub_id"] for r in new_rows)
        min_id = min(r["sub_id"] for r in new_rows)
        last_top = min_id - 1
        page += 1
        if page % 10 == 0 or len(rows) < 20:
            print(f"  已抓取第 {page} 页，累计获取 {len(all_subs)} 条记录 (最新ID: {new_rows[0]['sub_id']}, 最小ID: {min_id})")
        time.sleep(0.05)
        if page > 600:
            break
            
    print(f"✅ 全量提交日志抓取完毕，共 {len(all_subs)} 条记录")
    return all_subs

def download_single_code(sub, cookie, codes_dir):
    sub_id = sub["sub_id"]
    prob = sub["prob"]
    user = sub["user"]
    filename = f"{prob}_{user}_{sub_id}.txt"
    filepath = os.path.join(codes_dir, filename)
    
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        return True
        
    url = f"{BASE_URL}/showsource.php?id={sub_id}"
    for attempt in range(3):
        try:
            html = make_request(url, cookie, timeout=15)
            # Extract code inside <pre> or <code> or <textarea>
            code_match = re.search(r"<(pre|code|textarea)[^>]*>(.*?)</(?:pre|code|textarea)>", html, re.DOTALL | re.IGNORECASE)
            if code_match:
                code_text = code_match.group(2)
                # Unescape HTML entities
                import html as py_html
                code_text = py_html.unescape(code_text)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(code_text)
                return True
            else:
                # Maybe raw source text
                if len(html) > 10 and "<html" not in html.lower():
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(html)
                    return True
        except Exception:
            time.sleep(0.3)
    return False

def download_error_codes(all_subs, cookie, error_root_dir):
    err_subs = [s for s in all_subs if not any(kw in s["result"] for kw in ["Accept", "AC", "正确", "Pending", "Running", "Compiling"])]
    print(f"\n[4/4+] 开始并发下载错误提交代码（共 {len(err_subs)} 份）...")
    
    type_mapping = {
        "Wrong": "答案错误", "WA": "答案错误", "错误": "答案错误",
        "Runtime": "运行错误", "RE": "运行错误",
        "Time": "时间超限", "TLE": "时间超限",
        "Compile": "编译错误", "CE": "编译错误",
        "Presentation": "格式错误", "PE": "格式错误"
    }

    def categorize_err(res_str):
        for k, v in type_mapping.items():
            if k.lower() in res_str.lower():
                return v
        return "答案错误"

    os.makedirs(error_root_dir, exist_ok=True)
    for v in set(type_mapping.values()):
        os.makedirs(os.path.join(error_root_dir, v), exist_ok=True)

    success = 0
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {}
        for s in err_subs:
            sub_err_dir = os.path.join(error_root_dir, categorize_err(s["result"]))
            futures[executor.submit(download_single_code, s, cookie, sub_err_dir)] = s

        for idx, fut in enumerate(as_completed(futures), 1):
            if fut.result():
                success += 1
            if idx % 200 == 0 or idx == len(err_subs):
                print(f"  已下载错误代码 {idx}/{len(err_subs)} (成功 {success})")
    print(f"✅ 错误代码下载完成！成功保存 {success} 份代码至 {error_root_dir}")

def download_ac_codes(all_subs, cookie, codes_dir):
    ac_subs = [s for s in all_subs if any(kw in s["result"] for kw in ["Accept", "AC", "正确"])]
    print(f"\n[3/4] 开始并发下载全量 AC 源代码（共 {len(ac_subs)} 份）...")
    os.makedirs(codes_dir, exist_ok=True)
    
    success = 0
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(download_single_code, s, cookie, codes_dir): s for s in ac_subs}
        for idx, fut in enumerate(as_completed(futures), 1):
            if fut.result():
                success += 1
            if idx % 200 == 0 or idx == len(ac_subs):
                print(f"  已下载 {idx}/{len(ac_subs)} (成功 {success})")
    print(f"✅ 源代码下载完成！成功保存 {success} 份代码至 {codes_dir}")

def main():
    parser = argparse.ArgumentParser(description="krand.site 数据抓取与源码下载")
    parser.add_argument("--cid", required=True, help="竞赛 ID (CID)")
    parser.add_argument("--cookie", required=True, help="浏览器 Cookie")
    parser.add_argument("--output-dir", required=True, help="输出保存目录")
    parser.add_argument("--download-codes", action="store_true", help="是否下载全量 AC 代码")
    parser.add_argument("--download-error-codes", action="store_true", help="是否下载全量错误代码")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"\n[1/4] 正在抓取竞赛主页、榜单与题目信息 (CID: {args.cid})...")
    contest_url = f"{BASE_URL}/contest.php?cid={args.cid}"
    contest_html = make_request(contest_url, args.cookie)
    if detect_login_page(contest_html):
        print("❌ 错误：Cookie 无效或已过期，请重新获取 Cookie！")
        sys.exit(1)

    c_name, p_titles = parse_contest_page(contest_html)

    rank_url = f"{BASE_URL}/contestrank.php?cid={args.cid}"
    rank_html = make_request(rank_url, args.cookie)
    _, rank_p_titles, rank_users = parse_rank_page(rank_html)

    # 优先使用 contest.php 的具体题目名称，补充缺失项
    prob_titles = {**rank_p_titles, **p_titles}
    contest_name = c_name or "2026新高二暑假作业"

    print(f"✅ 竞赛名称: {contest_name}")
    print(f"✅ 识别到 {len(rank_users)} 名注册学生，{len(prob_titles)} 道题目")

    # 保存榜单和题目名
    with open(os.path.join(args.output_dir, "rank_users.json"), "w", encoding="utf-8") as f:
        json.dump(rank_users, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.output_dir, "prob_titles.json"), "w", encoding="utf-8") as f:
        json.dump(prob_titles, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.output_dir, "contest_info.json"), "w", encoding="utf-8") as f:
        json.dump({"contest_name": contest_name, "cid": args.cid}, f, ensure_ascii=False, indent=2)

    # 抓取提交
    all_subs = fetch_all_subs(args.cid, args.cookie)
    print(f"✅ 成功获取全量提交日志: {len(all_subs)} 条")
    with open(os.path.join(args.output_dir, "all_subs.json"), "w", encoding="utf-8") as f:
        json.dump(all_subs, f, ensure_ascii=False, indent=2)

    # 下载代码
    if args.download_codes:
        codes_dir = os.path.join(args.output_dir, "codes")
        download_ac_codes(all_subs, args.cookie, codes_dir)

    if args.download_error_codes:
        error_codes_dir = os.path.join(args.output_dir, "error-codes")
        download_error_codes(all_subs, args.cookie, error_codes_dir)

    print(f"\n🎉 数据获取全部完成，数据保存在: {args.output_dir}")

if __name__ == "__main__":
    main()
