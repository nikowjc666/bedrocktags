"""One-time patch: inject test_profile endpoint into app.py"""
import re

with open('app.py', encoding='utf-8') as f:
    src = f.read()

new_route = '''
@app.route("/api/test_profile", methods=["POST"])
def test_profile():
    data = request.get_json() or {}
    ak, sk, user_id = _creds(data)
    region = (data.get("region") or "").strip()
    profile_arn = (data.get("inference_profile_arn") or "").strip()
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
        return jsonify({
            "ok": True,
            "available": status == "ACTIVE",
            "status": status,
            "inferenceProfileId": p.get("inferenceProfileId", ""),
            "inferenceProfileArn": p.get("inferenceProfileArn", profile_arn),
            "name": p.get("inferenceProfileName", ""),
        })
    except botocore.exceptions.ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("ResourceNotFoundException", "NotFoundException"):
            return jsonify({"ok": True, "available": False, "status": "NOT_FOUND",
                            "error": "ARN 不存在或无访问权限"})
        return jsonify({"ok": False, "available": False, "error": _aws_error(e)})
    except Exception as e:
        return jsonify({"ok": False, "available": False, "error": _aws_error(e)})

'''

# Insert before the index route
marker = '\n@app.route("/")\ndef index():'
if marker not in src:
    print("ERROR: marker not found")
    print(repr(src[-500:]))
else:
    src = src.replace(marker, new_route + marker)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print("OK: test_profile route added")
