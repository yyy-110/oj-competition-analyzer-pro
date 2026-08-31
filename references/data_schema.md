# 数据结构规范 (Data Schema) - Pro 版

---

## 1. 班级名单结构 (Excel / CSV / JSON)

### Excel 多列模式（默认标准模式）
- 第一行每一列为班级名称（如 `技术1班`, `技术2班`, `首创`）
- 列下方单元格为该班学生姓名。

示例表格：
| 技术1班 | 技术2班 | 首创 |
| :--- | :--- | :--- |
| 张三 | 赵六 | 周八 |
| 李四 | 钱七 | 吴九 |
| 王五 | 孙八 | 郑十 |

---

## 2. class_summary.json (班级横向对比数据)

`generate_report.py` 产出的班级聚合与对比数据。

```json
{
  "classes": ["技术1班", "技术2班", "未分班"],
  "summary": [
    {
      "class_name": "技术1班",
      "roster_count": 55,
      "actual_count": 54,
      "attend_rate": 98.2,
      "avg_solved": 21.4,
      "full_cnt": 12,
      "full_rate": 22.2,
      "avg_subs": 68.2,
      "ac_rate": 62.5,
      "anomaly_users_cnt": 3,
      "anomaly_rate": 5.6,
      "prob_pass_rates": {
        "A": 100.0,
        "B": 98.1,
        "K": 51.9
      }
    }
  ],
  "all_probs": ["A", "B", "C", "...", "Y"]
}
```

---

## 3. 全员榜单 rank_users.json 与 提交记录 all_subs.json

- **用户身份契约**：严格以 `user` 真实用户名（如 `许珺杰2028`）为唯一主键，废弃自定义乱填昵称 `nick`；
- **包含字段**：`user`, `solved`, `penalty`, `sub_id`, `prob`, `result`, `time_raw`。

---

## 4. anomalies.json (代码异常审计)

包含：
- `non_python`: 非 Python 语言违规提交列表；
- `advanced_syntax`: 超纲高级 Python 语法；
- `plagiarism_groups`: 去注释 AST 与文本高雷同代码群组（≥95%）；
- `submission_bursts`: 短时间突发极速连交/秒交记录；
- `ai_comments`: 代码注释中自曝 AI 互动痕迹。

---

## 5. deep_analysis.json (深度算法流派与错误代码聚类)

包含非基础题（K~Y）的 AC 算法流派 AST 聚类与 Top 10 核心题错误代码聚类：

```json
{
  "ac_analysis": {
    "K": {
      "title": "单词反转1",
      "total_ac": 124,
      "summary_intro": "...",
      "teaching_note": "...",
      "genres": [
        {
          "name": "双重嵌套循环",
          "complexity": "O(n²)",
          "students": ["张三2028", "李四2028"],
          "student_samples": {
            "张三2028": "s = input()...\n",
            "李四2028": "s = input()...\n"
          },
          "sample_user": "张三2028",
          "sample_code": "s = input()...\n",
          "count": 28,
          "pct": 22.6
        }
      ]
    }
  },
  "err_diagnostics": {
    "K": {
      "title": "单词反转1",
      "error_groups": [
        {
          "err_type": "答案错误",
          "count": 18,
          "clusters_count": 2,
          "samples": [
            {
              "cluster_id": 1,
              "cluster_name": "整句全局逆序模式",
              "students": ["张三2028", "王五2028"],
              "student_samples": {
                "张三2028": { "sub_id": "100234", "code": "print(s[::-1])" }
              },
              "flaw": "...",
              "testcase": "...",
              "fix": "..."
            }
          ]
        }
      ]
    }
  }
}
```\n