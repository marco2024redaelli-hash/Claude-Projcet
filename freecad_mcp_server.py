#!/usr/bin/env python3
"""
MCP Server CAD — Integrazione FreeCAD/OpenCASCADE con Claude
=============================================================
Server Model Context Protocol che espone operazioni CAD 3D come tool
utilizzabili da Claude Code. Usa OpenCASCADE (via cadquery-ocp) come
motore geometrico — lo stesso kernel di FreeCAD.

Avvio:
    python freecad_mcp_server.py

Configurazione Claude Code (.claude/mcp.json):
    {
      "mcpServers": {
        "freecad": {
          "command": "python3",
          "args": ["/percorso/a/freecad_mcp_server.py"]
        }
      }
    }
"""

import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

import cadquery as cq

# ── Server MCP ────────────────────────────────────────────
mcp = FastMCP("FreeCAD MCP Server")

# ── Workspace: contiene tutti gli oggetti 3D della sessione ──
_workspace: dict[str, cq.Workplane] = {}
_export_dir = os.environ.get("CAD_EXPORT_DIR", os.getcwd())


def _get_object(name: str) -> cq.Workplane:
    if name not in _workspace:
        raise ValueError(
            f"Oggetto '{name}' non trovato. Oggetti disponibili: {list(_workspace.keys())}"
        )
    return _workspace[name]


def _summary(name: str, wp: cq.Workplane) -> dict:
    """Restituisce un riepilogo dell'oggetto."""
    bb = wp.val().BoundingBox()
    return {
        "name": name,
        "bounding_box": {
            "x_min": round(bb.xmin, 4), "x_max": round(bb.xmax, 4),
            "y_min": round(bb.ymin, 4), "y_max": round(bb.ymax, 4),
            "z_min": round(bb.zmin, 4), "z_max": round(bb.zmax, 4),
        },
        "size": {
            "x": round(bb.xlen, 4),
            "y": round(bb.ylen, 4),
            "z": round(bb.zlen, 4),
        },
    }


# ═══════════════════════════════════════════════════════════
#  TOOL: Forme primitive
# ═══════════════════════════════════════════════════════════

@mcp.tool()
def create_box(name: str, length: float, width: float, height: float, centered: bool = True) -> str:
    """Crea un parallelepipedo (box).

    Args:
        name: Nome univoco dell'oggetto
        length: Lunghezza (asse X)
        width: Larghezza (asse Y)
        height: Altezza (asse Z)
        centered: Se True, centra il box sull'origine XY
    """
    wp = cq.Workplane("XY").box(length, width, height, centered=(centered, centered, False))
    _workspace[name] = wp
    return json.dumps(_summary(name, wp), indent=2)


@mcp.tool()
def create_cylinder(name: str, radius: float, height: float, centered: bool = True) -> str:
    """Crea un cilindro.

    Args:
        name: Nome univoco dell'oggetto
        radius: Raggio del cilindro
        height: Altezza del cilindro
        centered: Se True, centra il cilindro sull'origine XY
    """
    wp = cq.Workplane("XY").cylinder(height, radius, centered=(centered, centered, False))
    _workspace[name] = wp
    return json.dumps(_summary(name, wp), indent=2)


@mcp.tool()
def create_sphere(name: str, radius: float) -> str:
    """Crea una sfera centrata nell'origine.

    Args:
        name: Nome univoco dell'oggetto
        radius: Raggio della sfera
    """
    wp = cq.Workplane("XY").sphere(radius)
    _workspace[name] = wp
    return json.dumps(_summary(name, wp), indent=2)


@mcp.tool()
def create_cone(name: str, radius_bottom: float, radius_top: float, height: float) -> str:
    """Crea un tronco di cono (o cono se radius_top=0).

    Args:
        name: Nome univoco dell'oggetto
        radius_bottom: Raggio della base inferiore
        radius_top: Raggio della base superiore (0 per un cono)
        height: Altezza
    """
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

    axis = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1))
    cone_shape = BRepPrimAPI_MakeCone(axis, radius_bottom, radius_top, height).Shape()
    wp = cq.Workplane("XY").newObject([cq.Shape(cone_shape)])
    _workspace[name] = wp
    return json.dumps(_summary(name, wp), indent=2)


@mcp.tool()
def create_torus(name: str, major_radius: float, minor_radius: float) -> str:
    """Crea un toro (ciambella).

    Args:
        name: Nome univoco dell'oggetto
        major_radius: Raggio maggiore (centro del toro all'asse del tubo)
        minor_radius: Raggio minore (raggio del tubo)
    """
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeTorus

    torus_shape = BRepPrimAPI_MakeTorus(major_radius, minor_radius).Shape()
    wp = cq.Workplane("XY").newObject([cq.Shape(torus_shape)])
    _workspace[name] = wp
    return json.dumps(_summary(name, wp), indent=2)


