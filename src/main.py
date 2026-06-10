from __future__ import annotations

import argparse
from pathlib import Path

from src.analyzer import build_dashboard_payload, export_csv
from src.parser import discover_local_exports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze Instagram exports discovered under a data directory."
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing Instagram export folders or ZIP files.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where CSV files will be written.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    exports = discover_local_exports(Path(args.data_dir))
    if not exports:
        raise FileNotFoundError(
            f"No Instagram exports were found under {Path(args.data_dir)}."
        )

    payload = build_dashboard_payload(exports)
    current = payload.current_export.metadata
    print(f"Detected export path: {current.detected_path}")

    output_dir = Path(args.output_dir)
    export_csv(output_dir / "mutuals.csv", payload.current_analysis.mutuals)
    export_csv(output_dir / "fans.csv", payload.current_analysis.fans)
    export_csv(
        output_dir / "not_following_back.csv",
        payload.current_analysis.not_following_back,
    )
    export_csv(
        output_dir / "recently_unfollowed.csv",
        payload.current_analysis.recently_unfollowed,
    )
    if payload.comparison_export is not None:
        export_csv(output_dir / "unfollowers.csv", payload.current_analysis.unfollowers)

    print("Instagram Analyzer Summary")
    print(f"Followers: {len(payload.current_analysis.followers)}")
    print(f"Following: {len(payload.current_analysis.following)}")
    print(f"Mutual followers: {len(payload.current_analysis.mutuals)}")
    print(
        "Not following back: "
        f"{len(payload.current_analysis.not_following_back)}"
    )
    print(f"Fans: {len(payload.current_analysis.fans)}")
    print(
        "Recently unfollowed: "
        f"{len(payload.current_analysis.recently_unfollowed)}"
    )
    if payload.comparison_export is not None:
        print(f"Unfollowers: {len(payload.current_analysis.unfollowers)}")
    else:
        print("Unfollowers: unavailable")


if __name__ == "__main__":
    main()
