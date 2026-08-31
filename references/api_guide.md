# HUSTOJ (krand.site) 接口与抓取指南

## 1. 认证机制
HUSTOJ 使用标准的 PHP Session Cookie 进行鉴权。
- 格式：`PHPSESSID=xxx; resolveIDs=0`
- 权限要求：需要能访问 `contestrank.php`、`status.php` 和 `showsource.php` 的教师或管理权限。

## 2. 核心 URL 清单
- 竞赛信息与题目列表：`https://krand.site/contest.php?cid={cid}`
- 排名榜单：`https://krand.site/contestrank.php?cid={cid}`
- 提交状态日志：`https://krand.site/status.php?cid={cid}&top={last_sub_id}`
- 源码详情：`https://krand.site/showsource.php?id={sub_id}`
