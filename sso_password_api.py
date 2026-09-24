#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过 SWBUPService.UpdatePassword 接口直接生成一次性密码。

抓包确认的接口格式:
    端点:    https://identitystore.<region>.amazonaws.com/
    Target:  SWBUPService.UpdatePassword
    服务名:  userpool  (SigV4 签名)
    请求体:  {"UserId": "<uid>", "PasswordMode": "OTP",
              "IdentityStoreId": "<store_id>"}

响应里含一次性密码, 字段名待确认 (常见: Password / OneTimePassword / password)。
"""
from __future__ import annotations

import re
import json
from typing import Any, Optional

try:
    import boto3
    import requests
    from requests.adapters import HTTPAdapter
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    from botocore.credentials import Credentials
except ImportError as e:
    raise ImportError("请先 pip install boto3 requests") from e


def new_http_session(concurrency: int = 8) -> "requests.Session":
    """创建一个连接池按并发数调好的 requests.Session。

    原先用 urllib.request.urlopen, 每个用户都要重新完成一次 TCP + TLS 握手;
    跨洋链路上单次握手就是好几个 RTT, 批量创建时这部分开销很可观。
    换成带连接池的 Session 后, 同一批用户复用同一条 TLS 连接。

    调用方负责 close(), 或者用 with 语句。
    """
    sess = requests.Session()
    pool = max(concurrency, 10)
    adapter = HTTPAdapter(pool_connections=pool, pool_maxsize=pool, max_retries=0)
    sess.mount("https://", adapter)
    return sess


# 未显式传入 http session 时用的兜底实例（命令行脚本、单发调用场景）
_default_http: Optional["requests.Session"] = None


def _get_default_http() -> "requests.Session":
    global _default_http
    if _default_http is None:
        _default_http = new_http_session()
    return _default_http

# 从响应里找密码的候选字段
_PASSWORD_FIELDS = [
    "Password", "password", "OneTimePassword", "oneTimePassword",
    "TemporaryPassword", "temporaryPassword", "NewPassword", "newPassword",
]
# 正则兜底: 8-64 位、含大小写数字符号的字符串
_PW_RE = re.compile(r"[A-Za-z0-9~!@#$%^&*_\-+=`|(){}\[\]:;\"'<>,.?/\\]{8,64}")


def generate_otp(
    session,
    region: str,
    user_id: str,
    identity_store_id: str,
    http: Optional["requests.Session"] = None,
) -> str:
    """为指定用户生成一次性密码并返回。

    Parameters
    ----------
    session:              boto3.Session, 需含有效凭证
    region:               Identity Center 所在区域, 如 us-east-1
    user_id:              目标用户的 UserId (来自 identitystore:CreateUser 返回)
    identity_store_id:    Identity Store ID, 如 d-90661f32af
    http:                 可选, 复用的 requests.Session (见 new_http_session);
                          批量调用时传入可省掉每次的 TLS 握手

    Returns
    -------
    str  一次性密码明文

    Raises
    ------
    RuntimeError  调用失败或未能从响应中解析出密码
    """
    endpoint = f"https://identitystore.{region}.amazonaws.com/"
    body = json.dumps({
        "UserId": user_id,
        "PasswordMode": "OTP",
        "IdentityStoreId": identity_store_id,
    })
    payload_bytes = body.encode("utf-8")

    aws_req = AWSRequest(
        method="POST",
        url=endpoint,
        data=payload_bytes,
        headers={
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "SWBUPService.UpdatePassword",
        },
    )
    creds = session.get_credentials()
    if creds is None:
        raise RuntimeError("未找到 AWS 凭证")
    SigV4Auth(
        creds.get_frozen_credentials(), "userpool", region
    ).add_auth(aws_req)

    cli = http or _get_default_http()
    resp = cli.post(endpoint, data=payload_bytes,
                    headers=dict(aws_req.headers), timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
    raw = resp.text

    payload: Any = {}
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {"_raw": raw}

    return _extract_password(payload)


def _extract_password(payload: Any) -> str:
    """从响应 JSON 中递归查找密码字段, 失败时用正则兜底。"""
    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, str) and k in _PASSWORD_FIELDS and _looks_like_password(v):
                    return v
                found = walk(v)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = walk(item)
                if found:
                    return found
        return ""

    hit = walk(payload)
    if hit:
        return hit

    # 正则兜底: 从整段 JSON 文本里挑符合复杂度的最长串
    text = json.dumps(payload, ensure_ascii=False)
    best = ""
    for tok in _PW_RE.findall(text):
        if (_looks_like_password(tok) and len(tok) > len(best)):
            best = tok
    if best:
        return best

    raise RuntimeError(
        "接口调用成功但未能从响应中解析出密码。"
        f"响应内容(节选): {str(payload)[:300]}\n"
        "请把响应内容告知开发者, 以便补充字段名。"
    )


def _looks_like_password(s: str) -> bool:
    if len(s) < 8 or set(s) <= {"*", "•", "·", "●"}:
        return False
    return (
        any(c.islower() for c in s)
        and any(c.isupper() for c in s)
        and any(c.isdigit() for c in s)
        and any(not c.isalnum() for c in s)
    )
