#!/usr/bin/env python3
"""Cross-figure consistency checker for the /figure skill.

Usage:
  python3 figure_audit.py inventory --figures-dir figures/
"""

import argparse
import glob
import json
import os
import re
import sys


# Morandi reference palette (canonical hex values)
MORANDI_PALETTE = {
    "steel_blue": "#576fa0",
    "steel_blue_light": "#a7b9d7",
    "gold": "#e3b87f",
    "gold_light": "#fadcb4",
    "rose": "#b57979",
    "rose_light": "#dea3a2",
    "gray": "#9f9f9f",
    "gray_light": "#cfcece",
}
MORANDI_HEX_SET = {v.lower() for v in MORANDI_PALETTE.values()}


def extract_tikz_style(filepath):
    """Extract style metadata from a TikZ .tex file."""
    with open(filepath, encoding="utf-8", errors="replace") as f:
        content = f.read()

    info = {"tool": "tikz", "file": filepath}

    # Colors
    colors_defined = re.findall(
        r"\\definecolor\{(\w+)\}\{(\w+)\}\{([^}]+)\}", content
    )
    info["colors_defined"] = [
        {"name": c[0], "model": c[1], "value": c[2]} for c in colors_defined
    ]

    # Fill/draw colors used inline
    fills = re.findall(r"fill=([a-zA-Z!0-9]+)", content)
    draws = re.findall(r"draw=([a-zA-Z!0-9]+)", content)
    info["colors_used"] = sorted(set(fills + draws))

    # Hex colors used inline
    hex_colors = re.findall(r"#([0-9a-fA-F]{6})", content)
    info["hex_colors"] = sorted(set(f"#{h.lower()}" for h in hex_colors))

    # Font packages
    font_pkgs = re.findall(r"\\usepackage(?:\[.*?\])?\{([^}]*)\}", content)
    info["font_packages"] = font_pkgs

    # TikZ libraries
    libs = re.findall(r"\\usetikzlibrary\{([^}]+)\}", content)
    info["tikz_libraries"] = [
        l.strip() for lib_str in libs for l in lib_str.split(",")
    ]

    # Arrow style
    info["has_stealth"] = "Stealth" in content or "stealth" in content

    # Document class
    dc = re.search(r"\\documentclass(?:\[([^\]]*)\])?\{(\w+)\}", content)
    if dc:
        info["documentclass"] = dc.group(2)
        info["documentclass_options"] = dc.group(1) or ""

    return info


def extract_python_style(filepath):
    """Extract style metadata from a Python plotting script."""
    with open(filepath, encoding="utf-8", errors="replace") as f:
        content = f.read()

    info = {"tool": "python", "file": filepath}

    # Hex colors
    hex_colors = re.findall(r'["\']#([0-9a-fA-F]{6})["\']', content)
    info["hex_colors"] = sorted(set(f"#{h.lower()}" for h in hex_colors))

    # rcParams font settings
    font_family = re.findall(r'font\.family["\']?\s*[:\]]\s*["\']([^"\']+)', content)
    font_serif = re.findall(r'font\.serif["\']?\s*[:\]]\s*\[?\s*["\']([^"\']+)', content)
    info["font_family"] = font_family[0] if font_family else None
    info["font_serif"] = font_serif[0] if font_serif else None

    # Also check direct font setting
    if "Times New Roman" in content:
        info["has_times"] = True
    else:
        info["has_times"] = bool(font_serif and "Times" in font_serif[0])

    # DPI
    dpi_vals = re.findall(r"dpi\s*=\s*(\d+)", content)
    info["dpi_values"] = sorted(set(int(d) for d in dpi_vals))

    # savefig format
    savefig_fmts = re.findall(r'savefig\(["\'].*?\.(pdf|png|svg|eps)["\']', content)
    info["output_formats"] = sorted(set(savefig_fmts))

    # figsize
    figsizes = re.findall(r"figsize\s*=\s*\(([^)]+)\)", content)
    info["figsizes"] = figsizes

    # Libraries imported
    imports = re.findall(r"^(?:import|from)\s+(\S+)", content, re.MULTILINE)
    info["imports"] = sorted(set(imports))

    return info


def extract_r_style(filepath):
    """Extract style metadata from an R plotting script."""
    with open(filepath, encoding="utf-8", errors="replace") as f:
        content = f.read()

    info = {"tool": "R", "file": filepath}

    # Hex colors
    hex_colors = re.findall(r'["\']#([0-9a-fA-F]{6})["\']', content)
    info["hex_colors"] = sorted(set(f"#{h.lower()}" for h in hex_colors))

    # Font family
    font_refs = re.findall(r'family\s*=\s*["\']([^"\']+)["\']', content)
    info["font_families"] = sorted(set(font_refs))
    info["has_times"] = any("Times" in f for f in font_refs)

    # ggsave params
    ggsave_calls = re.findall(r"ggsave\(([^)]+)\)", content, re.DOTALL)
    info["ggsave_calls"] = len(ggsave_calls)

    # Output formats
    output_fmts = re.findall(
        r'ggsave\(\s*["\'].*?\.(pdf|png|svg|eps)["\']', content
    )
    # Also check device= parameter
    device_fmts = re.findall(r'device\s*=\s*["\'](\w+)["\']', content)
    info["output_formats"] = sorted(set(output_fmts + device_fmts))

    # DPI
    dpi_vals = re.findall(r"dpi\s*=\s*(\d+)", content)
    info["dpi_values"] = sorted(set(int(d) for d in dpi_vals))

    # Width/height
    widths = re.findall(r"width\s*=\s*([\d.]+)", content)
    heights = re.findall(r"height\s*=\s*([\d.]+)", content)
    info["dimensions"] = {"widths": widths[:5], "heights": heights[:5]}

    # Libraries loaded
    libs = re.findall(r"library\((\w+)\)", content)
    info["libraries"] = sorted(set(libs))

    return info


