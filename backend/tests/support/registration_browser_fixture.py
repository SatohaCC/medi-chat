"""Fresh original-XML registration in a browser-owned test schema."""

import argparse
from pathlib import Path

from backend.tests.support.postgres_browser_fixture import prepare


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.root, full=True), flush=True)


if __name__ == "__main__":
    main()
