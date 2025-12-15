#!/usr/bin/env python3
"""
Fix SU2 2D mesh element orientation (make all QUADs counter-clockwise).

Usage:
  python su2_fix_orientation.py input.su2 -o output_fixed.su2
"""

import argparse
from typing import List, Tuple


def is_int_token(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


def parse_su2_mesh(path: str):
    """
    Minimal SU2 ASCII parser for:
      NDIME
      NPOIN
      NELEM
      MARKER_* blocks (copied as-is)
    Keeps enough structure to rewrite with fixed element ordering.
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    # We'll store:
    # - header lines up to NELEM line (inclusive) with possible other keywords
    # - elements: list of token lists (strings)
    # - node lines: list of token lists (strings)
    # - tail: everything after nodes (including MARKER blocks etc.) as raw lines

    ndime = None
    nelem = None
    npoin = None

    # Find NDIME, NELEM, NPOIN line indices
    def find_key_idx(key: str) -> int:
        for i, line in enumerate(lines):
            if line.strip().startswith(key):
                return i
        return -1

    idx_ndime = find_key_idx("NDIME=")
    idx_nelem = find_key_idx("NELEM=")
    idx_npoin = find_key_idx("NPOIN=")

    if idx_ndime < 0 or idx_nelem < 0 or idx_npoin < 0:
        raise RuntimeError("Could not find NDIME=, NELEM=, or NPOIN= in the SU2 file.")

    ndime = int(lines[idx_ndime].split("=")[1].strip())
    if ndime != 2:
        raise RuntimeError(f"This script is intended for 2D meshes (NDIME=2). Got NDIME={ndime}.")

    nelem = int(lines[idx_nelem].split("=")[1].strip())
    npoin = int(lines[idx_npoin].split("=")[1].strip())

    # Elements block is right after NELEM line
    elem_start = idx_nelem + 1
    elem_end = elem_start + nelem

    # Nodes block is right after NPOIN line
    node_start = idx_npoin + 1
    node_end = node_start + npoin

    # Basic sanity check: element block should appear before node block in common SU2 layout
    # (If not, we'll still proceed but slicing must be correct.)
    if not (elem_start <= elem_end <= len(lines)) or not (node_start <= node_end <= len(lines)):
        raise RuntimeError("File structure seems inconsistent with NELEM/NPOIN counts.")

    # Header is everything up to and including the NELEM line
    header = lines[:elem_start]

    # Parse elements as tokens
    elements = [lines[i].strip().split() for i in range(elem_start, elem_end)]

    # Between elements end and NPOIN line: keep as "mid" (some meshes have extra keywords here)
    mid = lines[elem_end:idx_npoin + 1]  # includes the NPOIN= line

    # Parse nodes as tokens
    nodes_tokens = [lines[i].strip().split() for i in range(node_start, node_end)]

    # Tail: everything after nodes
    tail = lines[node_end:]

    return header, elements, mid, nodes_tokens, tail


def signed_area_quad(p0: Tuple[float, float],
                     p1: Tuple[float, float],
                     p2: Tuple[float, float],
                     p3: Tuple[float, float]) -> float:
    # Shoelace formula for polygon (quad)
    x0, y0 = p0
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    return 0.5 * (
        x0 * y1 - y0 * x1 +
        x1 * y2 - y1 * x2 +
        x2 * y3 - y2 * x3 +
        x3 * y0 - y3 * x0
    )


def fix_elements_orientation(elements: List[List[str]], nodes_tokens: List[List[str]]) -> Tuple[List[List[str]], int]:
    """
    Fix QUAD elements (type 9) orientation based on signed area.
    Returns (fixed_elements, number_flipped)
    """
    # Build node coordinate array: node index equals line number order (0..NPOIN-1)
    # SU2 node lines are typically: x y (z) [id]
    coords: List[Tuple[float, float]] = []
    for tok in nodes_tokens:
        if len(tok) < 2:
            raise RuntimeError("Invalid node line (expected at least 2 coordinates).")
        x = float(tok[0])
        y = float(tok[1])
        coords.append((x, y))

    flipped = 0
    fixed = []

    for e in elements:
        if len(e) < 5:
            # Minimal element: type + 4 nodes (quad) => 5 tokens
            fixed.append(e)
            continue

        etype = int(e[0])

        # QUAD in SU2 is commonly type 9
        if etype == 9:
            # Node indices are next 4 tokens, optional element id may follow
            n = [int(e[1]), int(e[2]), int(e[3]), int(e[4])]

            p0, p1, p2, p3 = coords[n[0]], coords[n[1]], coords[n[2]], coords[n[3]]
            area = signed_area_quad(p0, p1, p2, p3)

            if area < 0.0:
                # Reverse orientation: (n0, n3, n2, n1) is a safe CCW flip for quads
                n_fixed = [n[0], n[3], n[2], n[1]]
                flipped += 1
                new_e = [e[0], str(n_fixed[0]), str(n_fixed[1]), str(n_fixed[2]), str(n_fixed[3])] + e[5:]
                fixed.append(new_e)
            else:
                fixed.append(e)
        else:
            # Leave other element types untouched
            fixed.append(e)

    return fixed, flipped


def write_su2_mesh(path_out: str,
                   header: List[str],
                   elements: List[List[str]],
                   mid: List[str],
                   nodes_tokens: List[List[str]],
                   tail: List[str]) -> None:
    with open(path_out, "w", encoding="utf-8") as f:
        # header (includes NELEM line)
        f.writelines(header)

        # elements
        for e in elements:
            f.write(" ".join(e) + "\n")

        # mid (includes NPOIN line)
        f.writelines(mid)

        # nodes
        for nt in nodes_tokens:
            f.write(" ".join(nt) + "\n")

        # tail
        f.writelines(tail)


def main():
    parser = argparse.ArgumentParser(description="Fix SU2 2D QUAD orientation (make all elements CCW).")
    parser.add_argument("input", help="Input SU2 mesh file (.su2)")
    parser.add_argument("-o", "--output", default=None, help="Output fixed SU2 mesh file (.su2)")
    args = parser.parse_args()

    out = args.output
    if out is None:
        if args.input.lower().endswith(".su2"):
            out = args.input[:-4] + "_fixed.su2"
        else:
            out = args.input + "_fixed.su2"

    header, elements, mid, nodes_tokens, tail = parse_su2_mesh(args.input)
    fixed_elements, flipped = fix_elements_orientation(elements, nodes_tokens)
    write_su2_mesh(out, header, fixed_elements, mid, nodes_tokens, tail)

    print(f"[OK] Wrote: {out}")
    print(f"[INFO] Flipped QUAD elements: {flipped}")


if __name__ == "__main__":
    main()
