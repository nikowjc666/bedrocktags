#!/usr/bin/env python3
"""
测试 q:CreateAssignment 订阅分配是否成功。
使用方法：在 .venv 环境下运行，填入真实的 AK/SK 和 user_id。

python _test_subscribe.py --ak AKIA... --sk ... --region us-east-1 --user-id <UserId> --plan pro
"""
import argparse, json, uuid, sys
import botocore.auth, botocore.awsrequest
import urllib.request, urllib.error
import boto3


def kiro_request(session, region, method, path, payload=None):
    import json as _json
    url = f"https://q.{region}.amazonaws.com{path}"
    body = _json.dumps(payload).encode() if payload else b""
    creds = session.get_credentials().get_frozen_credentials()
    req_obj = botocore.awsrequest.AWSRequest(
        method=method, url=url, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    botocore.auth.SigV4Auth(creds, "q", region).add_auth(req_obj)
    prepared = req_obj.prepare()
    req = urllib.request.Request(
        url=prepared.url,
        data=prepared.body if isinstance(prepared.body, bytes) else (prepared.body or b""),
        headers=dict(prepared.headers), method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            print(f"[OK] HTTP {resp.status}")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode(errors="replace")
        print(f"[ERROR] HTTP {e.code}: {body_txt}")
        return None


PLAN_MAP = {
    "pro":     "Q_DEVELOPER_STANDALONE_PRO",
    "pro_plus":"Q_DEVELOPER_STANDALONE_PRO_PLUS",
    "pro_max": "Q_DEVELOPER_STANDALONE_PRO_MAX",
    "power":   "Q_DEVELOPER_STANDALONE_POWER",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ak", required=True)
    p.add_argument("--sk", required=True)
    p.add_argument("--tok", default=None)
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--user-id", required=True, help="Identity Store UserId")
    p.add_argument("--plan", default="pro", choices=list(PLAN_MAP))
    p.add_argument("--group-id", default=None, help="如果要测试组订阅填此项")
    args = p.parse_args()

    session = boto3.Session(
        aws_access_key_id=args.ak,
        aws_secret_access_key=args.sk,
        aws_session_token=args.tok,
        region_name=args.region,
    )

    sub_type = PLAN_MAP[args.plan]
    principal_id   = args.group_id or args.user_id
    principal_type = "GROUP" if args.group_id else "USER"

    payload = {
        "principal": {"type": principal_type, "id": principal_id},
        "subscriptionType": sub_type,
        "clientToken": str(uuid.uuid4()),
    }

    print(f"Calling q:CreateAssignment")
    print(f"  Endpoint : https://q.{args.region}.amazonaws.com/CreateAssignment")
    print(f"  Payload  : {json.dumps(payload, indent=2)}")
    print()

    result = kiro_request(session, args.region, "POST", "/CreateAssignment", payload)
    if result is not None:
        print("Response:", json.dumps(result, indent=2))
    else:
        print("Request failed - see error above")


if __name__ == "__main__":
    main()
