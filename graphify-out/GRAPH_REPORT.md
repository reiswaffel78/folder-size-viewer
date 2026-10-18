# Graph Report - folder-size-viewer  (2026-10-18)

## Corpus Check
- 6 files · ~2,970 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 2)

## Summary
- 86 nodes · 142 edges · 10 communities (1 shown, 9 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 12 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a437b6b8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- FolderSizeViewer
- SizeScanner
- ._on_mouse_move
- folder_size_viewer.py
- Tooltip
- CLAUDE.md
- graphify
- AGENTS.md
- .claude/CLAUDE.md

## God Nodes (most connected - your core abstractions)
1. `FolderSizeViewer` - 29 edges
2. `Tooltip` - 10 edges
3. `SizeScanner` - 9 edges
4. `format_size_full()` - 6 edges
5. `format_size()` - 5 edges
6. `format_bytes_exact()` - 4 edges
7. `get_mtime_str()` - 4 edges
8. `main()` - 4 edges
9. `graphify` - 2 edges
10. `sort_key()` - 2 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `FolderSizeViewer`  [EXTRACTED]
  folder_size_viewer.py → folder_size_viewer.py  _Bridges community 0 → community 4_

## Import Cycles
- None detected.

## Communities (10 total, 9 thin omitted)

### Community 3 - "._on_mouse_move"
Cohesion: 0.21
Nodes (3): format_bytes_exact(), format_size(), format_size_full()

## Knowledge Gaps
- **1 isolated node(s):** `graphify-mcp`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 32 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FolderSizeViewer` connect `FolderSizeViewer` to `._add_entry`, `SizeScanner`, `._on_mouse_move`, `folder_size_viewer.py`, `Tooltip`?**
  _High betweenness centrality (0.398) - this node is a cross-community bridge._
- **What connects `graphify-mcp` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Why does `SizeScanner` connect `SizeScanner` to `FolderSizeViewer`, `._on_mouse_move`, `folder_size_viewer.py`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **Why does `Tooltip` connect `Tooltip` to `FolderSizeViewer`, `._add_entry`, `SizeScanner`, `folder_size_viewer.py`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._