# ═══════════════════════════════════════════════════════════
#  TOOL: Operazioni booleane
# ═══════════════════════════════════════════════════════════

@mcp.tool()
def boolean_union(name: str, object_a: str, object_b: str) -> str:
    """Unione booleana (fusione) di due oggetti.

    Args:
        name: Nome del nuovo oggetto risultante
        object_a: Nome del primo oggetto
        object_b: Nome del secondo oggetto
    """
    a = _get_object(object_a)
    b = _get_object(object_b)
    result = a.union(b)
    _workspace[name] = result
    return json.dumps(_summary(name, result), indent=2)


@mcp.tool()
def boolean_cut(name: str, object_a: str, object_b: str) -> str:
    """Sottrazione booleana: rimuove object_b da object_a.

    Args:
        name: Nome del nuovo oggetto risultante
        object_a: Nome dell'oggetto da cui sottrarre
        object_b: Nome dell'oggetto da sottrarre
    """
    a = _get_object(object_a)
    b = _get_object(object_b)
    result = a.cut(b)
    _workspace[name] = result
    return json.dumps(_summary(name, result), indent=2)


@mcp.tool()
def boolean_intersect(name: str, object_a: str, object_b: str) -> str:
    """Intersezione booleana: mantiene solo il volume comune.

    Args:
        name: Nome del nuovo oggetto risultante
        object_a: Nome del primo oggetto
        object_b: Nome del secondo oggetto
    """
    a = _get_object(object_a)
    b = _get_object(object_b)
    result = a.intersect(b)
    _workspace[name] = result
    return json.dumps(_summary(name, result), indent=2)


# ═══════════════════════════════════════════════════════════
#  TOOL: Trasformazioni
# ═══════════════════════════════════════════════════════════

@mcp.tool()
def translate(name: str, object_name: str, x: float = 0, y: float = 0, z: float = 0) -> str:
    """Trasla (sposta) un oggetto.

    Args:
        name: Nome del nuovo oggetto risultante
        object_name: Nome dell'oggetto da traslare
        x: Spostamento lungo X
        y: Spostamento lungo Y
        z: Spostamento lungo Z
    """
    obj = _get_object(object_name)
    result = obj.translate((x, y, z))
    _workspace[name] = result
    return json.dumps(_summary(name, result), indent=2)


@mcp.tool()
def rotate(name: str, object_name: str, axis_x: float = 0, axis_y: float = 0,
           axis_z: float = 1, angle_degrees: float = 0) -> str:
    """Ruota un oggetto attorno a un asse passante per l'origine.

    Args:
        name: Nome del nuovo oggetto risultante
        object_name: Nome dell'oggetto da ruotare
        axis_x: Componente X dell'asse di rotazione
        axis_y: Componente Y dell'asse di rotazione
        axis_z: Componente Z dell'asse di rotazione
        angle_degrees: Angolo di rotazione in gradi
    """
    obj = _get_object(object_name)
    result = obj.rotate((0, 0, 0), (axis_x, axis_y, axis_z), angle_degrees)
    _workspace[name] = result
    return json.dumps(_summary(name, result), indent=2)


@mcp.tool()
def mirror(name: str, object_name: str, plane: str = "XY") -> str:
    """Specchia un oggetto rispetto a un piano.

    Args:
        name: Nome del nuovo oggetto risultante
        object_name: Nome dell'oggetto da specchiare
        plane: Piano di simmetria — "XY", "XZ" o "YZ"
    """
    obj = _get_object(object_name)
    result = obj.mirror(plane)
    _workspace[name] = result
    return json.dumps(_summary(name, result), indent=2)


# ═══════════════════════════════════════════════════════════
#  TOOL: Modifiche geometriche
# ═══════════════════════════════════════════════════════════

@mcp.tool()
def fillet_all_edges(name: str, object_name: str, radius: float) -> str:
    """Applica un raccordo (fillet) a tutti gli spigoli di un oggetto.

    Args:
        name: Nome del nuovo oggetto risultante
        object_name: Nome dell'oggetto
        radius: Raggio del raccordo
    """
    obj = _get_object(object_name)
    result = obj.edges().fillet(radius)
    _workspace[name] = result
    return json.dumps(_summary(name, result), indent=2)


