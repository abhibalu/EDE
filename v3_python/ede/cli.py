"""
EDE CLI -- Typer app with validate, assemble, schema, and coverage commands.

Claude Code invokes these commands; Python provides guardrails, not orchestration.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

app = typer.Typer(name="ede", help="Domain Extraction Engine -- validation & assembly CLI")


# -- validate -----------------------------------------------------------------


@app.command()
def validate(
    node0: Annotated[Optional[Path], typer.Option(help="Path to Node 0 JSON")] = None,
    node1: Annotated[Optional[Path], typer.Option(help="Path to Node 1 JSON")] = None,
    node2: Annotated[Optional[Path], typer.Option(help="Path to Node 2 JSON")] = None,
    node3: Annotated[Optional[Path], typer.Option(help="Path to Node 3 JSON")] = None,
    node4: Annotated[Optional[Path], typer.Option(help="Path to Node 4 JSON")] = None,
    strict: Annotated[bool, typer.Option(help="Enable Pydantic strict mode")] = False,
) -> None:
    """Validate pipeline outputs (L1 schema + L2/L3 constraints)."""
    from pydantic import ValidationError

    from .constraints import PipelineData, validate_pipeline
    from .nodes.node0 import Node0Output
    from .nodes.node1 import Node1Output
    from .nodes.node2 import Node2Output
    from .nodes.node3 import Node3Output
    from .nodes.node4 import Node4Output

    node_files = {"node0": node0, "node1": node1, "node2": node2, "node3": node3, "node4": node4}
    models = {"node0": Node0Output, "node1": Node1Output, "node2": Node2Output, "node3": Node3Output, "node4": Node4Output}

    if not any(node_files.values()):
        typer.echo("Error: provide at least one --nodeN flag", err=True)
        raise typer.Exit(1)

    pipeline_data: PipelineData = {}  # type: ignore[typeddict-item]

    # L1: Parse each provided file
    for key, filepath in node_files.items():
        if filepath is None:
            continue
        if not filepath.exists():
            typer.echo(f"Error: {filepath} does not exist", err=True)
            raise typer.Exit(1)

        raw = json.loads(filepath.read_text())
        model_cls = models[key]
        try:
            if strict:
                parsed = model_cls.model_validate(raw, strict=True)
            else:
                parsed = model_cls.model_validate(raw)
        except ValidationError as e:
            typer.echo(f"L1 FAIL ({key}): {e.error_count()} validation errors")
            for err in e.errors():
                loc = ".".join(str(x) for x in err["loc"])
                typer.echo(f"  {loc}: {err['msg']}")
            raise typer.Exit(1)

        pipeline_data[key] = parsed  # type: ignore[literal-required]
        typer.echo(f"L1 OK: {key}")

    # L2+L3: Cross-node constraints
    result = validate_pipeline(pipeline_data)

    for f in result["findings"]:
        icon = {"ERROR": "X", "WARN": "!", "INFO": "i"}[f.level]
        rule = f" [{f.rule}]" if f.rule else ""
        typer.echo(f"[{icon}] Node {f.node} | {f.where}: {f.message}{rule}")

    typer.echo(f"\nErrors: {result['errors']}, Warnings: {result['warnings']}, Infos: {result['infos']}")
    typer.echo(f"Valid: {result['valid']}")

    if not result["valid"]:
        raise typer.Exit(1)


# -- assemble -----------------------------------------------------------------


@app.command()
def assemble(
    fragments_dir: Annotated[Path, typer.Option(help="Directory containing fragment JSON files")],
    node: Annotated[int, typer.Option(help="Node number to assemble (1, 2, or 3)")],
    registry_file: Annotated[Optional[Path], typer.Option(help="Path to registry JSON or Node 0 output")] = None,
    output: Annotated[Path, typer.Option(help="Output file path")] = Path("assembled.json"),
    node1_file: Annotated[Optional[Path], typer.Option(help="Node 1 output (required for node 2 assembly)")] = None,
) -> None:
    """Assemble fragments into node output."""
    from .assemblers import assemble_node1, assemble_node2, assemble_node3
    from .fragments import Node1Fragment, Node2Fragment, Node3Fragment
    from .nodes.node1 import Node1Output
    from .primitives import Registry

    if node not in (1, 2, 3):
        typer.echo("Error: --node must be 1, 2, or 3", err=True)
        raise typer.Exit(1)

    # Load fragments
    fragment_files = sorted(fragments_dir.glob("*.json"))
    if not fragment_files:
        typer.echo(f"Error: no JSON files found in {fragments_dir}", err=True)
        raise typer.Exit(1)

    if node == 3:
        # Node 3 assembler: just obstacle fragments, no registry needed
        fragments_n3 = [Node3Fragment.model_validate(json.loads(f.read_text())) for f in fragment_files]
        result = assemble_node3(fragments_n3)

        for f in result.findings:
            icon = {"ERROR": "X", "WARN": "!", "INFO": "i"}[f.level]
            typer.echo(f"[{icon}] {f.where}: {f.message}")

        output.write_text(json.dumps(result.output, indent=2))
        typer.echo(f"\nAssembled {len(result.output)} new obstacles to {output}")
        return

    # Nodes 1 and 2 require registry
    if not registry_file:
        typer.echo("Error: --registry-file required for node 1 and 2 assembly", err=True)
        raise typer.Exit(1)

    reg_raw = json.loads(registry_file.read_text())
    if "registry" in reg_raw:
        registry = Registry.model_validate(reg_raw["registry"])
    else:
        registry = Registry.model_validate(reg_raw)

    if node == 1:
        fragments = [Node1Fragment.model_validate(json.loads(f.read_text())) for f in fragment_files]
        result = assemble_node1(registry, fragments)
    elif node == 2:
        if not node1_file:
            typer.echo("Error: --node1-file required for node 2 assembly", err=True)
            raise typer.Exit(1)
        n1 = Node1Output.model_validate(json.loads(node1_file.read_text()))
        fragments_n2 = [Node2Fragment.model_validate(json.loads(f.read_text())) for f in fragment_files]
        result = assemble_node2(registry, fragments_n2, n1)

    # Report findings
    for f in result.findings:
        icon = {"ERROR": "X", "WARN": "!", "INFO": "i"}[f.level]
        typer.echo(f"[{icon}] {f.where}: {f.message}")

    # Write output
    output.write_text(result.output.model_dump_json(by_alias=True, indent=2))
    typer.echo(f"\nAssembled output written to {output}")


# -- schema -------------------------------------------------------------------


@app.command()
def schema(
    node: Annotated[Optional[int], typer.Option(help="Node number (0-4)")] = None,
    fragment: Annotated[Optional[str], typer.Option(help="Fragment name: node1, node2, or node3")] = None,
    format: Annotated[str, typer.Option(help="Output format: json-schema")] = "json-schema",
) -> None:
    """Dump JSON Schema for a node model or fragment model."""
    from .fragments import Node1Fragment, Node2Fragment, Node3Fragment
    from .nodes.node0 import Node0Output
    from .nodes.node1 import Node1Output
    from .nodes.node2 import Node2Output
    from .nodes.node3 import Node3Output
    from .nodes.node4 import Node4Output

    if node is not None and fragment is not None:
        typer.echo("Error: use --node or --fragment, not both", err=True)
        raise typer.Exit(1)

    if node is None and fragment is None:
        typer.echo("Error: provide --node (0-4) or --fragment (node1, node2, node3)", err=True)
        raise typer.Exit(1)

    if fragment is not None:
        fragment_models = {"node1": Node1Fragment, "node2": Node2Fragment, "node3": Node3Fragment}
        if fragment not in fragment_models:
            typer.echo(f"Error: --fragment must be node1, node2, or node3, got '{fragment}'", err=True)
            raise typer.Exit(1)
        schema_data = fragment_models[fragment].model_json_schema(by_alias=True)
    else:
        node_models = {0: Node0Output, 1: Node1Output, 2: Node2Output, 3: Node3Output, 4: Node4Output}
        if node not in node_models:
            typer.echo(f"Error: --node must be 0-4, got {node}", err=True)
            raise typer.Exit(1)
        schema_data = node_models[node].model_json_schema(by_alias=True)

    typer.echo(json.dumps(schema_data, indent=2))


# -- coverage -----------------------------------------------------------------


@app.command()
def coverage(
    node0_file: Annotated[Path, typer.Option("--node0", help="Path to Node 0 JSON")],
    node1_file: Annotated[Path, typer.Option("--node1", help="Path to Node 1 JSON")],
) -> None:
    """Cross-reference Node 0 keyFiles against Node 1 filesScanned."""
    from .nodes.node0 import Node0Output
    from .nodes.node1 import Node1Output

    n0 = Node0Output.model_validate(json.loads(node0_file.read_text()))
    n1 = Node1Output.model_validate(json.loads(node1_file.read_text()))

    key_files = {kf.path for kf in n0.key_files}
    scanned_files: set[str] = set()
    for area in n1.metadata.scan_areas:
        scanned_files.update(area.files_scanned)

    # Files in keyFiles that were never scanned
    unscanned = key_files - scanned_files
    if unscanned:
        typer.echo("Key files NOT scanned in Node 1:")
        for f in sorted(unscanned):
            typer.echo(f"  - {f}")
    else:
        typer.echo("All key files were scanned.")

    # Scan areas with zero events
    area_event_counts: dict[str, int] = {}
    for event in n1.events:
        prefix = event.id.split("-")[1] if "-" in event.id else ""
        area_event_counts[prefix] = area_event_counts.get(prefix, 0) + 1

    empty_areas = []
    for area in n1.metadata.scan_areas:
        if area_event_counts.get(area.area_code, 0) == 0:
            empty_areas.append(area.area_code)

    if empty_areas:
        typer.echo(f"\nScan areas with ZERO events (suspicious):")
        for code in empty_areas:
            typer.echo(f"  - {code}")

    if unscanned or empty_areas:
        raise typer.Exit(1)
    typer.echo("\nCoverage check passed.")


# -- validate-fragment --------------------------------------------------------


@app.command(name="validate-fragment")
def validate_fragment(
    node: Annotated[int, typer.Option(help="Node number (1, 2, or 3)")],
    fragment: Annotated[Path, typer.Option(help="Path to fragment JSON file")],
) -> None:
    """Validate a sub-agent fragment against its schema (L1 + cheap L2)."""
    from pydantic import ValidationError

    from .fragments import Node1Fragment, Node2Fragment, Node3Fragment

    if node not in (1, 2, 3):
        typer.echo("Error: --node must be 1, 2, or 3", err=True)
        raise typer.Exit(1)

    if not fragment.exists():
        typer.echo(f"Error: {fragment} does not exist", err=True)
        raise typer.Exit(1)

    raw = json.loads(fragment.read_text())
    models = {1: Node1Fragment, 2: Node2Fragment, 3: Node3Fragment}
    model_cls = models[node]

    # L1: Schema validation
    try:
        parsed = model_cls.model_validate(raw)
    except ValidationError as e:
        typer.echo(f"L1 FAIL: {e.error_count()} schema errors")
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            typer.echo(f"  {loc}: {err['msg']}")
        raise typer.Exit(1)

    typer.echo(f"L1 OK: node{node} fragment")

    # L2 cheap: intra-fragment referential integrity
    errors: list[str] = []

    if node == 2:
        state_names = {s.name for s in parsed.states}
        for t in parsed.transitions:
            if t.source not in state_names:
                errors.append(f"Transition source '{t.source}' is not a declared state")
            if t.target not in state_names:
                errors.append(f"Transition target '{t.target}' is not a declared state")

    if errors:
        typer.echo(f"L2 FAIL: {len(errors)} referential errors")
        for err_msg in errors:
            typer.echo(f"  {err_msg}")
        raise typer.Exit(1)

    if node == 2 and parsed.transitions:
        typer.echo(f"L2 OK: {len(parsed.transitions)} transitions reference valid states")

    typer.echo("Fragment valid.")


# -- render -------------------------------------------------------------------


@app.command()
def render(
    node0: Annotated[Path, typer.Option(help="Path to Node 0 JSON")],
    node1: Annotated[Path, typer.Option(help="Path to Node 1 JSON")],
    node2: Annotated[Path, typer.Option(help="Path to Node 2 JSON")],
    node3: Annotated[Path, typer.Option(help="Path to Node 3 JSON")],
    node4: Annotated[Path, typer.Option(help="Path to Node 4 JSON")],
    output: Annotated[Path, typer.Option(help="Output markdown file")] = Path("domain-spec.md"),
) -> None:
    """Render the complete markdown domain specification from 5 node JSONs."""
    from .nodes.node0 import Node0Output
    from .nodes.node1 import Node1Output
    from .nodes.node2 import Node2Output
    from .nodes.node3 import Node3Output
    from .nodes.node4 import Node4Output
    from .renderer import render_markdown

    paths = {"node0": node0, "node1": node1, "node2": node2, "node3": node3, "node4": node4}
    models = {"node0": Node0Output, "node1": Node1Output, "node2": Node2Output, "node3": Node3Output, "node4": Node4Output}

    # Load and validate all 5 files
    parsed = {}
    for key, path in paths.items():
        if not path.exists():
            typer.echo(f"Error: {path} does not exist", err=True)
            raise typer.Exit(1)
        raw = json.loads(path.read_text())
        try:
            parsed[key] = models[key].model_validate(raw)
        except Exception as e:
            typer.echo(f"Error parsing {key}: {e}", err=True)
            raise typer.Exit(1)

    md = render_markdown(parsed["node0"], parsed["node1"], parsed["node2"], parsed["node3"], parsed["node4"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(md)
    line_count = md.count("\n") + 1
    typer.echo(f"Rendered to {output} ({line_count} lines)")


if __name__ == "__main__":
    app()