def check_morandi_compliance(hex_colors):
    """Check how many colors match the Morandi palette."""
    if not hex_colors:
        return "N/A", []
    matches = [c for c in hex_colors if c.lower() in MORANDI_HEX_SET]
    non_matches = [c for c in hex_colors if c.lower() not in MORANDI_HEX_SET]
    if len(matches) == len(hex_colors):
        return "FULL", non_matches
    elif matches:
        return "PARTIAL", non_matches
    else:
        return "NONE", non_matches


def cmd_inventory(args):
    """Scan figures directory and extract style metadata."""
    fdir = args.figures_dir
    if not os.path.isdir(fdir):
        print(f"ERROR: Directory not found: {fdir}", file=sys.stderr)
        print("=== VERIFY: FAIL ===")
        sys.exit(1)

    results = []
    errors = []

    # Scan TikZ files
    for f in sorted(glob.glob(os.path.join(fdir, "**", "*.tex"), recursive=True)):
        try:
            results.append(extract_tikz_style(f))
        except Exception as e:
            errors.append(f"TikZ parse error {f}: {e}")

    # Scan Python files
    for f in sorted(glob.glob(os.path.join(fdir, "**", "*.py"), recursive=True)):
        try:
            results.append(extract_python_style(f))
        except Exception as e:
            errors.append(f"Python parse error {f}: {e}")

    # Scan R files
    for f in sorted(glob.glob(os.path.join(fdir, "**", "*.R"), recursive=True)):
        try:
            results.append(extract_r_style(f))
        except Exception as e:
            errors.append(f"R parse error {f}: {e}")

    # Also scan data/scripts/ if it exists (common location for R/Python scripts)
    for scripts_dir in ["data/scripts", "scripts", "code"]:
        parent = os.path.dirname(fdir.rstrip("/"))
        sdir = os.path.join(parent, scripts_dir)
        if os.path.isdir(sdir):
            for ext, extractor in [("*.py", extract_python_style), ("*.R", extract_r_style)]:
                for f in sorted(glob.glob(os.path.join(sdir, ext))):
                    try:
                        results.append(extractor(f))
                    except Exception as e:
                        errors.append(f"Parse error {f}: {e}")

    if not results:
        print(f"WARNING: No figure source files found in {fdir}")
        print("=== VERIFY: FAIL ===")
        sys.exit(1)

    # Build summary
    print("=== FIGURE STYLE INVENTORY ===\n")
    print(f"{'#':<4} {'Tool':<8} {'File':<40} {'Colors':<10} {'Morandi':<10} {'Font':<8} {'Format':<8}")
    print("-" * 100)

    all_issues = []

    for i, r in enumerate(results, 1):
        fname = os.path.basename(r["file"])
        tool = r["tool"]
        hex_colors = r.get("hex_colors", [])
        morandi_status, non_morandi = check_morandi_compliance(hex_colors)

        # Font check
        if tool == "tikz":
            has_font = "newtxtext" in str(r.get("font_packages", []))
            font_str = "OK" if has_font else "MISS"
        else:
            has_font = r.get("has_times", False)
            font_str = "OK" if has_font else "MISS"

        # Format check
        if tool == "tikz":
            fmt_str = "PDF"  # TikZ always compiles to PDF
        else:
            fmts = r.get("output_formats", [])
            fmt_str = ",".join(fmts) if fmts else "?"

        print(
            f"{i:<4} {tool:<8} {fname:<40} {len(hex_colors):<10} {morandi_status:<10} {font_str:<8} {fmt_str:<8}"
        )

        # Collect issues
        if morandi_status == "NONE" and hex_colors:
            all_issues.append(f"{fname}: no Morandi colors (uses {hex_colors[:3]}...)")
        elif morandi_status == "PARTIAL":
            all_issues.append(f"{fname}: non-Morandi colors found: {non_morandi[:3]}")
        if font_str == "MISS":
            all_issues.append(f"{fname}: missing Times New Roman / newtxtext font")
        if "png" in r.get("output_formats", []):
            all_issues.append(f"{fname}: outputs PNG (should be PDF)")

    # Write JSON
    audit_path = os.path.join(fdir, "_figure_audit.json")
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(
            {"figures": results, "issues": all_issues, "total": len(results)},
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\nTotal source files: {len(results)}")
    print(f"Issues found: {len(all_issues)}")
    if all_issues:
        print("\nIssues:")
        for issue in all_issues:
            print(f"  - {issue}")
    if errors:
        print("\nParse errors:")
        for err in errors:
            print(f"  - {err}")

    print(f"\nAudit JSON: {audit_path}")

    if all_issues:
        print(f"\n=== VERIFY: FAIL ({len(all_issues)} issues) ===")
    else:
        print("\n=== VERIFY: PASS ===")


def main():
    parser = argparse.ArgumentParser(description="Cross-figure consistency checker")
    sub = parser.add_subparsers(dest="command")

    p_inv = sub.add_parser("inventory", help="Scan figures and extract style metadata")
    p_inv.add_argument("--figures-dir", required=True, help="Path to figures/ directory")

    args = parser.parse_args()
    if args.command == "inventory":
        cmd_inventory(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
