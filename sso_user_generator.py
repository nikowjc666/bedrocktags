#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量在 AWS IAM Identity Center 创建 SSO 用户。

邮箱规则: 前缀 + 序号 + @域名, 例如 kiro01@example.com。
支持指定数量、序号起始值、序号位数, 支持 dry-run 预览、幂等跳过、
以及可选地把新用户加入指定组。

用法示例:
    # 预览将要创建的 3 个用户, 不实际调用 AWS
    python sso_user_generator.py --prefix kiro --domain example.com --count 3 --dry-run

    # 真正创建 5 个用户 (kiro01..kiro05), 序号 2 位
    python sso_user_generator.py --prefix kiro --domain example.com --count 5

    # 从序号 10 开始创建 3 个, 并加入某个组
    python sso_user_generator.py --prefix kiro --domain example.com --count 3 \
        --start 10 --group Developers
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
except ImportError:  # 允许在未安装 boto3 时至少能跑 --dry-run
    boto3 = None
    ClientError = BotoCoreError = Exception


@dataclass
class PlannedUser:
    """一个待创建用户的完整信息。"""
    username: str
    email: str
    given_name: str
    family_name: str
    display_name: str


def build_users(
    prefix: str,
    domain: str,
    count: int,
    start: int = 1,
    pad: int = 2,
) -> list[PlannedUser]:
    """根据规则生成用户列表。

    count == 1 时不加序号后缀 (username = prefix), 便于单个用户场景。
    count > 1 时使用零填充序号: prefix01, prefix02 ...
    """
    if count < 1:
        raise ValueError("count 必须 >= 1")
    if start < 0:
        raise ValueError("start 必须 >= 0")

    users: list[PlannedUser] = []
    for i in range(count):
        seq = start + i
        # 只有 count==1 且 start==1 时才省略序号 (纯单用户场景)
        # 只要 start != 1, 说明明确指定了起始序号, 一定加序号后缀
        if count == 1 and start == 1:
            username = prefix
        else:
            username = f"{prefix}{seq:0{pad}d}"
        email = f"{username}@{domain}"
        display = username
        users.append(
            PlannedUser(
                username=username,
                email=email,
                given_name=prefix,
                family_name=str(seq),
                display_name=display,
            )
        )
    return users


def resolve_identity_store_id(session, explicit_id: Optional[str]) -> str:
    """获取 Identity Store ID。若未显式提供, 通过 sso-admin 自动发现。"""
    if explicit_id:
        return explicit_id
    sso_admin = session.client("sso-admin")
    instances = sso_admin.list_instances().get("Instances", [])
    if not instances:
        raise RuntimeError(
            "未找到 IAM Identity Center 实例, 请确认已启用, "
            "或用 --identity-store-id 显式指定。"
        )
    if len(instances) > 1:
        ids = ", ".join(inst["IdentityStoreId"] for inst in instances)
        raise RuntimeError(
            f"检测到多个 Identity Center 实例 ({ids}), 请用 --identity-store-id 指定。"
        )
    return instances[0]["IdentityStoreId"]


