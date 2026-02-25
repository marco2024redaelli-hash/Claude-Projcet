#!/usr/bin/env python3
"""
MCP Server per Blender - Bridge Claude Code <-> Blender
=========================================================
Server MCP (stdio) che espone tool per controllare Blender.
Comunica con l'addon blender_mcp_addon.py via TCP socket.

Prerequisiti:
    1. Blender aperto con l'addon MCP attivato (porta 9876)
    2. pip install mcp

Avvio:
    python blender_mcp_server.py

Configurazione Claude Code (.claude/mcp.json):
    {
      "mcpServers": {
        "blender": {
          "command": "python3",
          "args": ["blender_mcp_server.py"]
        }
      }
    }
"""

import json
import socket
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Blender MCP Server")

BLENDER_HOST = "127.0.0.1"
BLENDER_PORT = 9876


def _send_command(command: str, params: dict = None) -> dict:
    """Invia un comando JSON all'addon Blender via TCP e restituisce la risposta."""
    if params is None:
        params = {}
    msg = json.dumps({"command": command, "params": params}) + "\n"

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(60.0)
        sock.connect((BLENDER_HOST, BLENDER_PORT))
        sock.sendall(msg.encode("utf-8"))

        buffer = b""
        while b"\n" not in buffer:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buffer += chunk
        sock.close()

        line = buffer.split(b"\n")[0]
        response = json.loads(line.decode("utf-8"))

        if not response.get("ok", False):
            error = response.get("error", "Errore sconosciuto da Blender")
            raise RuntimeError(error)

        return response.get("result", {})

    except ConnectionRefusedError:
        raise RuntimeError(
            "Impossibile connettersi a Blender. "
            "Assicurati che Blender sia aperto e l'addon MCP sia attivo (porta 9876)."
        )


# ===========================================================
#  TOOL: Connessione
# ===========================================================

@mcp.tool()
def ping() -> str:
    """Verifica la connessione con Blender. Restituisce la versione di Blender."""
    result = _send_command("ping")
    return json.dumps(result, indent=2)


# ===========================================================
#  TOOL: Scena
# ===========================================================

@mcp.tool()
def list_objects() -> str:
    """Elenca tutti gli oggetti nella scena di Blender con tipo, posizione, rotazione e scala."""
    result = _send_command("list_objects")
    return json.dumps(result, indent=2)


@mcp.tool()
def get_object_info(name: str) -> str:
    """Informazioni dettagliate su un oggetto: mesh, materiale, modificatori, figli.

    Args:
        name: Nome dell'oggetto in Blender
    """
    result = _send_command("get_object_info", {"name": name})
    return json.dumps(result, indent=2)


@mcp.tool()
def delete_object(name: str) -> str:
    """Elimina un oggetto dalla scena.

    Args:
        name: Nome dell'oggetto da eliminare
    """
    result = _send_command("delete_object", {"name": name})
    return json.dumps(result, indent=2)


@mcp.tool()
def clear_scene(keep_camera: bool = True, keep_lights: bool = True) -> str:
    """Pulisce la scena rimuovendo gli oggetti.

    Args:
        keep_camera: Se True, mantiene la camera
        keep_lights: Se True, mantiene le luci
    """
    result = _send_command("clear_scene", {"keep_camera": keep_camera, "keep_lights": keep_lights})
    return json.dumps(result, indent=2)


@mcp.tool()
def get_scene_info() -> str:
    """Informazioni sulla scena: motore di rendering, risoluzione, conteggio oggetti."""
    result = _send_command("get_scene_info")
    return json.dumps(result, indent=2)


# ===========================================================
#  TOOL: Primitive 3D
# ===========================================================

