"""CLI entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import base64
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from release2gitcode.core.models import LocalUploadConfig
from release2gitcode.core.sync import ReleaseSyncService, load_local_upload_config_from_env


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release2gitcode", description="Release2GitCode CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    upload_local = subparsers.add_parser("upload-local", help="Upload local release assets to GitCode")
    upload_local.add_argument("--repo-url")
    upload_local.add_argument("--tag")
    upload_local.add_argument("--token")
    upload_local.add_argument("--release-name")
    upload_local.add_argument("--release-body-file")
    upload_local.add_argument("--target-branch")
    upload_local.add_argument("--file", action="append", dest="files")

    sync_github = subparsers.add_parser("sync-github", help="Sync a GitHub release to GitCode directly")
    sync_github.add_argument("--github-release-url", required=True)
    sync_github.add_argument("--gitcode-repo-url", required=True)
    sync_github.add_argument("--gitcode-token", required=True)
    sync_github.add_argument("--github-token")
    sync_github.add_argument("--serverchan3-sendkey")

    encrypt = subparsers.add_parser("encrypt", help="Encrypt a secret with an RSA public key")
    encrypt.add_argument("--public-key-file")
    encrypt.add_argument("--public-key-env", default="PUBLIC_KEY")
    encrypt.add_argument("--secret")
    encrypt.add_argument("--secret-env")

    return parser


def _load_release_body(path: str | None) -> str | None:
    if not path:
        return None
    return Path(path).read_text(encoding="utf-8")


def _load_local_config(args: argparse.Namespace) -> LocalUploadConfig:
    if not any([args.repo_url, args.tag, args.token, args.files, args.release_name, args.release_body_file, args.target_branch]):
        return load_local_upload_config_from_env()
    files = [Path(item) for item in (args.files or [])]
    return LocalUploadConfig(
        token=args.token or os.getenv("GITCODE_TOKEN", "").strip(),
        repo_url=args.repo_url or os.getenv("GITCODE_REPO_URL", "").strip(),
        tag=args.tag or os.getenv("GITCODE_TAG", "").strip(),
        release_name=args.release_name or os.getenv("GITCODE_RELEASE_NAME", "").strip() or None,
        release_body=_load_release_body(args.release_body_file),
        target_branch=args.target_branch or os.getenv("GITCODE_TARGET_BRANCH", "").strip() or None,
        upload_attempts=int(os.getenv("GITCODE_UPLOAD_ATTEMPTS", "5")),
        timeout_seconds=float(os.getenv("GITCODE_TIMEOUT")) if os.getenv("GITCODE_TIMEOUT") else None,
        files=files or load_local_upload_config_from_env().files,
    )


def _encrypt_secret(public_key_pem: str, secret: str) -> str:
    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    encrypted = public_key.encrypt(
        secret.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(encrypted).decode("utf-8")


async def _run(args: argparse.Namespace) -> int:
    service = ReleaseSyncService()
    if args.command == "upload-local":
        result = await service.upload_local_release(_load_local_config(args))
        print(f"Completed local upload. processed={result.processed_assets} skipped={result.skipped_assets} failed={len(result.failed_assets)}")
        return 0
    if args.command == "sync-github":
        result = await service.sync_github_release(
            github_release_url=args.github_release_url,
            gitcode_repo_url=args.gitcode_repo_url,
            gitcode_token=args.gitcode_token,
            GH_TOKEN=args.GH_TOKEN or os.getenv("GH_TOKEN", "").strip() or None,
            serverchan3_sendkey=args.serverchan3_sendkey,
        )
        print(f"Completed sync. processed={result.processed_assets} skipped={result.skipped_assets} failed={len(result.failed_assets)}")
        if result.notification_warning:
            print(f"Notification warning: {result.notification_warning}", file=sys.stderr)
        return 0 if not result.failed_assets else 1
    if args.command == "encrypt":
        public_key_pem = Path(args.public_key_file).read_text(encoding="utf-8") if args.public_key_file else os.getenv(args.public_key_env, "")
        secret = os.getenv(args.secret_env, "") if args.secret_env else args.secret or ""
        if not public_key_pem or not secret:
            print("public key and secret are required", file=sys.stderr)
            return 1
        print(_encrypt_secret(public_key_pem, secret))
        return 0
    return 1


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))
