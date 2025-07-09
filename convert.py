#!/usr/bin/env python3
import json
import argparse

def generate_toml_assignment(input_path: str) -> str:
    """
    Reads a JSON file, compacts it, escapes backslashes and quotes,
    and returns a single-line TOML-compatible assignment.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Compact JSON (no extra spaces), preserve unicode
    compact = json.dumps(data, separators=(',', ':'), ensure_ascii=False)

    # Escape backslashes then double quotes for TOML
    escaped = compact.replace('\\', '\\\\').replace('"', '\\"')

    # Build the TOML assignment line
    return f'config = "{escaped}"'

def main():
    parser = argparse.ArgumentParser(
        description="Generate a TOML-compatible config assignment from config.json")
    parser.add_argument(
        "-i", "--input", default="config.json",
        help="Path to your config.json")
    parser.add_argument(
        "-o", "--output",
        help="Optional file to write the assignment to; prints to stdout if omitted")
    args = parser.parse_args()

    assignment = generate_toml_assignment(args.input)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as out:
            out.write(assignment + "\n")
        print(f"Written assignment to {args.output}")
    else:
        print(assignment)

if __name__ == "__main__":
    main()
