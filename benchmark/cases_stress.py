"""Deliberately tricky wording. Written after the first held-out run to find failure modes."""
S, U = "supported", "unsupported"
CASES = [
("gsoc",S,"Applied ML researcher, GSoC 2024 contributor at Keras."),
("gsoc",S,"Gave a talk at PyCon on my GSoC 2024 project with CPython."),
("gsoc",S,"Google Summer of Code\nContributor, CNCF, May-Aug 2024"),
("gsoc",S,"GSoC 2024 proposal accepted by Apache; shipped the project."),
("gsoc",U,"I am not a GSoC participant."),
("gsoc",U,"Reviewer for a friend's Google Summer of Code 2024 work."),
("gsoc",U,"Compared GSoC 2024 statistics in a data analysis project."),
("girl_script",U,"Organised GSSoC 2024 events for my college as a volunteer."),
("founder",S,"Founder, Acme Labs (2023), previously intern at Google."),
("founder",S,"Co-founder of a community platform startup, Meetly."),
("founder",U,"Built a tool for founders and startup teams."),
("founder",U,"Founded a startup club at Amrita."),
("founder",U,"Startup-founder matching app, a college project with 200 users."),
("early_engineer",S,"Founding engineer at Tracebit, after interning at Zoho."),
("early_engineer",U,"First engineer to fix the bug on my college team."),
("orchestrate",U,"HackerRank Orchestrate 2026, team of 5th-year students.",5),
("orchestrate",S,"HackerRank Orchestrate\nRank 42",42),
]