def find_existing_user(identitystore, identity_store_id: str, username: str) -> Optional[str]:
    """按 UserName 查找已存在用户, 返回 UserId 或 None。"""
    try:
        resp = identitystore.get_user_id(
            IdentityStoreId=identity_store_id,
            AlternateIdentifier={
                "UniqueAttribute": {
                    "AttributePath": "UserName",
                    "AttributeValue": username,
                }
            },
        )
        return resp["UserId"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return None
        raise


def find_group_id(identitystore, identity_store_id: str, group_name: str) -> str:
    """按显示名查找组 ID。"""
    resp = identitystore.get_group_id(
        IdentityStoreId=identity_store_id,
        AlternateIdentifier={
            "UniqueAttribute": {
                "AttributePath": "DisplayName",
                "AttributeValue": group_name,
            }
        },
    )
    return resp["GroupId"]


def ensure_group(identitystore, identity_store_id: str, group_name: str) -> tuple[str, bool]:
    """获取组 ID, 不存在则创建。返回 (group_id, created)。

    按组管理便于后续在 Kiro 控制台一次性对整个组开通订阅,
    不必逐个用户添加。
    """
    try:
        return find_group_id(identitystore, identity_store_id, group_name), False
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
    resp = identitystore.create_group(
        IdentityStoreId=identity_store_id,
        DisplayName=group_name,
        Description="批量创建的 SSO 用户组 (用于 Kiro 订阅)",
    )
    return resp["GroupId"], True


def build_portal_url(identity_store_id: str, subdomain: Optional[str] = None) -> str:
    """构造 AWS access portal (登录门户) 地址。

    默认形式: https://d-xxxxxxxxxx.awsapps.com/start
    若在 Identity Center 里配置了自定义子域, 则为
    https://<subdomain>.awsapps.com/start
    """
    host = (subdomain or identity_store_id or "").strip()
    if not host:
        return ""
    return f"https://{host}.awsapps.com/start"


def build_dualstack_portal_url(instance_id: str, region: str) -> str:
    """构造双栈登录地址 (控制台里显示的第二个 URL)。

    形式: https://<instance_id>.portal.<region>.app.aws
    instance_id 形如 ssoins-72239bb0ae50b6e3 (来自 InstanceArn 末段)。
    """
    inst = (instance_id or "").strip()
    reg = (region or "").strip()
    if not inst or not reg:
        return ""
    return f"https://{inst}.portal.{reg}.app.aws"


def create_user(identitystore, identity_store_id: str, user: PlannedUser) -> str:
    """创建单个用户, 返回 UserId。"""
    resp = identitystore.create_user(
        IdentityStoreId=identity_store_id,
        UserName=user.username,
        DisplayName=user.display_name,
        Name={"GivenName": user.given_name, "FamilyName": user.family_name},
        Emails=[{"Value": user.email, "Type": "work", "Primary": True}],
    )
    return resp["UserId"]


def delete_user(identitystore, identity_store_id: str, user_id: str) -> None:
    """按 UserId 删除用户。此操作不可逆。"""
    identitystore.delete_user(
        IdentityStoreId=identity_store_id,
        UserId=user_id,
    )


def add_to_group(identitystore, identity_store_id: str, group_id: str, user_id: str) -> None:
    """把用户加入组 (幂等: 已存在成员关系会被忽略)。"""
    try:
        identitystore.create_group_membership(
            IdentityStoreId=identity_store_id,
            GroupId=group_id,
            MemberId={"UserId": user_id},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConflictException":
            return
        raise


EXPORT_HEADERS = [
    "username",
    "email",
    "display_name",
    "user_id",
    "portal_url",
    "one_time_password",
    "password_note",
    "status",
]


def write_reports(results: list[dict], portal_url: str = "") -> tuple[str, str]:
    """把结果写到 CSV 和 JSON, 返回两个文件名。

    导出内容包含登录地址 (portal_url) 和一次性密码列 (one_time_password)。
    注意: IAM Identity Center 没有生成一次性密码的 API, 该列需要管理员
    在控制台生成后自行填写; 若已开启 Send email OTP, 用户会收到邮件自行设密码。
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"sso_users_{ts}.csv"
    json_path = f"sso_users_{ts}.json"

    rows = []
    for r in results:
        row = dict(r)
        row.setdefault("display_name", row.get("username", ""))
        row["portal_url"] = row.get("portal_url") or portal_url
        row.setdefault("one_time_password", "")
        row.setdefault(
            "password_note",
            "控制台生成一次性密码后填入, 或开启 Send email OTP 由用户自行设置",
        )
        rows.append(row)

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(EXPORT_HEADERS)
        for row in rows:
            writer.writerow([row.get(h, "") for h in EXPORT_HEADERS])

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {"portal_url": portal_url, "users": rows},
            f, ensure_ascii=False, indent=2,
        )

    return csv_path, json_path


def _html_escape(value) -> str:
    """转义 HTML 特殊字符, 避免用户名/密码里的符号破坏文档结构。"""
    s = "" if value is None else str(value)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


DELIVERY_CSS = """
body{font-family:"Microsoft YaHei",sans-serif;padding:28px;color:#111;}
h1{font-size:20px;margin-bottom:4px;}
.note{color:#555;font-size:13px;margin-bottom:20px;line-height:1.7;}
.u{border:1px solid #ddd;border-radius:8px;padding:14px;margin-bottom:14px;
   page-break-inside:avoid;}
.t{font-weight:700;margin-bottom:8px;font-size:15px;}
table{border-collapse:collapse;width:100%;font-size:13px;}
th{text-align:left;width:110px;color:#555;padding:4px 0;vertical-align:top;}
td{padding:4px 0;word-break:break-all;}
.pw{font-family:Consolas,monospace;font-weight:700;}
.miss{color:#b91c1c;}
"""


def write_delivery_html(results: list[dict], portal_url: str = "",
                        dualstack_url: str = "") -> str:
    """生成按用户分卡片的交付文档 (HTML), 返回文件名。

    包含完整登录方式: 登录地址 (及备用双栈地址)、用户名、邮箱、初始密码、
    所属组, 以及"如何登录"的步骤说明。可直接打印或另存为 PDF 发给客户。
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"sso_登录信息_{ts}.html"

    delivery_css = (
        'body{font-family:"Microsoft YaHei",sans-serif;padding:28px;color:#111;}'
        "h1{font-size:20px;margin-bottom:4px;}"
        ".note{color:#555;font-size:13px;margin-bottom:16px;line-height:1.8;}"
        ".how{background:#f0f6ff;border:1px solid #bfdbfe;border-radius:8px;"
        "padding:12px 16px;margin-bottom:20px;font-size:13px;line-height:1.8;}"
        ".how ol{margin:6px 0 0 20px;padding:0;}"
        ".u{border:1px solid #ddd;border-radius:8px;padding:14px;margin-bottom:14px;"
        "page-break-inside:avoid;}"
        ".t{font-weight:700;margin-bottom:8px;font-size:15px;}"
        "table{border-collapse:collapse;width:100%;font-size:13px;}"
        "th{text-align:left;width:96px;color:#555;padding:4px 0;vertical-align:top;}"
        "td{padding:4px 0;word-break:break-all;}"
        ".pw{font-family:Consolas,monospace;font-weight:700;color:#b45309;}"
        ".miss{color:#b91c1c;}"
    )

    cards = []
    for r in results:
        url = r.get("portal_url") or portal_url
        dual = r.get("portal_url_dualstack") or dualstack_url
        pwd = r.get("one_time_password") or ""
        pwd_html = (
            f'<span class="pw">{_html_escape(pwd)}</span>' if pwd
            else '<span class="miss">(未获取到密码)</span>'
        )
        rows = [
            f'<tr><th>登录地址</th><td><a href="{_html_escape(url)}">'
            f"{_html_escape(url)}</a></td></tr>",
        ]
        if dual:
            rows.append(
                f'<tr><th>备用地址</th><td><a href="{_html_escape(dual)}">'
                f"{_html_escape(dual)}</a></td></tr>"
            )
        rows += [
            f'<tr><th>用户名</th><td>{_html_escape(r.get("username"))}</td></tr>',
            f'<tr><th>邮箱</th><td>{_html_escape(r.get("email"))}</td></tr>',
            f"<tr><th>初始密码</th><td>{pwd_html}</td></tr>",
        ]
        if r.get("group"):
            rows.append(f'<tr><th>所属组</th><td>{_html_escape(r.get("group"))}</td></tr>')
        cards.append(
            '<div class="u">'
            f'<div class="t">{_html_escape(r.get("username"))}</div>'
            "<table>" + "".join(rows) + "</table></div>"
        )

    # 登录方式说明 (放在文档开头, 让客户知道怎么用这些信息登录)
    how_to = (
        '<div class="how"><b>如何登录</b>'
        "<ol>"
        f'<li>在浏览器打开登录地址:'
        f'<a href="{_html_escape(portal_url)}">{_html_escape(portal_url)}</a></li>'
        "<li>输入下方对应的用户名和初始密码。</li>"
        "<li>首次登录会要求设置新密码,并可能要求注册多因素认证 (MFA) 设备。</li>"
        "<li>设置完成后即可进入 AWS 访问门户,使用已分配的应用与账号。</li>"
        "</ol></div>"
    )

    html = (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
        "<title>SSO 登录信息</title>"
        f"<style>{delivery_css}</style></head><body>"
        "<h1>AWS SSO 登录信息</h1>"
        f'<div class="note">生成时间:{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        f"<br>登录地址:{_html_escape(portal_url)}"
        + (f"<br>备用地址:{_html_escape(dualstack_url)}" if dualstack_url else "")
        + "<br>初始密码为一次性密码,首次登录后请立即修改。</div>"
        + how_to
        + "".join(cards) + "</body></html>"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="批量在 AWS IAM Identity Center 创建 SSO 用户",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--prefix", required=True, help="用户名前缀, 例如 kiro")
    p.add_argument("--domain", required=True, help="邮箱域名, 例如 example.com")
    p.add_argument("--count", type=int, required=True, help="要创建的用户数量")
    p.add_argument("--start", type=int, default=1, help="序号起始值 (默认 1)")
    p.add_argument("--pad", type=int, default=2, help="序号零填充位数 (默认 2, 即 01)")
    p.add_argument("--group", default=None, help="可选: 创建后加入的组显示名")
    p.add_argument(
        "--create-group",
        action="store_true",
        help="可选: 组不存在时自动创建 (便于在 Kiro 控制台按组订阅)",
    )
    p.add_argument(
        "--identity-store-id",
        default=None,
        help="可选: Identity Store ID; 不填则自动发现",
    )
    p.add_argument(
        "--portal-subdomain",
        default=None,
        help="可选: 登录门户自定义子域; 不填则用 Identity Store ID 拼接",
    )
    p.add_argument("--region", default=None, help="可选: AWS 区域, 例如 us-east-1")
    p.add_argument("--profile", default=None, help="可选: AWS 凭证 profile 名称")
    p.add_argument("--access-key-id", default=None, help="可选: 直接指定 Access Key ID")
    p.add_argument(
        "--secret-access-key", default=None, help="可选: 直接指定 Secret Access Key"
    )
    p.add_argument("--session-token", default=None, help="可选: 临时凭证的 Session Token")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="只预览将要创建的用户, 不调用 AWS",
    )
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    try:
        users = build_users(args.prefix, args.domain, args.count, args.start, args.pad)
    except ValueError as e:
        print(f"参数错误: {e}", file=sys.stderr)
        return 2

    print(f"计划创建 {len(users)} 个用户:")
    for u in users:
        print(f"  - {u.username:<16} {u.email}")

    if args.dry_run:
        print("\n[dry-run] 未调用 AWS。移除 --dry-run 以实际创建。")
        return 0

    if boto3 is None:
        print("未安装 boto3, 请先运行: pip install -r requirements.txt", file=sys.stderr)
        return 1

    if bool(args.access_key_id) != bool(args.secret_access_key):
        print(
            "--access-key-id 和 --secret-access-key 必须同时提供。",
            file=sys.stderr,
        )
        return 2

    try:
        if args.access_key_id:
            session = boto3.Session(
                aws_access_key_id=args.access_key_id,
                aws_secret_access_key=args.secret_access_key,
                aws_session_token=args.session_token,
                region_name=args.region,
            )
        else:
            session = boto3.Session(profile_name=args.profile, region_name=args.region)
        identity_store_id = resolve_identity_store_id(session, args.identity_store_id)
        identitystore = session.client("identitystore")
    except (ClientError, BotoCoreError, RuntimeError) as e:
        print(f"初始化 AWS 客户端失败: {e}", file=sys.stderr)
        return 1

    portal_url = build_portal_url(identity_store_id, args.portal_subdomain)
    print(f"\n使用 Identity Store: {identity_store_id}")
    print(f"登录地址 (access portal): {portal_url}")

    group_id = None
    if args.group:
        try:
            if args.create_group:
                group_id, was_created = ensure_group(
                    identitystore, identity_store_id, args.group
                )
                tag = " (新建)" if was_created else ""
                print(f"目标组 '{args.group}'{tag} -> {group_id}")
            else:
                group_id = find_group_id(identitystore, identity_store_id, args.group)
                print(f"目标组 '{args.group}' -> {group_id}")
        except ClientError as e:
            print(f"处理组 '{args.group}' 失败: {e}", file=sys.stderr)
            return 1

    results: list[dict] = []
    created = skipped = failed = 0

    for u in users:
        row = {
            "username": u.username,
            "email": u.email,
            "display_name": u.display_name,
            "user_id": "",
            "portal_url": portal_url,
            "one_time_password": "",
            "status": "",
        }
        try:
            existing = find_existing_user(identitystore, identity_store_id, u.username)
            if existing:
                row["user_id"] = existing
                row["status"] = "skipped_exists"
                skipped += 1
                print(f"  跳过 (已存在): {u.username}")
            else:
                user_id = create_user(identitystore, identity_store_id, u)
                row["user_id"] = user_id
                row["status"] = "created"
                created += 1
                print(f"  已创建: {u.username} -> {user_id}")

            if group_id and row["user_id"]:
                add_to_group(identitystore, identity_store_id, group_id, row["user_id"])
                print(f"    已加入组 '{args.group}'")

        except (ClientError, BotoCoreError) as e:
            row["status"] = f"error: {e}"
            failed += 1
            print(f"  失败: {u.username} -> {e}", file=sys.stderr)

        results.append(row)

    csv_path, json_path = write_reports(results, portal_url)

    print(
        f"\n完成。创建 {created}, 跳过 {skipped}, 失败 {failed}。\n"
        f"导出: {csv_path} / {json_path}"
    )
    print(
        "\n关于密码 (AWS 限制: 无生成一次性密码的 API):\n"
        "  方式一 (推荐): 控制台 Settings -> Authentication -> Standard authentication\n"
        "                 开启 Send email OTP, 用户首次登录会收到邮件自行设置密码。\n"
        "  方式二: 在控制台逐个用户 Reset password -> Generate a one-time password,\n"
        "         再把密码填入导出 CSV 的 one_time_password 列后分发。"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