@mcp.tool()
def create_cube(
    name: str = "Cube",
    size: float = 2.0,
    location: list[float] = None,
    rotation: list[float] = None,
    scale: list[float] = None,
) -> str:
    """Crea un cubo.

    Args:
        name: Nome dell'oggetto
        size: Dimensione del lato
        location: Posizione [x, y, z]
        rotation: Rotazione in gradi [rx, ry, rz]
        scale: Scala [sx, sy, sz]
    """
    params = {"name": name, "size": size}
    if location:
        params["location"] = location
    if rotation:
        params["rotation"] = rotation
    if scale:
        params["scale"] = scale
    result = _send_command("create_cube", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def create_sphere(
    name: str = "Sphere",
    radius: float = 1.0,
    segments: int = 32,
    ring_count: int = 16,
    location: list[float] = None,
    rotation: list[float] = None,
) -> str:
    """Crea una sfera UV.

    Args:
        name: Nome dell'oggetto
        radius: Raggio
        segments: Segmenti orizzontali
        ring_count: Anelli verticali
        location: Posizione [x, y, z]
        rotation: Rotazione in gradi [rx, ry, rz]
    """
    params = {"name": name, "radius": radius, "segments": segments, "ring_count": ring_count}
    if location:
        params["location"] = location
    if rotation:
        params["rotation"] = rotation
    result = _send_command("create_uv_sphere", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def create_ico_sphere(
    name: str = "IcoSphere",
    radius: float = 1.0,
    subdivisions: int = 2,
    location: list[float] = None,
) -> str:
    """Crea una icosfera.

    Args:
        name: Nome dell'oggetto
        radius: Raggio
        subdivisions: Livello di suddivisione (1-6)
        location: Posizione [x, y, z]
    """
    params = {"name": name, "radius": radius, "subdivisions": subdivisions}
    if location:
        params["location"] = location
    result = _send_command("create_ico_sphere", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def create_cylinder(
    name: str = "Cylinder",
    radius: float = 1.0,
    depth: float = 2.0,
    vertices: int = 32,
    location: list[float] = None,
    rotation: list[float] = None,
) -> str:
    """Crea un cilindro.

    Args:
        name: Nome dell'oggetto
        radius: Raggio
        depth: Altezza
        vertices: Numero di vertici della sezione circolare
        location: Posizione [x, y, z]
        rotation: Rotazione in gradi [rx, ry, rz]
    """
    params = {"name": name, "radius": radius, "depth": depth, "vertices": vertices}
    if location:
        params["location"] = location
    if rotation:
        params["rotation"] = rotation
    result = _send_command("create_cylinder", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def create_cone(
    name: str = "Cone",
    radius1: float = 1.0,
    radius2: float = 0.0,
    depth: float = 2.0,
    vertices: int = 32,
    location: list[float] = None,
) -> str:
    """Crea un cono o tronco di cono.

    Args:
        name: Nome dell'oggetto
        radius1: Raggio base inferiore
        radius2: Raggio base superiore (0 = cono appuntito)
        depth: Altezza
        vertices: Numero vertici della sezione circolare
        location: Posizione [x, y, z]
    """
    params = {"name": name, "radius1": radius1, "radius2": radius2, "depth": depth, "vertices": vertices}
    if location:
        params["location"] = location
    result = _send_command("create_cone", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def create_torus(
    name: str = "Torus",
    major_radius: float = 1.0,
    minor_radius: float = 0.25,
    major_segments: int = 48,
    minor_segments: int = 12,
    location: list[float] = None,
) -> str:
    """Crea un toro (ciambella).

    Args:
        name: Nome dell'oggetto
        major_radius: Raggio maggiore
        minor_radius: Raggio minore (tubo)
        major_segments: Segmenti maggiori
        minor_segments: Segmenti minori
        location: Posizione [x, y, z]
    """
    params = {
        "name": name, "major_radius": major_radius, "minor_radius": minor_radius,
        "major_segments": major_segments, "minor_segments": minor_segments,
    }
    if location:
        params["location"] = location
    result = _send_command("create_torus", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def create_plane(name: str = "Plane", size: float = 2.0, location: list[float] = None) -> str:
    """Crea un piano.

    Args:
        name: Nome dell'oggetto
        size: Dimensione del lato
        location: Posizione [x, y, z]
    """
    params = {"name": name, "size": size}
    if location:
        params["location"] = location
    result = _send_command("create_plane", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def create_monkey(name: str = "Suzanne", location: list[float] = None) -> str:
    """Crea la testa di scimmia Suzanne (utile per test).

    Args:
        name: Nome dell'oggetto
        location: Posizione [x, y, z]
    """
    params = {"name": name}
    if location:
        params["location"] = location
    result = _send_command("create_monkey", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def create_text(
    name: str = "Text",
    text: str = "Hello",
    size: float = 1.0,
    extrude: float = 0.0,
    location: list[float] = None,
) -> str:
    """Crea un oggetto testo 3D.

    Args:
        name: Nome dell'oggetto
        text: Contenuto del testo
        size: Dimensione del carattere
        extrude: Profondita di estrusione (0 = piatto)
        location: Posizione [x, y, z]
    """
    params = {"name": name, "text": text, "size": size}
    if extrude > 0:
        params["extrude"] = extrude
    if location:
        params["location"] = location
    result = _send_command("create_text", params)
    return json.dumps(result, indent=2)


# ===========================================================
#  TOOL: Trasformazioni
# ===========================================================

@mcp.tool()
def set_location(name: str, location: list[float]) -> str:
    """Imposta la posizione assoluta di un oggetto.

    Args:
        name: Nome dell'oggetto
        location: Nuova posizione [x, y, z]
    """
    result = _send_command("set_location", {"name": name, "location": location})
    return json.dumps(result, indent=2)


@mcp.tool()
def set_rotation(name: str, rotation: list[float]) -> str:
    """Imposta la rotazione assoluta di un oggetto (in gradi).

    Args:
        name: Nome dell'oggetto
        rotation: Rotazione [rx, ry, rz] in gradi
    """
    result = _send_command("set_rotation", {"name": name, "rotation": rotation})
    return json.dumps(result, indent=2)


@mcp.tool()
def set_scale(name: str, scale: list[float]) -> str:
    """Imposta la scala assoluta di un oggetto.

    Args:
        name: Nome dell'oggetto
        scale: Scala [sx, sy, sz]
    """
    result = _send_command("set_scale", {"name": name, "scale": scale})
    return json.dumps(result, indent=2)


@mcp.tool()
def translate(name: str, offset: list[float]) -> str:
    """Trasla (sposta) un oggetto di un offset relativo.

    Args:
        name: Nome dell'oggetto
        offset: Spostamento [dx, dy, dz]
    """
    result = _send_command("translate", {"name": name, "offset": offset})
    return json.dumps(result, indent=2)


@mcp.tool()
def rotate(name: str, axis: str, angle: float) -> str:
    """Ruota un oggetto attorno a un asse.

    Args:
        name: Nome dell'oggetto
        axis: Asse di rotazione ("X", "Y" o "Z")
        angle: Angolo in gradi
    """
    result = _send_command("rotate", {"name": name, "axis": axis, "angle": angle})
    return json.dumps(result, indent=2)


@mcp.tool()
def scale_object(name: str, factor: float) -> str:
    """Scala un oggetto uniformemente.

    Args:
        name: Nome dell'oggetto
        factor: Fattore di scala (2.0 = doppio, 0.5 = meta)
    """
    result = _send_command("scale", {"name": name, "factor": factor})
    return json.dumps(result, indent=2)


# ===========================================================
#  TOOL: Modificatori
# ===========================================================

@mcp.tool()
def add_modifier(
    name: str,
    modifier_type: str,
    modifier_name: str = "",
    properties: dict = None,
) -> str:
    """Aggiunge un modificatore a un oggetto.

    Args:
        name: Nome dell'oggetto
        modifier_type: Tipo di modificatore (SUBSURF, MIRROR, ARRAY, SOLIDIFY, BEVEL, BOOLEAN, DECIMATE, etc.)
        modifier_name: Nome del modificatore (opzionale)
        properties: Dizionario di proprieta del modificatore (es. {"levels": 2})
    """
    params = {"name": name, "modifier_type": modifier_type}
    if modifier_name:
        params["modifier_name"] = modifier_name
    if properties:
        params["properties"] = properties
    result = _send_command("add_modifier", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def apply_modifier(name: str, modifier_name: str) -> str:
    """Applica un modificatore, rendendolo permanente sulla mesh.

    Args:
        name: Nome dell'oggetto
        modifier_name: Nome del modificatore da applicare
    """
    result = _send_command("apply_modifier", {"name": name, "modifier_name": modifier_name})
    return json.dumps(result, indent=2)


@mcp.tool()
def remove_modifier(name: str, modifier_name: str) -> str:
    """Rimuove un modificatore senza applicarlo.

    Args:
        name: Nome dell'oggetto
        modifier_name: Nome del modificatore da rimuovere
    """
    result = _send_command("remove_modifier", {"name": name, "modifier_name": modifier_name})
    return json.dumps(result, indent=2)


# ===========================================================
#  TOOL: Operazioni booleane
# ===========================================================

@mcp.tool()
def boolean_operation(
    object_a: str,
    object_b: str,
    operation: str = "DIFFERENCE",
    result_name: str = "",
    delete_tool: bool = True,
) -> str:
    """Esegue un'operazione booleana tra due oggetti.

    Args:
        object_a: Nome dell'oggetto principale (quello che viene modificato)
        object_b: Nome dell'oggetto strumento
        operation: Tipo: "DIFFERENCE" (sottrai), "UNION" (unisci), "INTERSECT" (intersezione)
        result_name: Nome del risultato (default: object_a_bool)
        delete_tool: Se True, elimina object_b dopo l'operazione
    """
    params = {"object_a": object_a, "object_b": object_b, "operation": operation, "delete_tool": delete_tool}
    if result_name:
        params["result_name"] = result_name
    result = _send_command("boolean_operation", params)
    return json.dumps(result, indent=2)


# ===========================================================
#  TOOL: Materiali
# ===========================================================

@mcp.tool()
def set_material(
    name: str,
    color: list[float],
    material_name: str = "",
    metallic: float = 0.0,
    roughness: float = 0.5,
) -> str:
    """Assegna un materiale con colore a un oggetto.

    Args:
        name: Nome dell'oggetto
        color: Colore RGBA [r, g, b, a] con valori 0.0-1.0
        material_name: Nome del materiale (opzionale)
        metallic: Metallicita (0.0-1.0)
        roughness: Rugosita (0.0-1.0)
    """
    params = {"name": name, "color": color, "metallic": metallic, "roughness": roughness}
    if material_name:
        params["material_name"] = material_name
    result = _send_command("set_material", params)
    return json.dumps(result, indent=2)


# ===========================================================
#  TOOL: Import / Export
# ===========================================================

@mcp.tool()
def export_stl(filepath: str, selected_only: bool = False) -> str:
    """Esporta la scena (o la selezione) in formato STL.

    Args:
        filepath: Percorso del file di output (.stl)
        selected_only: Se True, esporta solo gli oggetti selezionati
    """
    result = _send_command("export_stl", {"filepath": filepath, "selected_only": selected_only})
    return json.dumps(result, indent=2)


@mcp.tool()
def export_obj(filepath: str) -> str:
    """Esporta la scena in formato OBJ.

    Args:
        filepath: Percorso del file di output (.obj)
    """
    result = _send_command("export_obj", {"filepath": filepath})
    return json.dumps(result, indent=2)


@mcp.tool()
def export_fbx(filepath: str) -> str:
    """Esporta la scena in formato FBX.

    Args:
        filepath: Percorso del file di output (.fbx)
    """
    result = _send_command("export_fbx", {"filepath": filepath})
    return json.dumps(result, indent=2)


@mcp.tool()
def export_gltf(filepath: str) -> str:
    """Esporta la scena in formato glTF.

    Args:
        filepath: Percorso del file di output (.gltf o .glb)
    """
    result = _send_command("export_gltf", {"filepath": filepath})
    return json.dumps(result, indent=2)


@mcp.tool()
def import_stl(filepath: str, name: str = "") -> str:
    """Importa un file STL nella scena.

    Args:
        filepath: Percorso del file STL
        name: Nome da assegnare all'oggetto importato (opzionale)
    """
    params = {"filepath": filepath}
    if name:
        params["name"] = name
    result = _send_command("import_stl", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def import_obj(filepath: str) -> str:
    """Importa un file OBJ nella scena.

    Args:
        filepath: Percorso del file OBJ
    """
    result = _send_command("import_obj", {"filepath": filepath})
    return json.dumps(result, indent=2)


@mcp.tool()
def import_fbx(filepath: str) -> str:
    """Importa un file FBX nella scena.

    Args:
        filepath: Percorso del file FBX
    """
    result = _send_command("import_fbx", {"filepath": filepath})
    return json.dumps(result, indent=2)


# ===========================================================
#  TOOL: Rendering
# ===========================================================

@mcp.tool()
def render_image(filepath: str = "", resolution_x: int = 1920, resolution_y: int = 1080) -> str:
    """Renderizza la scena corrente e salva l'immagine.

    Args:
        filepath: Percorso del file di output (.png)
        resolution_x: Larghezza in pixel
        resolution_y: Altezza in pixel
    """
    params = {"resolution_x": resolution_x, "resolution_y": resolution_y}
    if filepath:
        params["filepath"] = filepath
    result = _send_command("render_image", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def set_camera(
    location: list[float] = None,
    rotation: list[float] = None,
    focal_length: float = 0,
) -> str:
    """Configura la camera della scena.

    Args:
        location: Posizione [x, y, z]
        rotation: Rotazione in gradi [rx, ry, rz]
        focal_length: Lunghezza focale in mm (0 = non modificare)
    """
    params = {}
    if location:
        params["location"] = location
    if rotation:
        params["rotation"] = rotation
    if focal_length > 0:
        params["focal_length"] = focal_length
    result = _send_command("set_camera", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def add_light(
    name: str = "Light",
    light_type: str = "POINT",
    energy: float = 1000,
    color: list[float] = None,
    location: list[float] = None,
) -> str:
    """Aggiunge una luce alla scena.

    Args:
        name: Nome della luce
        light_type: Tipo: "POINT", "SUN", "SPOT", "AREA"
        energy: Intensita in Watt
        color: Colore [r, g, b] (0.0-1.0)
        location: Posizione [x, y, z]
    """
    params = {"name": name, "type": light_type, "energy": energy}
    if color:
        params["color"] = color
    if location:
        params["location"] = location
    result = _send_command("add_light", params)
    return json.dumps(result, indent=2)


@mcp.tool()
def set_render_settings(
    engine: str = "",
    resolution_x: int = 0,
    resolution_y: int = 0,
    samples: int = 0,
    film_transparent: bool = False,
) -> str:
    """Configura le impostazioni di rendering.

    Args:
        engine: Motore: "CYCLES", "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"
        resolution_x: Larghezza in pixel (0 = non modificare)
        resolution_y: Altezza in pixel (0 = non modificare)
        samples: Numero di campioni Cycles (0 = non modificare)
        film_transparent: Sfondo trasparente
    """
    params = {}
    if engine:
        params["engine"] = engine
    if resolution_x > 0:
        params["resolution_x"] = resolution_x
    if resolution_y > 0:
        params["resolution_y"] = resolution_y
    if samples > 0:
        params["samples"] = samples
    if film_transparent:
        params["film_transparent"] = film_transparent
    result = _send_command("set_render_settings", params)
    return json.dumps(result, indent=2)


# ===========================================================
#  TOOL: Scripting libero
# ===========================================================

@mcp.tool()
def run_blender_script(script: str) -> str:
    """Esegue uno script Python arbitrario dentro Blender.

    Lo script ha accesso a: bpy, math, Vector, Euler, Matrix.
    Assegna il risultato a una variabile 'result' per restituirlo.

    Args:
        script: Codice Python da eseguire in Blender
    """
    result = _send_command("run_script", {"script": script})
    return json.dumps(result, indent=2)


# ===========================================================
#  TOOL: Parenting
# ===========================================================

@mcp.tool()
def set_parent(child: str, parent: str) -> str:
    """Imposta la relazione genitore-figlio tra due oggetti.

    Args:
        child: Nome dell'oggetto figlio
        parent: Nome dell'oggetto genitore
    """
    result = _send_command("set_parent", {"child": child, "parent": parent})
    return json.dumps(result, indent=2)


@mcp.tool()
def clear_parent(name: str) -> str:
    """Rimuove il genitore di un oggetto.

    Args:
        name: Nome dell'oggetto
    """
    result = _send_command("clear_parent", {"name": name})
    return json.dumps(result, indent=2)


# ===========================================================
#  RESOURCE
# ===========================================================

@mcp.resource("blender://info")
def server_info() -> str:
    """Informazioni sul server Blender MCP."""
    return json.dumps({
        "server": "Blender MCP Server",
        "version": "1.0.0",
        "connection": f"{BLENDER_HOST}:{BLENDER_PORT}",
        "capabilities": [
            "Primitive: cube, sphere, cylinder, cone, torus, plane, monkey, text",
            "Trasformazioni: location, rotation, scale, translate, rotate",
            "Modificatori: subsurf, mirror, array, solidify, bevel, boolean, decimate",
            "Booleane: union, difference, intersect",
            "Materiali: colore, metallicita, rugosita",
            "Import: STL, OBJ, FBX",
            "Export: STL, OBJ, FBX, glTF",
            "Rendering: immagine, camera, luci, impostazioni",
            "Scripting Python arbitrario dentro Blender",
        ],
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
