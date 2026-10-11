import os
import sys

# same as score.py
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

import argparse

from roles import load_role, list_available_roles
from cover_letter import evaluate_cover_letter, print_cover_letter_results


def main(cover_letter_path, role):
    result = evaluate_cover_letter(cover_letter_path, role)
    candidate_name = os.path.basename(cover_letter_path).replace(".pdf", "")
    print_cover_letter_results(result, candidate_name)
    return result


if __name__ == "__main__":
    available_roles = list_available_roles()
    parser = argparse.ArgumentParser(
        description="Score a cover letter against a role (and its job description)."
    )
    parser.add_argument("cover_letter_path", help="Path to the cover letter PDF")
    parser.add_argument(
        "--role",
        required=True,
        help="Role to score against (a directory name under roles/). "
        + (f"Available: {', '.join(available_roles)}" if available_roles else ""),
    )
    args = parser.parse_args()

    if not os.path.exists(args.cover_letter_path):
        print(f"Error: File '{args.cover_letter_path}' does not exist.")
        exit(1)

    try:
        role = load_role(args.role)
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)

    main(args.cover_letter_path, role)