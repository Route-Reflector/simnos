"""SimNOS command-line entry point."""

import argparse
from contextlib import suppress
from importlib.metadata import version
import logging
import os
import time

from simnos import SimNOS
from simnos.core.simnos import DEFAULT_PORT_START
from simnos.plugins.nos import available_platforms

log = logging.getLogger(__name__)

# ad-hoc 専用 flag (dest, CLI 表記) — `-d` 以外で明示されたら warning する集合。
# device_type/inventory は排他 group が argparse 段で弾くので含めない (#267 / Decision 2)。
_ADHOC_FLAGS = (
    ("port", "--port"),
    ("username", "--username"),
    ("password", "--password"),
    ("host_name", "--host-name"),
)

_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _non_empty(value: str) -> str:
    """argparse type: reject empty/whitespace-only strings and strip the rest.

    Used on the path/identifier flags (``-i`` / ``-d`` / ``-n`` / ``--sys-config``)
    so an empty value fails loudly at the CLI boundary (exit 2) and a padded one
    is normalized — notably ``-n "   "`` would otherwise become a whitespace host
    key (gemini#1 2nd). Relying on facade-side truthiness (``SimNOS.__init__``'s
    ``inventory or default``, ``Host``'s ``if self.device_type:``) would let an
    empty string silently mis-launch (default 3-host / builtin cisco_ios), so
    the contract is pinned here instead (#267 / Decision 2). Stripping keeps a
    padded value (``-d " cisco_ios "``) from leaking whitespace into platform /
    path resolution downstream (gemini#1 1st).
    """
    stripped = value.strip()
    if not stripped:
        raise argparse.ArgumentTypeError("must not be empty")
    return stripped


def build_parser() -> argparse.ArgumentParser:
    """Construct the arg parser. No side effects (import-safe)."""
    parser = argparse.ArgumentParser(prog="simnos", description=f"SimNOS, version {version('simnos')}")
    # 共通フラグは parent parser に置き subcommand の後ろでも指定可能にする。
    # add_help=False で親の -h と衝突させない。`simnos up -l DEBUG` /
    # `simnos list-platforms -l DEBUG` が動く。type=str.upper + choices で不正
    # level を argparse が綺麗な usage で弾く (traceback 露出回避)。
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-l",
        "--log-level",
        dest="log_level",
        default="INFO",
        type=str.upper,
        choices=_LOG_LEVELS,
        help="Log level",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    up = sub.add_parser("up", parents=[common], help="Start fake NOS server(s)")
    src = up.add_mutually_exclusive_group(required=False)  # neither = default_inventory 起動
    src.add_argument("-i", "--inventory", type=_non_empty, default=None, help="Path to inventory YAML")
    src.add_argument(
        "-d",
        "--device-type",
        "--device_type",
        dest="device_type",
        type=_non_empty,
        default=None,
        help="Ad-hoc single-host platform (no inventory needed)",
    )
    up.add_argument("-p", "--port", type=int, default=None, help="Ad-hoc listen port (0 = OS-assigned ephemeral, #271)")
    up.add_argument("-n", "--host-name", dest="host_name", type=_non_empty, default=None, help="Ad-hoc host name")
    up.add_argument("-u", "--username", default=None, help="Ad-hoc username (default: builtin)")
    up.add_argument("-w", "--password", default=None, help="Ad-hoc password (default: builtin)")
    up.add_argument("--sys-config", dest="sys_config", type=_non_empty, default=None, help="Explicit sys_config path")
    up.add_argument("-r", "--reload-commands", dest="reload", action="store_true", help="Dev: reload commands")
    up.set_defaults(func=_cmd_up)

    lp = sub.add_parser("list-platforms", parents=[common], help="List supported platforms")
    lp.set_defaults(func=_cmd_list_platforms)
    return parser


