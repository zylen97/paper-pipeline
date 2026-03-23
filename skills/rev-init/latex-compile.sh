#!/bin/bash
# latex-compile.sh — PostToolUse hook for auto-compiling .tex files (revision version with diff)
# Triggered after Edit|Write on .tex files
# - Compiles the edited .tex file with latexmk
# - If manuscript.tex: also runs tools/make-diff.sh for track changes

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only process .tex files
if [[ ! "$FILE" =~ \.tex$ ]]; then
  exit 0
fi

BASENAME=$(basename "$FILE" .tex)
DIR=$(dirname "$FILE")

# Run in background to avoid blocking
(
  cd "$DIR" || exit 0

  # Compile the edited file
  /Library/TeX/texbin/latexmk -pvc- -pv- "$BASENAME.tex" > /dev/null 2>&1

  # If manuscript.tex, also generate track changes
  if [ "$BASENAME" = "manuscript" ] && [ -f "tools/make-diff.sh" ]; then
    bash tools/make-diff.sh > /dev/null 2>&1
  fi
) &

exit 0
