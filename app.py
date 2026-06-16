"""AWS Bedrock Inference Profile 管理工具"""
import json
import boto3
import botocore
from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
from flask_cors import CORS
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
CORS(app)

REGIONS = [
    "us-east-1", "us-east-2", "us-west-2", "us-west-1",
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1",
    "eu-central-2", "eu-north-1", "eu-south-1", "eu-south-2",
    "ap-east-1", "ap-south-1", "ap-south-2",
    "ap-southeast-1", "ap-southeast-2", "ap-southeast-3", "ap-southeast-4",
    "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
    "sa-east-1", "ca-central-1", "me-south-1", "me-central-1",
    "af-south-1", "il-central-1",
]

# 固定 Claude 4+ 版本（无需每次从 AWS 加载）
# sources: 系统 Inference Profile ID，用于 copyFrom（新版模型不支持直接用 foundation model）
CLAUDE_VERSIONS = [
    {
        "id": "anthropic.claude-fable-5",
        "label": "Claude Fable 5",
        "sources": {
            "us": "us.anthropic.claude-fable-5",
            "eu": "eu.anthropic.claude-fable-5",
            "global": "global.anthropic.claude-fable-5",
        },
    },
    {
        "id": "anthropic.claude-opus-4-8",
        "label": "Claude Opus 4.8",
        "sources": {"global": "global.anthropic.claude-opus-4-8"},
    },
    {
        "id": "anthropic.claude-opus-4-7",
        "label": "Claude Opus 4.7",
        "sources": {"global": "global.anthropic.claude-opus-4-7"},
    },
    {
        "id": "anthropic.claude-opus-4-6-v1",
        "label": "Claude Opus 4.6",
        "sources": {
            "us": "us.anthropic.claude-opus-4-6-v1",
            "eu": "eu.anthropic.claude-opus-4-6-v1",
            "global": "global.anthropic.claude-opus-4-6-v1",
        },
    },
    {
        "id": "anthropic.claude-opus-4-5-20251101-v1:0",
        "label": "Claude Opus 4.5",
        "sources": {"global": "global.anthropic.claude-opus-4-5-20251101-v1:0"},
    },
    {
        "id": "anthropic.claude-sonnet-4-6",
        "label": "Claude Sonnet 4.6",
        "sources": {
            "us": "us.anthropic.claude-sonnet-4-6",
            "eu": "eu.anthropic.claude-sonnet-4-6",
            "global": "global.anthropic.claude-sonnet-4-6",
        },
    },
    {
        "id": "anthropic.claude-sonnet-4-5-20250929-v1:0",
        "label": "Claude Sonnet 4.5",
        "sources": {
            "us": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "eu": "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "global": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        },
    },
    {
        "id": "anthropic.claude-haiku-4-5-20251001-v1:0",
        "label": "Claude Haiku 4.5",
        "sources": {
            "us": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
            "eu": "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
            "global": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        },
    },
    {
        "id": "anthropic.claude-opus-4-20250514-v1:0",
        "label": "Claude Opus 4",
        "sources": {
            "us": "us.anthropic.claude-opus-4-20250514-v1:0",
            "eu": "eu.anthropic.claude-opus-4-20250514-v1:0",
            "global": "global.anthropic.claude-opus-4-20250514-v1:0",
        },
    },
    {
        "id": "anthropic.claude-sonnet-4-20250514-v1:0",
        "label": "Claude Sonnet 4",
        "sources": {
            "us": "us.anthropic.claude-sonnet-4-20250514-v1:0",
            "eu": "eu.anthropic.claude-sonnet-4-20250514-v1:0",
            "global": "global.anthropic.claude-sonnet-4-20250514-v1:0",
        },
    },
]

CLAUDE_BY_ID = {v["id"]: v for v in CLAUDE_VERSIONS}

# Claude 4.5 及以上（排除 4.0 初代）
CLAUDE_40_IDS = {
    "anthropic.claude-opus-4-20250514-v1:0",
    "anthropic.claude-sonnet-4-20250514-v1:0",
}
CLAUDE_45_PLUS_VERSIONS = [v for v in CLAUDE_VERSIONS if v["id"] not in CLAUDE_40_IDS]
CLAUDE_45_BY_ID = {v["id"]: v for v in CLAUDE_45_PLUS_VERSIONS}


def _is_claude_45_plus(model_id):
    return model_id in CLAUDE_45_BY_ID


def _model_slug(model_id):
    return model_id.replace("anthropic.", "").replace(":", "-").replace(".", "-")[:36]


def _make_profile_name(prefix, region, model_id, multi):
    """生成 Inference Profile 名称。
    
    格式：claude-{版本}-auto{月日}-{前缀}
    例如：claude-sonnet-45-auto0615-myprofile
    """
    # 从 model_id 获取版本标签
    ver = CLAUDE_45_BY_ID.get(model_id) or CLAUDE_BY_ID.get(model_id) or {}
    label = (ver.get("label") or model_id).lower().replace(" ", "-").replace(".", "")
    
    # 月份日期（如 0615）
    auto_date = datetime.now().strftime("%m%d")
    
    # 组装名称：claude-{版本}-auto{月日}-{前缀}
    parts = ["claude", label, f"auto{auto_date}"]
    if prefix:
        parts.append(prefix)
    name = "-".join(parts)
    return name[:64]

US_GEO_REGIONS = {
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1", "sa-east-1",
}
EU_GEO_REGIONS = {
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", "eu-central-2",
    "eu-north-1", "eu-south-1", "eu-south-2", "il-central-1",
    "me-central-1", "me-south-1", "af-south-1",
}
AP_NORTHEAST = {"ap-northeast-1", "ap-northeast-2", "ap-northeast-3"}


def _foundation_model_arn(region, model_id):
    return f"arn:aws:bedrock:{region}::foundation-model/{model_id}"


def _inference_profile_arn(region, profile_id):
    return f"arn:aws:bedrock:{region}::inference-profile/{profile_id}"


def _region_geo(region):
    if region in US_GEO_REGIONS:
        return "us"
    if region in EU_GEO_REGIONS:
        return "eu"
    if region in AP_NORTHEAST:
        return "jp"
    return "global"


def _build_model_source_index(br, region):
    """从 AWS 列出系统 Inference Profile，建立 model_id -> copyFrom ARN 索引"""
    geo = _region_geo(region)
    index = {}
    paginator = br.get_paginator("list_inference_profiles")
    for page in paginator.paginate(typeEquals="SYSTEM_DEFINED"):
        for summary in page.get("inferenceProfileSummaries", []):
            pid = summary.get("inferenceProfileId", "")
            if "anthropic" not in pid:
                continue
            try:
                detail = br.get_inference_profile(inferenceProfileIdentifier=pid)
                profile = detail.get("inferenceProfile", detail)
                parn = profile.get("inferenceProfileArn", "")
                if not parn:
                    continue
                model_ids = set()
                in_region = False
                for m in profile.get("models", []):
                    arn = m.get("modelArn", "")
                    if f":bedrock:{region}:" in arn:
                        in_region = True
                    if "/foundation-model/" in arn:
                        model_ids.add(arn.split("/foundation-model/", 1)[1])
                priority = 0
                if pid.startswith(f"{geo}."):
                    priority = 3
                elif pid.startswith("global."):
                    priority = 2
                elif in_region:
                    priority = 1
                for mid in model_ids:
                    prev = index.get(mid)
                    if prev is None or priority > prev[0]:
                        index[mid] = (priority, parn)
            except Exception:
                continue
    return {k: v[1] for k, v in index.items()}


def _resolve_copy_from(br, region, ver, index=None):
    """解析 create_inference_profile 的 copyFrom 来源 ARN"""
    model_id = ver["id"]
    sources = ver.get("sources") or {}
    geo = _region_geo(region)
    for key in (geo, "global"):
        pid = sources.get(key)
        if pid:
            return _inference_profile_arn(region, pid), pid

    if index is None:
        index = _build_model_source_index(br, region)
    if model_id in index:
        return index[model_id], model_id

    try:
        resp = br.list_foundation_models(byInferenceType="ON_DEMAND")
        for m in resp.get("modelSummaries", []):
            if m.get("modelId") == model_id:
                arn = m.get("modelArn") or _foundation_model_arn(region, model_id)
                return arn, model_id
    except Exception:
        pass

    return None, None


def _creds(data):
    ak = (data.get("access_key") or "").strip()
    sk = (data.get("secret_key") or "").strip()
    user_id = (data.get("user_id") or "").strip()
    return ak, sk, user_id


def _bedrock(ak, sk, region):
    sess = boto3.Session(aws_access_key_id=ak, aws_secret_access_key=sk)
    return sess.client("bedrock", region_name=region)


def _bedrock_runtime(ak, sk, region):
    sess = boto3.Session(aws_access_key_id=ak, aws_secret_access_key=sk)
    return sess.client("bedrock-runtime", region_name=region)


def _list_resource_tags(br, resource_arn):
    try:
        resp = br.list_tags_for_resource(resourceARN=resource_arn)
        return resp.get("tags", [])
    except Exception:
        return []


def _is_claude(model_summary):
    mid = (model_summary.get("modelId") or "").lower()
    prov = (model_summary.get("providerName") or "").lower()
    name = (model_summary.get("modelName") or "").lower()
    return "claude" in mid or "anthropic" in prov or "claude" in name


def _claude_models(br):
    resp = br.list_foundation_models()
    models = []
    for m in resp.get("modelSummaries", []):
        if not _is_claude(m):
            continue
        models.append({
            "modelArn": m.get("modelArn", ""),
            "modelId": m.get("modelId", ""),
            "modelName": m.get("modelName", ""),
            "providerName": m.get("providerName", ""),
            "inputModalities": m.get("inputModalities", []),
            "outputModalities": m.get("outputModalities", []),
        })
    return models


def _verify_account(ak, sk, user_id=None):
    sess = boto3.Session(aws_access_key_id=ak, aws_secret_access_key=sk)
    sts = sess.client("sts")
    identity = sts.get_caller_identity()
    account = identity["Account"]
    arn = identity.get("Arn", "")
    if user_id and user_id != account:
        return None, f"用户 ID 不匹配，期望 {user_id}，实际账号 {account}"
    return {"account_id": account, "arn": arn}, None


def _aws_error(e):
    if isinstance(e, botocore.exceptions.ClientError):
        return f"AWS 错误: {e.response['Error']['Message']}"
    return str(e)


def _profile_summary(p, tags=None):
    summary = {
        "arn": p.get("inferenceProfileArn", ""),
        "name": p.get("inferenceProfileName", ""),
        "id": p.get("inferenceProfileId", ""),
        "status": p.get("status", ""),
        "description": p.get("description", ""),
        "type": p.get("type", ""),
        "createdAt": str(p.get("createdAt", "")),
        "updatedAt": str(p.get("updatedAt", "")),
    }
    if tags is not None:
        summary["tags"] = tags
    return summary


def _list_application_profiles(br, name_prefix=None):
    """列出 APPLICATION 类型 inference profile，可按名称前缀过滤"""
    profiles = []
    paginator = br.get_paginator("list_inference_profiles")
    for page in paginator.paginate(typeEquals="APPLICATION"):
        for p in page.get("inferenceProfileSummaries", []):
            name = p.get("inferenceProfileName", "")
            if name_prefix and not name.startswith(name_prefix):
                continue
            profiles.append(_profile_summary(p))
    return profiles



@app.route("/api/verify", methods=["POST"])
def verify():
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    if not ak or not sk:
        return jsonify({"ok": False, "error": "请填写 Access Key 和 Secret Key"}), 400
    try:
        info, err = _verify_account(ak, sk, user_id or None)
        if err:
            return jsonify({"ok": False, "error": err}), 400
        return jsonify({"ok": True, **info})
    except Exception as e:
        return jsonify({"ok": False, "error": _aws_error(e)}), 400


@app.route("/api/regions", methods=["GET"])
def regions():
    return jsonify({"ok": True, "regions": REGIONS})


@app.route("/api/claude_versions", methods=["GET"])
def claude_versions():
    return jsonify({"ok": True, "versions": CLAUDE_VERSIONS})


@app.route("/api/claude_45_versions", methods=["GET"])
def claude_45_versions():
    return jsonify({"ok": True, "versions": CLAUDE_45_PLUS_VERSIONS})


@app.route("/api/resolveclaude_models", methods=["POST"])
def resolve_claude_models():
    """解析 Claude 4.5+ 系统 Inference Profile ARN（区域 × 模型）"""
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    regions = [r.strip() for r in (data.get("regions") or []) if r and r.strip()]
    model_ids = [m.strip() for m in (data.get("model_ids") or []) if m and m.strip()]
    if not all([ak, sk]):
        return jsonify({"ok": False, "error": "请填写 AK/SK"}), 400
    if not regions:
        return jsonify({"ok": False, "error": "请至少选择一个区域"}), 400
    if not model_ids:
        return jsonify({"ok": False, "error": "请至少选择一个模型"}), 400
    invalid = [m for m in model_ids if not _is_claude_45_plus(m)]
    if invalid:
        return jsonify({"ok": False, "error": f"仅支持 Claude 4.5+，无效模型: {', '.join(invalid)}"}), 400
    try:
        if user_id:
            _, err = _verify_account(ak, sk, user_id)
            if err:
                return jsonify({"ok": False, "error": err}), 400
        results = []
        for region in regions:
            br = _bedrock(ak, sk, region)
            index = _build_model_source_index(br, region)
            for model_id in model_ids:
                ver = CLAUDE_45_BY_ID[model_id]
                arn, source_id = _resolve_copy_from(br, region, ver, index)
                if not arn:
                    results.append({
                        "region": region,
                        "model_id": model_id,
                        "model_label": ver["label"],
                        "ok": False,
                        "error": "该区域未找到可用的系统 Inference Profile",
                    })
                    continue
                try:
                    resp = br.get_inference_profile(inferenceProfileIdentifier=arn)
                    p = resp.get("inferenceProfile", resp)
                    results.append({
                        "region": region,
                        "model_id": model_id,
                        "model_label": ver["label"],
                        "profile_id": source_id or p.get("inferenceProfileId", ""),
                        "arn": p.get("inferenceProfileArn", arn),
                        "status": p.get("status", ""),
                        "type": p.get("type", ""),
                        "tags": _list_resource_tags(br, p.get("inferenceProfileArn", arn)),
                        "ok": True,
                    })
                except Exception as e:
                    results.append({
                        "region": region,
                        "model_id": model_id,
                        "model_label": ver["label"],
                        "arn": arn,
                        "ok": False,
                        "error": _aws_error(e),
                    })
        ok_cnt = sum(1 for r in results if r.get("ok"))
        return jsonify({
            "ok": True,
            "total": len(results),
            "success": ok_cnt,
            "failed": len(results) - ok_cnt,
            "results": results,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": _aws_error(e)}), 500


@app.route("/api/queryclaude_models", methods=["POST"])
def query_claude_models():
    """根据 AK/SK/用户 ID 查询账号可用的 Claude 模型"""
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    region = (data.get("region") or "us-east-1").strip()
    if not all([ak, sk, user_id]):
        return jsonify({"ok": False, "error": "请填写 AK、SK 和用户 ID（账号 ID）"}), 400
    try:
        info, err = _verify_account(ak, sk, user_id)
        if err:
            return jsonify({"ok": False, "error": err}), 400
        br = _bedrock(ak, sk, region)
        models = _claude_models(br)
        return jsonify({
            "ok": True,
            "account_id": info["account_id"],
            "region": region,
            "count": len(models),
            "models": models,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": _aws_error(e)}), 400


@app.route("/api/list_foundation_models", methods=["POST"])
def list_foundation_models():
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    region = (data.get("region") or "").strip()
    if not all([ak, sk, region]):
        return jsonify({"ok": False, "error": "参数不完整"}), 400
    try:
        if user_id:
            _, err = _verify_account(ak, sk, user_id)
            if err:
                return jsonify({"ok": False, "error": err}), 400
        br = _bedrock(ak, sk, region)
        return jsonify({"ok": True, "models": _claude_models(br)})
    except Exception as e:
        return jsonify({"ok": False, "error": _aws_error(e)}), 400


@app.route("/api/list_profiles", methods=["POST"])
def list_profiles():
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    region = (data.get("region") or "").strip()
    if not all([ak, sk, region]):
        return jsonify({"ok": False, "error": "参数不完整"}), 400
    try:
        if user_id:
            _, err = _verify_account(ak, sk, user_id)
            if err:
                return jsonify({"ok": False, "error": err}), 400
        br = _bedrock(ak, sk, region)
        profiles = []
        paginator = br.get_paginator("list_inference_profiles")
        for page in paginator.paginate(typeEquals="APPLICATION"):
            for p in page.get("inferenceProfileSummaries", []):
                profiles.append(_profile_summary(p))
        return jsonify({"ok": True, "profiles": profiles})
    except Exception as e:
        return jsonify({"ok": False, "error": _aws_error(e)}), 400


@app.route("/api/get_profile", methods=["POST"])
def get_profile():
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    region = (data.get("region") or "").strip()
    profile_id = (data.get("inference_profile_id") or data.get("inference_profile_arn") or "").strip()
    if not all([ak, sk, region, profile_id]):
        return jsonify({"ok": False, "error": "参数不完整"}), 400
    try:
        if user_id:
            _, err = _verify_account(ak, sk, user_id)
            if err:
                return jsonify({"ok": False, "error": err}), 400
        br = _bedrock(ak, sk, region)
        resp = br.get_inference_profile(inferenceProfileIdentifier=profile_id)
        p = resp.get("inferenceProfile", resp)
        tags = []
        try:
            tag_resp = br.list_tags_for_resource(resourceARN=p.get("inferenceProfileArn", profile_id))
            tags = tag_resp.get("tags", [])
        except Exception:
            pass
        return jsonify({
            "ok": True,
            "profile": _profile_summary(p),
            "modelSource": p.get("models", p.get("modelSource", {})),
            "tags": tags,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": _aws_error(e)}), 400


@app.route("/api/create_profile", methods=["POST"])
def create_profile():
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    region = (data.get("region") or "").strip()
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    model_source_arn = (data.get("model_source_arn") or "").strip()
    model_id = (data.get("model_id") or "").strip()
    tags_raw = data.get("tags") or {}
    if not all([ak, sk, region, name]):
        return jsonify({"ok": False, "error": "请填写必要参数"}), 400
    if not model_source_arn and not model_id:
        return jsonify({"ok": False, "error": "请选择模型"}), 400
    try:
        if user_id:
            _, err = _verify_account(ak, sk, user_id)
            if err:
                return jsonify({"ok": False, "error": err}), 400
        br = _bedrock(ak, sk, region)
        if not model_source_arn and model_id:
            ver = CLAUDE_BY_ID.get(model_id)
            if ver:
                model_source_arn, _ = _resolve_copy_from(br, region, ver)
            else:
                model_source_arn = _foundation_model_arn(region, model_id)
        if not model_source_arn:
            return jsonify({
                "ok": False,
                "error": "无法解析模型来源，请确认该区域已开通该 Claude 模型",
            }), 400
        params = {
            "inferenceProfileName": name,
            "modelSource": {"copyFrom": model_source_arn},
        }
        if description:
            params["description"] = description
        if tags_raw:
            params["tags"] = [{"key": k, "value": v} for k, v in tags_raw.items()]
        resp = br.create_inference_profile(**params)
        return jsonify({"ok": True, "result": {
            "inferenceProfileArn": resp.get("inferenceProfileArn", ""),
            "inferenceProfileId": resp.get("inferenceProfileId", ""),
            "status": resp.get("status", ""),
        }})
    except Exception as e:
        return jsonify({"ok": False, "error": _aws_error(e)}), 400


@app.route("/api/batch_create_profiles", methods=["POST"])
def batch_create_profiles():
    """区域 × Claude 4.5+ 模型 笛卡尔积批量创建 Inference Profile 并打标签"""
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    regions = [r.strip() for r in (data.get("regions") or []) if r and r.strip()]
    model_ids = [m.strip() for m in (data.get("model_ids") or []) if m and m.strip()]
    name_prefix = (data.get("name_prefix") or data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    tags_raw = data.get("tags") or {}
    claude_45_only = data.get("claude_45_only", True)

    if not all([ak, sk]):
        return jsonify({"ok": False, "error": "请填写 AK/SK"}), 400
    if not name_prefix:
        return jsonify({"ok": False, "error": "请填写配置名称"}), 400
    if not regions:
        return jsonify({"ok": False, "error": "请至少选择一个区域"}), 400
    if not model_ids:
        return jsonify({"ok": False, "error": "请至少选择一个 Claude 版本"}), 400

    if claude_45_only:
        invalid = [m for m in model_ids if not _is_claude_45_plus(m)]
        if invalid:
            return jsonify({
                "ok": False,
                "error": f"仅支持 Claude 4.5+，无效模型: {', '.join(invalid)}",
            }), 400

    total = len(regions) * len(model_ids)
    multi = len(regions) > 1 or len(model_ids) > 1
    tag_list = [{"key": k, "value": v} for k, v in tags_raw.items()] if tags_raw else []
    results = []

    try:
        if user_id:
            _, err = _verify_account(ak, sk, user_id)
            if err:
                return jsonify({"ok": False, "error": err}), 400

        for region in regions:
            br = _bedrock(ak, sk, region)
            source_index = _build_model_source_index(br, region)
            for model_id in model_ids:
                ver = (CLAUDE_45_BY_ID if claude_45_only else CLAUDE_BY_ID).get(model_id)
                if not ver:
                    results.append({
                        "region": region,
                        "model_id": model_id,
                        "name": "",
                        "ok": False,
                        "error": "未知或不支持的模型版本",
                    })
                    continue
                name = _make_profile_name(name_prefix, region, model_id, multi)
                arn, source_id = _resolve_copy_from(br, region, ver, source_index)
                if not arn:
                    results.append({
                        "region": region,
                        "model_id": model_id,
                        "model_label": ver["label"],
                        "name": name,
                        "ok": False,
                        "error": "该区域未找到可用的系统 Inference Profile",
                    })
                    continue
                try:
                    params = {
                        "inferenceProfileName": name,
                        "modelSource": {"copyFrom": arn},
                    }
                    if description:
                        params["description"] = description
                    if tag_list:
                        params["tags"] = tag_list
                    resp = br.create_inference_profile(**params)
                    profile_arn = resp.get("inferenceProfileArn", "")
                    results.append({
                        "region": region,
                        "model_id": model_id,
                        "model_label": ver["label"],
                        "name": name,
                        "ok": True,
                        "copyFrom": source_id or arn,
                        "inferenceProfileArn": profile_arn,
                        "inferenceProfileId": resp.get("inferenceProfileId", ""),
                        "status": resp.get("status", ""),
                        "tags": tags_raw,
                    })
                except Exception as e:
                    results.append({
                        "region": region,
                        "model_id": model_id,
                        "model_label": ver["label"],
                        "name": name,
                        "ok": False,
                        "error": _aws_error(e),
                    })

        ok_cnt = sum(1 for r in results if r["ok"])
        return jsonify({
            "ok": True,
            "total": total,
            "success": ok_cnt,
            "failed": total - ok_cnt,
            "results": results,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": _aws_error(e)}), 500


@app.route("/api/batch_create_stream", methods=["POST"])
def batch_create_stream():
    """流式批量创建 —— 区域间并发，每完成一个立即推送 SSE。

    优化：
    1. _resolve_copy_from 优先走硬编码 sources，绝大多数模型直接命中，
       完全跳过 _build_model_source_index 的 N 次 get_inference_profile 调用。
    2. 各区域用 ThreadPoolExecutor 并发执行，IO 等待不再串行叠加。
    3. fallback 时才懒加载 source_index，且同一区域只查一次。
    """
    import queue
    from concurrent.futures import ThreadPoolExecutor, as_completed

    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    regions        = [r.strip() for r in (data.get("regions")    or []) if r and r.strip()]
    model_ids      = [m.strip() for m in (data.get("model_ids")  or []) if m and m.strip()]
    name_prefix    = (data.get("name_prefix") or data.get("name") or "").strip()
    description    = (data.get("description") or "").strip()
    tags_raw       = data.get("tags") or {}
    claude_45_only = data.get("claude_45_only", True)

    def _err(msg):
        return Response(
            f"data: {json.dumps({'type':'error','error':msg}, ensure_ascii=False)}\n\n",
            mimetype="text/event-stream", status=400,
        )

    if not all([ak, sk]):   return _err("请填写 AK/SK")
    if not name_prefix:     return _err("请填写配置名称")
    if not regions:         return _err("请至少选择一个区域")
    if not model_ids:       return _err("请至少选择一个 Claude 版本")
    if claude_45_only:
        invalid = [m for m in model_ids if not _is_claude_45_plus(m)]
        if invalid:         return _err(f"仅支持 Claude 4.5+，无效模型: {', '.join(invalid)}")

    total    = len(regions) * len(model_ids)
    multi    = total > 1
    tag_list = [{"key": k, "value": v} for k, v in tags_raw.items()] if tags_raw else []
    model_lookup = CLAUDE_45_BY_ID if claude_45_only else CLAUDE_BY_ID

    def _create_region(region):
        """在一个区域里依次创建所有模型，返回 list[row_dict]。"""
        rows = []
        try:
            br = _bedrock(ak, sk, region)
        except Exception as e:
            for mid in model_ids:
                ver = model_lookup.get(mid) or {}
                rows.append({
                    "region": region, "model_id": mid,
                    "model_label": ver.get("label", mid),
                    "name": _make_profile_name(name_prefix, region, mid, multi),
                    "ok": False, "error": _aws_error(e),
                })
            return rows

        # 懒加载：只有 sources 命中失败时才查一次
        _index_cache = {}

        def _get_index():
            if "v" not in _index_cache:
                try:
                    _index_cache["v"] = _build_model_source_index(br, region)
                except Exception:
                    _index_cache["v"] = {}
            return _index_cache["v"]

        for model_id in model_ids:
            ver = model_lookup.get(model_id)
            if not ver:
                rows.append({
                    "region": region, "model_id": model_id, "model_label": model_id,
                    "name": "", "ok": False, "error": "未知或不支持的模型版本",
                })
                continue

            name = _make_profile_name(name_prefix, region, model_id, multi)

            # 先尝试 sources 直接命中（不触发 AWS API）
            sources = ver.get("sources") or {}
            geo     = _region_geo(region)
            arn = source_id = None
            for key in (geo, "global"):
                pid = sources.get(key)
                if pid:
                    arn       = _inference_profile_arn(region, pid)
                    source_id = pid
                    break

            # fallback：查 AWS 系统 profile 索引
            if not arn:
                idx = _get_index()
                if model_id in idx:
                    arn = source_id = idx[model_id]

            if not arn:
                rows.append({
                    "region": region, "model_id": model_id,
                    "model_label": ver["label"], "name": name,
                    "ok": False,
                    "error": "该区域未找到可用的系统 Inference Profile",
                })
                continue

            try:
                params = {"inferenceProfileName": name, "modelSource": {"copyFrom": arn}}
                if description:
                    params["description"] = description
                if tag_list:
                    params["tags"] = tag_list
                resp        = br.create_inference_profile(**params)
                profile_arn = resp.get("inferenceProfileArn", "")
                rows.append({
                    "region": region, "model_id": model_id,
                    "model_label": ver["label"], "name": name,
                    "ok": True,
                    "copyFrom": source_id or arn,
                    "inferenceProfileArn": profile_arn,
                    "inferenceProfileId": resp.get("inferenceProfileId", ""),
                    "status": resp.get("status", ""),
                    "tags": tags_raw,
                })
            except Exception as e:
                rows.append({
                    "region": region, "model_id": model_id,
                    "model_label": ver["label"], "name": name,
                    "ok": False, "error": _aws_error(e),
                })
        return rows

    def _generate():
        yield f"data: {json.dumps({'type':'start','total':total}, ensure_ascii=False)}\n\n"

        try:
            if user_id:
                _, err = _verify_account(ak, sk, user_id)
                if err:
                    yield f"data: {json.dumps({'type':'error','error':err}, ensure_ascii=False)}\n\n"
                    return
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','error':_aws_error(e)}, ensure_ascii=False)}\n\n"
            return

        done    = 0
        # 并发数：区域数，最多 10 个线程（避免连接数爆炸）
        workers = min(len(regions), 10)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_create_region, r): r for r in regions}
            for future in as_completed(futures):
                try:
                    rows = future.result()
                except Exception as e:
                    region = futures[future]
                    rows = [{"region": region, "model_id": mid,
                             "model_label": model_lookup.get(mid, {}).get("label", mid),
                             "name": _make_profile_name(name_prefix, region, mid, multi),
                             "ok": False, "error": _aws_error(e)}
                            for mid in model_ids]

                for row in rows:
                    done += 1
                    row.update({"type": "item", "done": done, "total": total})
                    yield f"data: {json.dumps(row, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type':'done','total':total,'done':done}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/update_profile", methods=["POST"])
def update_profile():
    """更新配置标签（Bedrock 不支持直接修改名称/模型，需删除后重建）"""
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    region = (data.get("region") or "").strip()
    profile_arn = (data.get("inference_profile_arn") or "").strip()
    tags_raw = data.get("tags") or {}
    remove_tag_keys = data.get("remove_tag_keys") or []
    if not all([ak, sk, region, profile_arn]):
        return jsonify({"ok": False, "error": "参数不完整"}), 400
    try:
        if user_id:
            _, err = _verify_account(ak, sk, user_id)
            if err:
                return jsonify({"ok": False, "error": err}), 400
        br = _bedrock(ak, sk, region)
        if remove_tag_keys:
            br.untag_resource(resourceARN=profile_arn, tagKeys=remove_tag_keys)
        if tags_raw:
            br.tag_resource(
                resourceARN=profile_arn,
                tags=[{"key": k, "value": v} for k, v in tags_raw.items()],
            )
        return jsonify({"ok": True, "message": "标签已更新"})
    except Exception as e:
        return jsonify({"ok": False, "error": _aws_error(e)}), 400


@app.route("/api/delete_profile", methods=["POST"])
def delete_profile():
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    region = (data.get("region") or "").strip()
    profile_id = (data.get("inference_profile_arn") or data.get("inference_profile_id") or "").strip()
    if not all([ak, sk, region, profile_id]):
        return jsonify({"ok": False, "error": "参数不完整"}), 400
    try:
        if user_id:
            _, err = _verify_account(ak, sk, user_id)
            if err:
                return jsonify({"ok": False, "error": err}), 400
        br = _bedrock(ak, sk, region)
        br.delete_inference_profile(inferenceProfileIdentifier=profile_id)
        return jsonify({"ok": True, "message": "已删除"})
    except Exception as e:
        return jsonify({"ok": False, "error": _aws_error(e)}), 400


@app.route("/api/batch_list_profiles", methods=["POST"])
def batch_list_profiles():
    """多区域列出 APPLICATION inference profile（可按名称前缀过滤）"""
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    regions = [r.strip() for r in (data.get("regions") or []) if r and r.strip()]
    name_prefix = (data.get("name_prefix") or "").strip()
    if not all([ak, sk]):
        return jsonify({"ok": False, "error": "请填写 AK/SK"}), 400
    if not regions:
        return jsonify({"ok": False, "error": "请至少选择一个区域"}), 400
    try:
        if user_id:
            _, err = _verify_account(ak, sk, user_id)
            if err:
                return jsonify({"ok": False, "error": err}), 400
        profiles = []
        for region in regions:
            br = _bedrock(ak, sk, region)
            for p in _list_application_profiles(br, name_prefix or None):
                profiles.append({**p, "region": region})
        return jsonify({"ok": True, "total": len(profiles), "profiles": profiles})
    except Exception as e:
        return jsonify({"ok": False, "error": _aws_error(e)}), 400


@app.route("/api/batch_delete_profiles", methods=["POST"])
def batch_delete_profiles():
    """批量删除 inference profile（指定列表，或按区域 × 名称前缀扫描删除）"""
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    regions = [r.strip() for r in (data.get("regions") or []) if r and r.strip()]
    name_prefix = (data.get("name_prefix") or "").strip()
    items = data.get("profiles") or []

    if not all([ak, sk]):
        return jsonify({"ok": False, "error": "请填写 AK/SK"}), 400

    targets = []
    if items:
        for it in items:
            region = (it.get("region") or "").strip()
            pid = (it.get("inference_profile_arn") or it.get("inference_profile_id") or it.get("arn") or "").strip()
            if region and pid:
                targets.append({"region": region, "id": pid, "name": it.get("name", "")})
    elif name_prefix and regions:
        if len(name_prefix) < 2:
            return jsonify({"ok": False, "error": "名称前缀至少 2 个字符，避免误删"}), 400
        for region in regions:
            br = _bedrock(ak, sk, region)
            for p in _list_application_profiles(br, name_prefix):
                targets.append({
                    "region": region,
                    "id": p.get("arn") or p.get("id", ""),
                    "name": p.get("name", ""),
                })
    else:
        return jsonify({"ok": False, "error": "请指定要删除的配置列表，或填写名称前缀并选择区域"}), 400

    if not targets:
        return jsonify({"ok": True, "total": 0, "success": 0, "failed": 0, "results": [], "message": "未找到匹配的配置"})

    try:
        if user_id:
            _, err = _verify_account(ak, sk, user_id)
            if err:
                return jsonify({"ok": False, "error": err}), 400

        results = []
        clients = {}
        for t in targets:
            region = t["region"]
            pid = t["id"]
            if region not in clients:
                clients[region] = _bedrock(ak, sk, region)
            br = clients[region]
            try:
                br.delete_inference_profile(inferenceProfileIdentifier=pid)
                results.append({
                    "region": region,
                    "name": t.get("name", ""),
                    "inference_profile_arn": pid,
                    "ok": True,
                })
            except Exception as e:
                results.append({
                    "region": region,
                    "name": t.get("name", ""),
                    "inference_profile_arn": pid,
                    "ok": False,
                    "error": _aws_error(e),
                })

        ok_cnt = sum(1 for r in results if r["ok"])
        return jsonify({
            "ok": True,
            "total": len(results),
            "success": ok_cnt,
            "failed": len(results) - ok_cnt,
            "results": results,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": _aws_error(e)}), 500


@app.route("/api/tag_profiles", methods=["POST"])
def tag_profiles():
    """批量标签操作：支持添加/删除标签"""
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    region = (data.get("region") or "").strip()
    resource_arns = data.get("resource_arns", [])
    tags_raw = data.get("tags", {})
    remove_tag_keys = data.get("remove_tag_keys", [])
    if not all([ak, sk, region]):
        return jsonify({"ok": False, "error": "参数不完整"}), 400
    if not resource_arns:
        return jsonify({"ok": False, "error": "请选择配置"}), 400
    if not tags_raw and not remove_tag_keys:
        return jsonify({"ok": False, "error": "请添加或者选择要删除的标签"}), 400
    tag_list = [{"key": k, "value": v} for k, v in tags_raw.items()]
    results = []
    try:
        if user_id:
            _, err = _verify_account(ak, sk, user_id)
            if err:
                return jsonify({"ok": False, "error": err}), 400
        br = _bedrock(ak, sk, region)
        for arn in resource_arns:
            try:
                if remove_tag_keys:
                    br.untag_resource(resourceARN=arn, tagKeys=remove_tag_keys)
                if tag_list:
                    br.tag_resource(resourceARN=arn, tags=tag_list)
                results.append({"arn": arn, "ok": True})
            except Exception as e:
                results.append({"arn": arn, "ok": False, "error": str(e)})
        ok_cnt = sum(1 for r in results if r["ok"])
        fail_cnt = len(results) - ok_cnt
        return jsonify({
            "ok": True,
            "total": len(results),
            "success": ok_cnt,
            "failed": fail_cnt,
            "details": results,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/test_profile", methods=["POST"])
def test_profile():
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    region = (data.get("region") or "").strip()
    profile_arn = (data.get("inference_profile_arn") or "").strip()
    do_invoke = bool(data.get("invoke", True))
    if not all([ak, sk, region, profile_arn]):
        return jsonify({"ok": False, "error": "参数不完整"}), 400
    try:
        if user_id:
            _, err = _verify_account(ak, sk, user_id)
            if err:
                return jsonify({"ok": False, "error": err}), 400
        br = _bedrock(ak, sk, region)
        resp = br.get_inference_profile(inferenceProfileIdentifier=profile_arn)
        p = resp.get("inferenceProfile", resp)
        status = p.get("status", "UNKNOWN")
        profile_arn = p.get("inferenceProfileArn", profile_arn)
        result = {
            "ok": True,
            "available": status == "ACTIVE",
            "status": status,
            "inferenceProfileId": p.get("inferenceProfileId", ""),
            "inferenceProfileArn": profile_arn,
            "name": p.get("inferenceProfileName", ""),
            "type": p.get("type", ""),
            "invoke_ok": None,
            "invoke_error": None,
        }
        if do_invoke:
            if status != "ACTIVE":
                # Profile 本身不 ACTIVE，无需尝试调用
                result["invoke_ok"] = False
                result["invoke_error"] = f"Profile 状态为 {status}，无法调用"
                result["available"] = False
            else:
                try:
                    rt = _bedrock_runtime(ak, sk, region)
                    invoke_resp = rt.converse(
                        modelId=profile_arn,
                        messages=[{"role": "user", "content": [{"text": "hi"}]}],
                        inferenceConfig={"maxTokens": 8, "temperature": 0},
                    )
                    text = ""
                    for block in invoke_resp.get("output", {}).get("message", {}).get("content", []):
                        if "text" in block:
                            text += block["text"]
                    result["invoke_ok"] = True
                    result["invoke_preview"] = (text or "")[:80]
                    result["available"] = True   # 调用成功才算真正可用
                except Exception as e:
                    result["invoke_ok"] = False
                    result["invoke_error"] = _aws_error(e)
                    result["available"] = False  # 调用失败 = 不可用
        return jsonify(result)
    except botocore.exceptions.ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("ResourceNotFoundException", "NotFoundException"):
            return jsonify({"ok": True, "available": False, "status": "NOT_FOUND",
                            "error": "ARN 不存在或无访问权限"})
        return jsonify({"ok": False, "available": False, "error": _aws_error(e)})
    except Exception as e:
        return jsonify({"ok": False, "available": False, "error": _aws_error(e)})



@app.route("/api/export_excel", methods=["POST"])
def export_excel():
    """导出批量创建结果为格式化 Excel，带单元格合并。

    列顺序：
      A  AWS账户ID  ─ 全部数据行合并（同一账户）
      B  登录URL    ─ 全部数据行合并
      C  账号       ─ 全部数据行合并（留空，用户填）
      D  密码       ─ 全部数据行合并（留空，用户填）
      E  模型类型   ─ 同一模型的连续行合并
      F  区域       ─ 每行独立
      G  模型QRN    ─ 每行独立
      H  标签       ─ 连续相同标签的行合并
    """
    data = request.get_json() or {}
    raw_results = data.get("results", [])
    account_id  = (data.get("account_id") or "").strip()

    if not raw_results:
        return jsonify({"ok": False, "error": "无数据可导出"}), 400

    # ── 预处理：计算每行的展示值 ──────────────────────────────
    login_url = (
        f"https://{account_id}.signin.aws.amazon.com/console"
        if account_id else ""
    )

    def _tags_str(r):
        if not r.get("ok"):
            return ""
        tags_raw = r.get("tags") or {}
        if isinstance(tags_raw, dict):
            return ", ".join(f"{k}={v}" for k, v in tags_raw.items())
        if isinstance(tags_raw, list):
            return ", ".join(
                f"{t.get('key','')}={t.get('value','')}" for t in tags_raw
            )
        return ""

    rows = []   # list of dicts, one per result row
    for r in raw_results:
        rows.append({
            "account_id":  account_id,
            "login_url":   login_url,
            "username":    "",           # C 留空
            "password":    "",           # D 留空
            "model_label": r.get("model_label", r.get("model_id", "")),
            "region":      r.get("region", ""),
            "qrn":         r.get("inferenceProfileArn", "") if r.get("ok")
                           else r.get("error", ""),
            "tags":        _tags_str(r),
            "ok":          bool(r.get("ok")),
        })

    # ── 按模型类型排序，相同模型的行聚在一起，再按区域排序 ──
    rows.sort(key=lambda x: (x["model_label"], x["region"]))

    # ── 工作簿 & 样式 ────────────────────────────────────────
    wb = Workbook()
    ws = wb.active
    ws.title = "Inference Profiles"

    hdr_font  = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    hdr_fill  = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    val_align   = Alignment(horizontal="left",   vertical="center", wrap_text=False)
    merge_align = Alignment(horizontal="center",  vertical="center", wrap_text=True)
    todo_align  = Alignment(horizontal="center",  vertical="center", wrap_text=False)

    def _border(top="thin", bottom="thin", left="thin", right="thin"):
        def _side(s):
            return Side(style=s, color="D0D7E3") if s else Side(style=None)
        return Border(left=_side(left), right=_side(right),
                      top=_side(top),   bottom=_side(bottom))

    full_border = _border()
    todo_fill   = PatternFill(start_color="FFFDE7", end_color="FFFDE7", fill_type="solid")
    err_font    = Font(name="Calibri", color="C65911", italic=True)

    # ── 表头（行 1） ─────────────────────────────────────────
    headers    = ["AWS账户ID", "登录URL", "账号", "密码",
                  "模型类型", "区域", "模型QRN", "标签"]
    col_widths = [18, 52, 18, 18, 26, 14, 72, 32]

    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.font      = hdr_font
        cell.fill      = hdr_fill
        cell.alignment = hdr_align
        cell.border    = full_border
    for ci, w in enumerate(col_widths, 1):
        ws.column_dimensions[chr(64 + ci)].width = w
    ws.row_dimensions[1].height = 20

    # ── 写入数据（行 2 起） ──────────────────────────────────
    data_start = 2
    total_rows = len(rows)

    for ri, row in enumerate(rows):
        excel_row = data_start + ri
        # 写各列
        values = [
            row["account_id"],  # A
            row["login_url"],   # B
            row["username"],    # C
            row["password"],    # D
            row["model_label"], # E
            row["region"],      # F
            row["qrn"],         # G
            row["tags"],        # H
        ]
        for ci, val in enumerate(values, 1):
            cell = ws.cell(row=excel_row, column=ci, value=val)
            cell.border    = full_border
            cell.alignment = val_align
            if ci in (3, 4):          # 账号/密码：留空高亮
                cell.fill      = todo_fill
                cell.alignment = todo_align
            if ci == 7 and not row["ok"]:   # QRN 失败标红
                cell.font = err_font

    # ── 合并辅助函数 ─────────────────────────────────────────
    def _apply_merge(ws, r1, r2, col, value, align, fill=None, font=None):
        """合并 (r1, col) ~ (r2, col)，写入值并补边框。"""
        if r1 == r2:
            # 单行不需要合并，但确保对齐已经在写入时设置
            return
        ws.merge_cells(
            start_row=r1, start_column=col,
            end_row=r2,   end_column=col
        )
        top_cell = ws.cell(row=r1, column=col, value=value)
        top_cell.alignment = align
        if fill:
            top_cell.fill = fill
        if font:
            top_cell.font = font
        # 合并区域外围补全边框（openpyxl 合并后内部格会丢边框）
        for r in range(r1, r2 + 1):
            top    = "thin" if r == r1 else None
            bottom = "thin" if r == r2 else None
            ws.cell(row=r, column=col).border = _border(
                top=top, bottom=bottom, left="thin", right="thin"
            )

    # ── A/B/C/D：全部数据行合并 ──────────────────────────────
    last_data = data_start + total_rows - 1
    if total_rows > 1:
        _apply_merge(ws, data_start, last_data, 1,
                     account_id, merge_align)
        _apply_merge(ws, data_start, last_data, 2,
                     login_url,  merge_align)
        _apply_merge(ws, data_start, last_data, 3,
                     "",         todo_align,  fill=todo_fill)
        _apply_merge(ws, data_start, last_data, 4,
                     "",         todo_align,  fill=todo_fill)

    # ── E（模型类型）：同一模型连续行合并 ────────────────────
    i = 0
    while i < total_rows:
        j = i + 1
        while j < total_rows and rows[j]["model_label"] == rows[i]["model_label"]:
            j += 1
        r1, r2 = data_start + i, data_start + j - 1
        _apply_merge(ws, r1, r2, 5, rows[i]["model_label"], merge_align)
        i = j

    # ── H（标签）：连续相同标签行合并 ────────────────────────
    i = 0
    while i < total_rows:
        j = i + 1
        while j < total_rows and rows[j]["tags"] == rows[i]["tags"]:
            j += 1
        r1, r2 = data_start + i, data_start + j - 1
        _apply_merge(ws, r1, r2, 8, rows[i]["tags"], merge_align)
        i = j

    # ── 冻结首行 ─────────────────────────────────────────────
    ws.freeze_panes = "A2"

    # ── 输出 ─────────────────────────────────────────────────
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    date_str = datetime.now().strftime("%Y%m%d")
    filename = (
        f"AWS-Bedrock-Arn-{account_id}-{date_str}.xlsx"
        if account_id
        else f"AWS-Bedrock-Arn-{date_str}.xlsx"
    )
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/model-tags")
def model_tags():
    return render_template("model_tags.html")


@app.route("/delete-profiles")
def delete_profiles():
    return render_template("delete_profiles.html")


@app.route("/test-profile")
def test_profile_page():
    return render_template("test_profile.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
