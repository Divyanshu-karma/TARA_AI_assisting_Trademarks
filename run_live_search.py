# run_live_search.py
"""
Manual runner — executes REAL USPTO live search via TessLiveAdapter.
This does NOT use mocks. Requires network access to USPTO APIs.

Usage:
    python run_live_search.py
    python run_live_search.py --rapidapi
    python run_live_search.py --mark "TECH GIANT" --class 042

Note:
    Imports from core.search_engine (merged core folder).
"""

import argparse
import json
import os
import sys

from core.search_engine import conduct_tmep_704_02_search

DEFAULT_APPLICATION = {
    "application_id": "123456789",
    "mark_text":      "ADAMS APPLE",
    "mark_type":      "standard_character",
    "goods_services": [
        {"class": "029", "description": "Dried fruits"}
    ],
    "event_trigger":  "first_review",
}


def main():
    parser = argparse.ArgumentParser(description="Run live §704.02 USPTO trademark search")
    parser.add_argument("--rapidapi", action="store_true",
                        help="Use RapidAPI adapter instead of TessLiveAdapter")
    parser.add_argument("--mark",     type=str, default=None, help="Override mark text")
    parser.add_argument("--class",    dest="ic_class", type=str, default=None,
                        help="Override IC class number (e.g. 042)")
    args = parser.parse_args()

    application = dict(DEFAULT_APPLICATION)
    if args.mark:
        application["mark_text"] = args.mark
    if args.ic_class:
        application["goods_services"] = [
            {"class": args.ic_class.zfill(3), "description": "Goods and services"}
        ]

    if args.rapidapi:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("RAPIDAPI_KEY", "")
        if not key:
            print("ERROR: RAPIDAPI_KEY not set in .env")
            sys.exit(1)
        from adapters.rapidapi_trademark import RapidApiTrademarkAdapter
        adapter = RapidApiTrademarkAdapter(rapidapi_key=key)
        print("Adapter: RapidAPI")
    else:
        from adapters.tess_live import TessLiveAdapter
        adapter = TessLiveAdapter()
        print("Adapter: USPTO TESS Live")

    print(f"\nSearching: '{application['mark_text']}' | Class: {application['goods_services'][0]['class']}")
    result = conduct_tmep_704_02_search(application, tess_adapter=adapter)
    print("\n=== LIVE USPTO SEARCH RESULT ===\n")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()