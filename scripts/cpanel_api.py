import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def cpanel_request(path, params=None, method="GET"):
    host = os.environ["CPANEL_HOST"]
    user = os.environ["CPANEL_USER"]
    token = os.environ["CPANEL_APITOKEN"]

    url = f"https://{host}:2083{path}"
    headers = {"Authorization": f"cpanel {user}:{token}"}
    data = None

    if params is not None:
        encoded = urllib.parse.urlencode(params)
        if method == "GET":
            url = f"{url}?{encoded}"
        else:
            data = encoded.encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_dir(parent_dir, dir_name):
    res = cpanel_request("/execute/Fileman/list_files", {"dir": parent_dir, "show_hidden": "1"})
    if res.get("status") != 1:
        raise RuntimeError(f"list_files failed for {parent_dir}: {res}")

    if any(item.get("file") == dir_name and item.get("type") == "dir" for item in res.get("data", [])):
        return

    mkdir_res = cpanel_request(
        "/json-api/cpanel",
        {
            "cpanel_jsonapi_version": "2",
            "cpanel_jsonapi_module": "Fileman",
            "cpanel_jsonapi_func": "mkdir",
            "path": parent_dir,
            "name": dir_name,
        },
    )
    api2_res = mkdir_res.get("cpanelresult", {})
    err = api2_res.get("error") or ""
    if err and "File exists" not in err:
        raise RuntimeError(f"mkdir failed for {parent_dir}/{dir_name}: {mkdir_res}")


def cmd_auth():
    webroot = os.environ["CPANEL_WEBROOT"].rstrip("/")
    token = os.environ["CERTBOT_TOKEN"]
    validation = os.environ["CERTBOT_VALIDATION"]

    well_known = f"{webroot}/.well-known"
    challenge_dir = f"{well_known}/acme-challenge"

    ensure_dir(webroot, ".well-known")
    ensure_dir(well_known, "acme-challenge")

    res = cpanel_request(
        "/execute/Fileman/save_file_content",
        {
            "dir": challenge_dir,
            "file": token,
            "content": validation,
            "from_charset": "UTF-8",
            "to_charset": "UTF-8",
            "fallback": "1",
        },
        method="POST",
    )
    if res.get("status") != 1:
        raise RuntimeError(f"save_file_content failed: {res}")
    print(f"Uploaded challenge file: {challenge_dir}/{token}")


def cmd_cleanup():
    webroot = os.environ["CPANEL_WEBROOT"].rstrip("/")
    token = os.environ["CERTBOT_TOKEN"]
    target = f"{webroot}/.well-known/acme-challenge/{token}"

    res = cpanel_request(
        "/json-api/cpanel",
        {
            "cpanel_jsonapi_version": "2",
            "cpanel_jsonapi_module": "Fileman",
            "cpanel_jsonapi_func": "fileop",
            "op": "unlink",
            "sourcefiles": target,
        },
    )
    api2_res = res.get("cpanelresult", {})
    if api2_res.get("error"):
        raise RuntimeError(f"cleanup unlink failed for {target}: {res}")
    print(f"Removed challenge file: {target}")


def cmd_deploy():
    lineage = os.environ["RENEWED_LINEAGE"]
    domain = os.environ["CERT_DOMAIN"]

    with open(os.path.join(lineage, "cert.pem"), "r", encoding="utf-8") as f:
        cert = f.read()
    with open(os.path.join(lineage, "privkey.pem"), "r", encoding="utf-8") as f:
        key = f.read()
    with open(os.path.join(lineage, "chain.pem"), "r", encoding="utf-8") as f:
        cabundle = f.read()

    res = cpanel_request(
        "/execute/SSL/install_ssl",
        {
            "domain": domain,
            "cert": cert,
            "key": key,
            "cabundle": cabundle,
        },
        method="POST",
    )
    if res.get("status") != 1:
        raise RuntimeError(f"SSL/install_ssl failed: {res}")
    print(f"cPanel SSL installed successfully for {domain}.")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"auth", "cleanup", "deploy"}:
        print("Usage: cpanel_api.py <auth|cleanup|deploy>", file=sys.stderr)
        sys.exit(2)

    action = sys.argv[1]
    if action == "auth":
        cmd_auth()
    elif action == "cleanup":
        cmd_cleanup()
    elif action == "deploy":
        cmd_deploy()


if __name__ == "__main__":
    main()
