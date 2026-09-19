import argparse
import json
from pathlib import Path

from ..exchange.package import export_exchange_package, import_exchange_package, inspect_exchange_package


def build_parser():
    parser = argparse.ArgumentParser(
        prog="code-composer-exchange",
        description="Lossless Code Composer-to-Code Composer .ccx handoff packages.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export", help="Checkpoint Music IR/workspace into a .ccx package")
    export.add_argument("source", type=Path, help="Music IR JSON or imported exchange workspace")
    export.add_argument("out_ccx", type=Path)
    export.add_argument("--author", required=True)
    export.add_argument("--message", default="")
    export.add_argument("--status", choices=("working", "review", "approved_internal"), default="working")
    export.add_argument("--request", action="append", default=[])
    export.add_argument("--lock", action="append", default=[])
    export.add_argument("--note", action="append", default=[])
    export.add_argument("--plan", type=Path)
    export.add_argument("--brief", type=Path)
    export.add_argument("--parent", type=Path, help="Explicit parent .ccx when exporting from a standalone Music IR")
    export.add_argument("--timestamp", default=None, help="Explicit ISO timestamp for reproducible provenance fixtures")

    imp = sub.add_parser("import", help="Validate and fast-forward a local exchange workspace")
    imp.add_argument("package", type=Path)
    imp.add_argument("workspace", type=Path)

    inspect = sub.add_parser("inspect", help="Validate a .ccx package and print its manifest summary")
    inspect.add_argument("package", type=Path)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "export":
        result = export_exchange_package(
            args.source,
            args.out_ccx,
            author=args.author,
            message=args.message,
            status=args.status,
            requested_changes=args.request,
            locked_scopes=args.lock,
            notes=args.note,
            plan=args.plan,
            brief=args.brief,
            parent_package=args.parent,
            created_at=args.timestamp,
        )
        output = {
            "package": result["package_path"],
            "package_sha256": result["package_sha256"],
            "revision_id": result["manifest"]["revision_id"],
            "parent_revision_id": result["manifest"].get("parent_revision_id"),
            "handoff_status": result["handoff"]["status"],
            "workspace_checkpointed": result["workspace_checkpointed"],
        }
    elif args.command == "import":
        output = import_exchange_package(args.package, args.workspace)
    else:
        output = inspect_exchange_package(args.package)
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