@mcp.tool()
def chamfer_all_edges(name: str, object_name: str, length: float) -> str:
    """Applica uno smusso (chamfer) a tutti gli spigoli di un oggetto.

    Args:
        name: Nome del nuovo oggetto risultante
        object_name: Nome dell'oggetto
        length: Lunghezza dello smusso
    """
    obj = _get_object(object_name)
    result = obj.edges().chamfer(length)
    _workspace[name] = result
    return json.dumps(_summary(name, result), indent=2)


@mcp.tool()
def shell(name: str, object_name: str, thickness: float) -> str:
    """Svuota un solido creando un guscio (shell) con lo spessore indicato.
    Rimuove la faccia superiore (Z+).

    Args:
        name: Nome del nuovo oggetto risultante
        object_name: Nome dell'oggetto
        thickness: Spessore del guscio
    """
    obj = _get_object(object_name)
    result = obj.faces(">Z").shell(-thickness)
    _workspace[name] = result
    return json.dumps(_summary(name, result), indent=2)


# ═══════════════════════════════════════════════════════════
#  TOOL: Estrusioni e sketch
# ═══════════════════════════════════════════════════════════

@mcp.tool()
def extrude_polygon(name: str, points: list[list[float]], height: float) -> str:
    """Estrude un poligono definito da una lista di punti 2D.

    Args:
        name: Nome del nuovo oggetto
        points: Lista di coordinate [x, y] che definiscono il profilo (chiuso automaticamente)
        height: Altezza di estrusione
    """
    tuples = [(p[0], p[1]) for p in points]
    wp = cq.Workplane("XY").polyline(tuples).close().extrude(height)
    _workspace[name] = wp
    return json.dumps(_summary(name, wp), indent=2)


@mcp.tool()
def extrude_circle(name: str, center_x: float, center_y: float, radius: float, height: float) -> str:
    """Estrude un cerchio (crea un cilindro in una posizione specifica).

    Args:
        name: Nome del nuovo oggetto
        center_x: Coordinata X del centro
        center_y: Coordinata Y del centro
        radius: Raggio del cerchio
        height: Altezza di estrusione
    """
    wp = (cq.Workplane("XY")
          .center(center_x, center_y)
          .circle(radius)
          .extrude(height))
    _workspace[name] = wp
    return json.dumps(_summary(name, wp), indent=2)


@mcp.tool()
def extrude_text(name: str, text: str, font_size: float, height: float, font: str = "Arial") -> str:
    """Estrude un testo 3D.

    Args:
        name: Nome del nuovo oggetto
        text: Testo da estrudere
        font_size: Dimensione del carattere
        height: Altezza di estrusione
        font: Nome del font (default: Arial)
    """
    wp = cq.Workplane("XY").text(text, font_size, height, font=font)
    _workspace[name] = wp
    return json.dumps(_summary(name, wp), indent=2)


# ═══════════════════════════════════════════════════════════
#  TOOL: Esecuzione script CadQuery arbitrario
# ═══════════════════════════════════════════════════════════

@mcp.tool()
def run_cadquery_script(name: str, script: str) -> str:
    """Esegue uno script CadQuery arbitrario e salva il risultato nel workspace.

    Lo script deve assegnare il risultato finale a una variabile chiamata `result`.
    Esempio: result = cq.Workplane("XY").box(10, 20, 5)

    Args:
        name: Nome con cui salvare il risultato nel workspace
        script: Codice Python/CadQuery da eseguire
    """
    exec_globals: dict[str, Any] = {"cq": cq, "math": math}
    exec_locals: dict[str, Any] = {}
    exec(script, exec_globals, exec_locals)

    if "result" not in exec_locals:
        raise ValueError("Lo script deve assegnare il risultato finale alla variabile 'result'.")

    result = exec_locals["result"]
    if not isinstance(result, cq.Workplane):
        raise TypeError(f"'result' deve essere un cq.Workplane, ricevuto: {type(result).__name__}")

    _workspace[name] = result
    return json.dumps(_summary(name, result), indent=2)


# ═══════════════════════════════════════════════════════════
#  TOOL: Import / Export
# ═══════════════════════════════════════════════════════════

@mcp.tool()
def import_step(name: str, filepath: str) -> str:
    """Importa un file STEP nel workspace.

    Args:
        name: Nome con cui salvare l'oggetto nel workspace
        filepath: Percorso del file STEP da importare
    """
    wp = cq.importers.importStep(filepath)
    _workspace[name] = wp
    return json.dumps(_summary(name, wp), indent=2)


