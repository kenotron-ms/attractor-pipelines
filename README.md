# dot-graph-samples

Fixture repository for testing the recursive `git+https://` remote
DOT-source feature in
[`amplifier-resolver-dot-graph`](https://github.com/microsoft/amplifier-resolver-dot-graph).

This repo is not a real pipeline — it exists to be **fetched over the
network** by the dot-graph resolver's remote-source machinery, exercising:

- In-origin `shape=folder` subgraph resolution (relative `dot_file=` paths)
- Multi-level recursive fetching (a subgraph that itself references a
  further subgraph)
- Cross-repo (cross-origin) subgraph resolution via a full
  `git+https://github.com/<owner>/<repo>@<ref>#subdirectory=<path>` URL
- That real file writes during a run land in the actual workspace
  (`context.target_dir`), not an ephemeral fetch temp directory

## Reference graph

```
main.dot
  ├── WriteProof              (tool node; writes proof.txt to workspace)
  ├── subgraphs/child.dot     (in-origin, relative dot_file=)
  │     └── subgraphs/grandchild.dot   (in-origin, relative dot_file=; leaf)
  └── git+https://github.com/kenotron-ms/dot-graph-samples-lib@main#subdirectory=lib.dot
        (cross-repo subgraph; see sibling repo)
```

## Usage

Point `amplifier-resolver-dot-graph` at this repo's entry pipeline via:

```
git+https://github.com/kenotron-ms/dot-graph-samples@main#subdirectory=pipelines/main.dot
```

The resolver should recursively fetch and materialize `main.dot`,
`subgraphs/child.dot`, `subgraphs/grandchild.dot` (all from this repo),
and `lib.dot` (from the sibling `dot-graph-samples-lib` repo, a different
origin), then execute the assembled pipeline end-to-end.

## Sibling repo

[`kenotron-ms/dot-graph-samples-lib`](https://github.com/kenotron-ms/dot-graph-samples-lib)
— the cross-repo subgraph library referenced by `main.dot`.
