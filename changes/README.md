# Changelog fragments

Each branch adds one file, `changes/<topic>.md`, instead of editing a shared
changelog (no merge conflicts). One line per change, starting with one of:

- `Fixed:` a bug fix
- `Changed:` behaviour users will notice, e.g. different return values
- `Added:` a new feature or command

Example, `changes/dot-unstuffing.md`:

    Fixed: dot-stuffed lines were returned twice by BODY, ARTICLE, HEAD and LIST (#99).

The fragments are collected into the changelog at release time.
