"""
Standalone verification for the profile-username URL parsing fix.

No test framework exists on `main`, so this script is self-contained: it builds
its own URLs and asserts against them directly, no fixtures to commit.

What it proves:
1. `extract_username_from_url()` assumes a fixed path shape for LinkedIn
   (`/in/<user>`, read as `parts[1]`) and Stack Overflow
   (`/users/<id>/<slug>`, read as `parts[2]`). Real resumes also carry the
   shorter forms `linkedin.com/<user>` and `stackoverflow.com/users/<id>`,
   where that fixed index is out of range. The IndexError is swallowed by the
   bare `except`, so the username silently comes back empty ("").
2. After the fix, the shorter forms resolve to the correct username/id, and the
   standard `/in/<user>` and `/users/<id>/<slug>` forms are unchanged.

Impact is data-quality only (the empty username lands in the profiles line of
the evaluator text and in the CSV username columns); it is not a scoring change,
and it only triggers when the extractor leaves `network` unset so that
`transform_basics()` runs URL-based extraction.
"""

from transform import (
    extract_domain_from_url,
    extract_username_from_url,
    transform_basics,
)


def username_for(url: str) -> str:
    """Mirror transform_basics(): derive the domain, then the username."""
    domain = extract_domain_from_url(url)
    return extract_username_from_url(url, domain)


# (url, expected_username, label)
CASES = [
    # Shorter forms that are broken on `main` (IndexError -> swallowed -> "").
    ("https://linkedin.com/asha-rao", "asha-rao", "linkedin without /in/"),
    ("https://stackoverflow.com/users/12345678", "12345678", "stackoverflow id only"),
    # Standard / longer forms that already work and must keep working.
    ("https://www.linkedin.com/in/asha-rao", "asha-rao", "linkedin /in/<user>"),
    (
        "https://stackoverflow.com/users/12345678/asha",
        "asha",
        "stackoverflow /users/<id>/<slug>",
    ),
    (
        "https://linkedin.com/pub/asha-rao/12/345/678",
        "asha-rao",
        "linkedin /pub/<user>/...",
    ),
    ("https://linkedin.com/company/acme", "acme", "linkedin /company/<x>"),
    # Degenerate Stack Overflow URL with no id: no username to recover.
    ("https://stackoverflow.com/users", "", "stackoverflow /users only"),
    # A plain GitHub profile URL is unaffected (first path segment).
    ("https://github.com/asha-rao", "asha-rao", "github profile"),
]


def main() -> None:
    failures = []
    for url, expected, label in CASES:
        actual = username_for(url)
        status = "OK" if actual == expected else "FAIL"
        print(
            f"[{status}] {label}: {url}\n       expected={expected!r} actual={actual!r}"
        )
        if actual != expected:
            failures.append(label)

    # End-to-end: the empty username really does land in the parsed profile.
    basics = {"profiles": [{"network": None, "url": "https://linkedin.com/asha-rao"}]}
    profile = transform_basics(basics)["profiles"][0]
    print(
        f"\n[end-to-end] transform_basics profile username: {profile.get('username')!r}"
    )
    if profile.get("username") != "asha-rao":
        failures.append("transform_basics end-to-end")

    if failures:
        raise AssertionError(f"Username extraction wrong for: {', '.join(failures)}")
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
