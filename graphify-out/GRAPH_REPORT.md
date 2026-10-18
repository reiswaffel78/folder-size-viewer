# Graph Report - folder-size-viewer  (2026-10-18)

## Corpus Check
- 1 files · ~2,193 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 3)

## Summary
- 76 nodes · 136 edges · 7 communities (0 shown, 7 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 12 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1d642678`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- FolderSizeViewer
- ._add_entry
- SizeScanner
- ._on_mouse_move
- folder_size_viewer.py
- Tooltip

## God Nodes (most connected - your core abstractions)
1. `FolderSizeViewer` - 29 edges
2. `Tooltip` - 10 edges
3. `SizeScanner` - 9 edges
4. `format_size_full()` - 6 edges
5. `format_size()` - 5 edges
6. `format_bytes_exact()` - 4 edges
7. `get_mtime_str()` - 4 edges
8. `main()` - 4 edges
9. `sort_key()` - 2 edges
10. `Ordnergroessen-Viewer fuer Windows 10 ======================================…` - 1 edges

## Surprising Connections (you probably didn't know these)
- `format_size_full()` --calls--> `format_size()`  [EXTRACTED]
  folder_size_viewer.py → folder_size_viewer.py  _Bridges community 3 → community 1_
- `main()` --calls--> `FolderSizeViewer`  [EXTRACTED]
  folder_size_viewer.py → folder_size_viewer.py  _Bridges community 0 → community 4_

## Import Cycles
- None detected.

## Communities (7 total, 7 thin omitted)

## Knowledge Gaps
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FolderSizeViewer` connect `FolderSizeViewer` to `._add_entry`, `._on_mouse_move`, `folder_size_viewer.py`, `Tooltip`, `._apply_filter`?**
  _High betweenness centrality (0.511) - this node is a cross-community bridge._
- **Why does `SizeScanner` connect `SizeScanner` to `FolderSizeViewer`, `._add_entry`, `folder_size_viewer.py`?**
  _High betweenness centrality (0.172) - this node is a cross-community bridge._
- **Why does `Tooltip` connect `Tooltip` to `FolderSizeViewer`, `._add_entry`, `SizeScanner`, `folder_size_viewer.py`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._