def _build_adhoc_inventory(args) -> dict:
    """Minimal NEW single-host inventory; the builtin default fills the rest.

    必ず新規 dict を返す — ``_load_inventory`` は渡された dict に builtin ``default``
    floor を in-place merge するため、caller-owned object を渡してはいけない。不正な
    ``device_type`` は SimNOS 構築後 ``Host._validate`` → ``_check_if_platform_is_supported``
    → ``assert_platform_supported`` が loud に弾く。``port`` は ``is not None`` で判定
    して明示 ``-p 0`` を default に化けさせず保持する。``-p 0`` は ephemeral 起動
    (OS 割当、#271) で、実 port は起動後に ``_cmd_up`` がログ報告する。``-p`` 省略時は
    ``DEFAULT_PORT_START`` (6000) を使う。
    """
    port = args.port if args.port is not None else DEFAULT_PORT_START
    host = {"device_type": args.device_type, "port": port}
    if args.username is not None:
        host["username"] = args.username
    if args.password is not None:
        host["password"] = args.password
    return {"hosts": {args.host_name or args.device_type: host}}


def _warn_stray_adhoc_flags(args, context: str) -> None:
    given = [flag for dest, flag in _ADHOC_FLAGS if getattr(args, dest) is not None]
    if given:
        log.warning("ad-hoc flags %s ignored (%s)", ", ".join(given), context)


def _cmd_up(args) -> int:
    # `-i`/`-d` の排他は argparse の mutually_exclusive_group が exit 2 で弾く。空文字
    # `-d ""`/`-i ""` は parser の type=_non_empty が parse 時に exit 2 で reject 済 —
    # ここへは None か非空文字しか届かない。分岐は `is not None` で判定し未指定 (None)
    # のみ neither (default 起動)。
    if args.device_type is not None:
        inventory = _build_adhoc_inventory(args)
    elif args.inventory is not None:
        _warn_stray_adhoc_flags(args, "with -i/--inventory")
        inventory = args.inventory
    else:  # neither → default_inventory の 3 host 起動 (現行 bare `simnos` を保存)
        _warn_stray_adhoc_flags(args, "without -d/--device-type; default inventory")
        inventory = None

    prior_reload = os.environ.get("SIMNOS_RELOAD_COMMANDS")  # 旧値を保存して復元
    if args.reload:
        os.environ["SIMNOS_RELOAD_COMMANDS"] = "ON"
    # `with SimNOS()` は使わない: __enter__(start) が途中失敗すると __exit__(stop) が
    # 呼ばれず stop() に到達できない。明示 try/finally なら全経路で stop() を試みる。
    # SimNOS.__init__ も inventory/device_type を validate して raise しうるため構築も
    # try 内に入れ、構築失敗時も reload env を復元する。`net = None` guard で構築失敗時
    # の net.stop() を回避。(net.stop() 自体は起動完了 host のみ停止する — server.start()
    # 途中 raise host の cleanup は core 側の別課題、#267 では追わない。)
    net = None
    try:
        net = SimNOS(inventory=inventory, sys_config=args.sys_config)
        log.info("Initiating SimNOS")
        net.start()
        # Report each host's real listening port. With ephemeral ports (`-p 0` or
        # the default inventory, #271) the bound port is OS-assigned, so this is how
        # an interactive user learns where to connect. `host.port` is resolved to the
        # real port after start (Host.start / D4).
        for name, host in net.hosts.items():
            address = host.server_inventory["configuration"].get("address", "127.0.0.1")
            log.info("host %s listening on %s:%d", name, address, host.port)
        with suppress(KeyboardInterrupt):
            while True:
                time.sleep(1)
        log.info("Shutting down SimNOS")
    finally:
        # net.stop() が raise しても reload env 復元へ必ず到達させる: stop を内側 try、
        # env 復元を内側 finally に置き process-global state を全経路で戻す。
        try:
            if net is not None:
                net.stop()  # 起動完了 host を停止 (全 exit 経路で到達)
        finally:
            if prior_reload is None:
                os.environ.pop("SIMNOS_RELOAD_COMMANDS", None)
            else:
                os.environ["SIMNOS_RELOAD_COMMANDS"] = prior_reload
    return 0


def _cmd_list_platforms(args) -> int:
    print(f"Supported platforms ({len(available_platforms)}):")
    for name in available_platforms:
        print(f"  {name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # -l は parent parser 継承で全 subcommand に常在。type=str.upper で正規化済なので
    # .upper() 不要。force=True で main(argv) を同一 process から複数回呼ぶ test でも
    # level 変更が反映される。
    logging.basicConfig(level=args.log_level, force=True)
    return args.func(args)


def run_cli() -> None:  # pyproject entry point (name preserved)
    raise SystemExit(main())


if __name__ == "__main__":
    run_cli()
