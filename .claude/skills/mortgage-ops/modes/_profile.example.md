# modes/_profile.example.md  (User Layer — copy to modes/_profile.md and edit; _profile.md is gitignored)
#
# Four knobs that scale the skill's narration and default behavior.
# Per LOCKED DECISIONS D-PROF-01 + D-PROF-02 (10-CONTEXT.md), this file does
# NOT duplicate any calc inputs (income, applicants, monthly debts, geography
# FIPS codes, escrow, VA block, target property value, lender preferences) --
# those live in config/household.yml + config/profile.yml per Phase 1
# DATA_CONTRACT.
#
# If _profile.md is missing on a fresh checkout, modes/_shared.md falls back
# to the four defaults below (D-PROF-04: standard / inline / true / always-ask).
#
# Field semantics:
#
#   verbosity:        concise = number + 1-line context;
#                     standard = full UI-SPEC three-part template
#                                (number / interpretation / citation);
#                     verbose  = full citations + worked-example breakdowns
#                                + footnoted cross-refs to references/*.md
#                                (D-VOICE-02).
#
#   citation_density: full = every claim cited;
#                     inline = key claims only;
#                     minimal = only blocking claims (e.g., DTI cap rejection).
#
#   save_report:      true  = unconditional auto-write per D-13-03;
#                     false = the ONLY user-level override of D-13-03 (suppresses
#                             both the report file AND the matching DuckDB row).
#
#   disambiguation:   always-ask = UI-SPEC §a printed disambiguation question;
#                     auto-pick  = silently route to most-likely mode (opt-in).
#
# To customize: copy this file to modes/_profile.md (without .example) and
# edit the four values below. modes/_profile.md is gitignored; your edits
# stay private. Do NOT add additional top-level keys -- Plan 10-05 CI gate
# `test_profile_example_md_has_exact_four_keys` enforces the four-key schema
# (D-PROF-01 + D-PROF-02).

verbosity: standard         # concise | standard | verbose
citation_density: inline    # full | inline | minimal
save_report: true           # true (default) | false to opt out of D-13-03 auto-write
disambiguation: always-ask  # always-ask (default) | auto-pick