@mcp.tool()
def export_step(object_name: str, filepath: str = "") -> str:
    """Esporta un oggetto in formato STEP.

    Args:
        object_name: Nome dell'oggetto da esportare
        filepath: Percorso di output (default: <export_dir>/<object_name>.step)
    """
    obj = _get_object(object_name)
    if not filepath:
        filepath = str(Path(_export_dir) / f"{object_name}.step")
    cq.exporters.export(obj, filepath, exportType="STEP")
    return json.dumps({"exported": filepath, "format": "STEP"})


@mcp.tool()
def export_stl(object_name: str, filepath: str = "", tolerance: float = 0.1, ascii_mode: bool = False) -> str:
    """Esporta un oggetto in formato STL.

    Args:
        object_name: Nome dell'oggetto da esportare
        filepath: Percorso di output (default: <export_dir>/<object_name>.stl)
        tolerance: Tolleranza della mesh (valori più bassi = mesh più fine)
        ascii_mode: Se True, salva in formato ASCII
    """
    obj = _get_object(object_name)
    if not filepath:
        filepath = str(Path(_export_dir) / f"{object_name}.stl")
    cq.exporters.export(obj, filepath, exportType="STL", tolerance=tolerance, angularTolerance=0.1)
    return json.dumps({"exported": filepath, "format": "STL", "tolerance": tolerance})


@mcp.tool()
def export_svg(object_name: str, filepath: str = "") -> str:
    """Esporta una vista 2D dell'oggetto in formato SVG.

    Args:
        object_name: Nome dell'oggetto da esportare
        filepath: Percorso di output (default: <export_dir>/<object_name>.svg)
    """
    obj = _get_object(object_name)
    if not filepath:
        filepath = str(Path(_export_dir) / f"{object_name}.svg")
    cq.exporters.export(obj, filepath, exportType="SVG")
    return json.dumps({"exported": filepath, "format": "SVG"})


# ═══════════════════════════════════════════════════════════
#  TOOL: Gestione workspace
# ═══════════════════════════════════════════════════════════

@mcp.tool()
def list_objects() -> str:
    """Elenca tutti gli oggetti presenti nel workspace con le loro dimensioni."""
    if not _workspace:
        return json.dumps({"objects": [], "message": "Workspace vuoto."})
    summaries = [_summary(name, wp) for name, wp in _workspace.items()]
    return json.dumps({"objects": summaries, "count": len(summaries)}, indent=2)


@mcp.tool()
def delete_object(name: str) -> str:
    """Rimuove un oggetto dal workspace.

    Args:
        name: Nome dell'oggetto da rimuovere
    """
    if name not in _workspace:
        raise ValueError(f"Oggetto '{name}' non trovato.")
    del _workspace[name]
    return json.dumps({"deleted": name, "remaining": list(_workspace.keys())})


@mcp.tool()
def clear_workspace() -> str:
    """Rimuove tutti gli oggetti dal workspace."""
    count = len(_workspace)
    _workspace.clear()
    return json.dumps({"cleared": count, "message": "Workspace svuotato."})


@mcp.tool()
def get_object_info(name: str) -> str:
    """Restituisce informazioni dettagliate su un oggetto.

    Args:
        name: Nome dell'oggetto
    """
    obj = _get_object(name)
    shape = obj.val()
    bb = shape.BoundingBox()
    info = _summary(name, obj)
    info["volume"] = round(shape.Volume(), 6)
    info["area"] = round(shape.Area(), 6)
    info["center_of_mass"] = {
        "x": round(shape.Center().x, 4),
        "y": round(shape.Center().y, 4),
        "z": round(shape.Center().z, 4),
    }
    return json.dumps(info, indent=2)


# ═══════════════════════════════════════════════════════════
#  RESOURCE: Informazioni sul server
# ═══════════════════════════════════════════════════════════

@mcp.resource("cad://info")
def server_info() -> str:
    """Informazioni sul server CAD MCP."""
    return json.dumps({
        "server": "FreeCAD MCP Server",
        "version": "1.0.0",
        "engine": "OpenCASCADE (via cadquery-ocp)",
        "export_dir": _export_dir,
        "workspace_objects": len(_workspace),
        "capabilities": [
            "Primitive shapes: box, cylinder, sphere, cone, torus",
            "Boolean operations: union, cut, intersect",
            "Transforms: translate, rotate, mirror",
            "Modifications: fillet, chamfer, shell",
            "Extrusion: polygon, circle, text",
            "Import/Export: STEP, STL, SVG",
            "Arbitrary CadQuery scripts",
        ],
    }, indent=2)


# ── Main ──────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
