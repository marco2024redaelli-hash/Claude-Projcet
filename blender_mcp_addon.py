"""
Blender MCP Addon - Bridge TCP per Claude Code
================================================
Addon per Blender che avvia un server TCP su localhost:9876.
Riceve comandi JSON dal MCP server esterno ed esegue operazioni
usando l'API bpy di Blender.

Installazione:
    1. Apri Blender > Edit > Preferences > Add-ons > Install...
    2. Seleziona questo file
    3. Attiva l'addon "MCP: Claude Bridge"
"""

bl_info = {
    "name": "MCP: Claude Bridge",
    "author": "Claude Code",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > MCP",
    "description": "Server TCP che permette a Claude Code di controllare Blender via MCP",
    "category": "Development",
}

import bpy
import json
import socket
import threading
import traceback
import math
import os
import tempfile
from mathutils import Vector, Euler, Matrix

HOST = "127.0.0.1"
PORT = 9876
_server_thread = None
_server_socket = None
_running = False


# ===========================================================
#  HANDLER COMANDI
# ===========================================================

def _handle_command(data):
    cmd = data.get("command", "")
    params = data.get("params", {})

    handlers = {
        "ping": cmd_ping,
        "list_objects": cmd_list_objects,
        "get_object_info": cmd_get_object_info,
        "delete_object": cmd_delete_object,
        "clear_scene": cmd_clear_scene,
        "get_scene_info": cmd_get_scene_info,
        "create_cube": cmd_create_cube,
        "create_sphere": cmd_create_sphere,
        "create_uv_sphere": cmd_create_uv_sphere,
        "create_ico_sphere": cmd_create_ico_sphere,
        "create_cylinder": cmd_create_cylinder,
        "create_cone": cmd_create_cone,
        "create_torus": cmd_create_torus,
        "create_plane": cmd_create_plane,
        "create_circle": cmd_create_circle,
        "create_monkey": cmd_create_monkey,
        "create_text": cmd_create_text,
        "create_bezier_curve": cmd_create_bezier_curve,
        "set_location": cmd_set_location,
        "set_rotation": cmd_set_rotation,
        "set_scale": cmd_set_scale,
        "translate": cmd_translate,
        "rotate": cmd_rotate,
        "scale": cmd_scale,
        "add_modifier": cmd_add_modifier,
        "apply_modifier": cmd_apply_modifier,
        "remove_modifier": cmd_remove_modifier,
        "boolean_operation": cmd_boolean_operation,
        "set_material": cmd_set_material,
        "set_parent": cmd_set_parent,
        "clear_parent": cmd_clear_parent,
        "export_stl": cmd_export_stl,
        "export_obj": cmd_export_obj,
        "export_fbx": cmd_export_fbx,
        "export_gltf": cmd_export_gltf,
        "import_stl": cmd_import_stl,
        "import_obj": cmd_import_obj,
        "import_fbx": cmd_import_fbx,
        "render_image": cmd_render_image,
        "set_camera": cmd_set_camera,
        "add_light": cmd_add_light,
        "set_render_settings": cmd_set_render_settings,
        "run_script": cmd_run_script,
    }

    handler = handlers.get(cmd)
    if handler is None:
        return {"ok": False, "error": f"Comando sconosciuto: '{cmd}'", "available": list(handlers.keys())}

    try:
        return {"ok": True, "result": handler(params)}
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


# -- Utilita --

def _get_obj(name):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Oggetto '{name}' non trovato.")
    return obj


def _apply_transform(obj, params):
    if "location" in params:
        obj.location = Vector(params["location"])
    if "rotation" in params:
        obj.rotation_euler = Euler([math.radians(a) for a in params["rotation"]])
    if "scale" in params:
        obj.scale = Vector(params["scale"])


def _obj_summary(obj):
    return {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "dimensions": list(obj.dimensions),
    }


# ===========================================================
#  PING
# ===========================================================

def cmd_ping(params):
    return {"status": "alive", "blender_version": ".".join(str(x) for x in bpy.app.version)}


# ===========================================================
#  SCENA
# ===========================================================

def cmd_list_objects(params):
    objects = []
    for obj in bpy.data.objects:
        objects.append({
            "name": obj.name,
            "type": obj.type,
            "location": list(obj.location),
            "rotation_euler": list(obj.rotation_euler),
            "scale": list(obj.scale),
            "visible": obj.visible_get(),
        })
    return {"objects": objects, "count": len(objects)}


def cmd_get_object_info(params):
    obj = _get_obj(params["name"])
    info = {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation_euler": [math.degrees(a) for a in obj.rotation_euler],
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
        "visible": obj.visible_get(),
        "parent": obj.parent.name if obj.parent else None,
        "children": [c.name for c in obj.children],
        "modifiers": [{"name": m.name, "type": m.type} for m in obj.modifiers],
    }
    if obj.type == "MESH":
        mesh = obj.data
        info["mesh"] = {
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
        }
    if obj.active_material:
        mat = obj.active_material
        info["material"] = {"name": mat.name}
        if mat.use_nodes:
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bc = bsdf.inputs["Base Color"].default_value
                info["material"]["base_color"] = list(bc)
    return info


def cmd_delete_object(params):
    obj = _get_obj(params["name"])
    bpy.data.objects.remove(obj, do_unlink=True)
    return {"deleted": params["name"]}


def cmd_clear_scene(params):
    keep_camera = params.get("keep_camera", True)
    keep_lights = params.get("keep_lights", True)
    removed = []
    for obj in list(bpy.data.objects):
        if keep_camera and obj.type == "CAMERA":
            continue
        if keep_lights and obj.type == "LIGHT":
            continue
        removed.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)
    return {"removed": removed, "count": len(removed)}


def cmd_get_scene_info(params):
    scene = bpy.context.scene
    return {
        "name": scene.name,
        "frame_current": scene.frame_current,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "render_engine": scene.render.engine,
        "resolution_x": scene.render.resolution_x,
        "resolution_y": scene.render.resolution_y,
        "objects_count": len(bpy.data.objects),
        "meshes_count": len(bpy.data.meshes),
        "materials_count": len(bpy.data.materials),
    }


# ===========================================================
#  PRIMITIVE
# ===========================================================

def cmd_create_cube(params):
    size = params.get("size", 2.0)
    bpy.ops.mesh.primitive_cube_add(size=size)
    obj = bpy.context.active_object
    if "name" in params:
        obj.name = params["name"]
    _apply_transform(obj, params)
    return _obj_summary(obj)


def cmd_create_sphere(params):
    return cmd_create_uv_sphere(params)


def cmd_create_uv_sphere(params):
    radius = params.get("radius", 1.0)
    segments = params.get("segments", 32)
    ring_count = params.get("ring_count", 16)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=segments, ring_count=ring_count)
    obj = bpy.context.active_object
    if "name" in params:
        obj.name = params["name"]
    _apply_transform(obj, params)
    return _obj_summary(obj)


def cmd_create_ico_sphere(params):
    radius = params.get("radius", 1.0)
    subdivisions = params.get("subdivisions", 2)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=radius, subdivisions=subdivisions)
    obj = bpy.context.active_object
    if "name" in params:
        obj.name = params["name"]
    _apply_transform(obj, params)
    return _obj_summary(obj)


def cmd_create_cylinder(params):
    radius = params.get("radius", 1.0)
    depth = params.get("depth", 2.0)
    vertices = params.get("vertices", 32)
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=vertices)
    obj = bpy.context.active_object
    if "name" in params:
        obj.name = params["name"]
    _apply_transform(obj, params)
    return _obj_summary(obj)


def cmd_create_cone(params):
    radius1 = params.get("radius1", 1.0)
    radius2 = params.get("radius2", 0.0)
    depth = params.get("depth", 2.0)
    vertices = params.get("vertices", 32)
    bpy.ops.mesh.primitive_cone_add(radius1=radius1, radius2=radius2, depth=depth, vertices=vertices)
    obj = bpy.context.active_object
    if "name" in params:
        obj.name = params["name"]
    _apply_transform(obj, params)
    return _obj_summary(obj)


def cmd_create_torus(params):
    major_radius = params.get("major_radius", 1.0)
    minor_radius = params.get("minor_radius", 0.25)
    major_segments = params.get("major_segments", 48)
    minor_segments = params.get("minor_segments", 12)
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius, minor_radius=minor_radius,
        major_segments=major_segments, minor_segments=minor_segments,
    )
    obj = bpy.context.active_object
    if "name" in params:
        obj.name = params["name"]
    _apply_transform(obj, params)
    return _obj_summary(obj)


def cmd_create_plane(params):
    size = params.get("size", 2.0)
    bpy.ops.mesh.primitive_plane_add(size=size)
    obj = bpy.context.active_object
    if "name" in params:
        obj.name = params["name"]
    _apply_transform(obj, params)
    return _obj_summary(obj)


def cmd_create_circle(params):
    radius = params.get("radius", 1.0)
    vertices = params.get("vertices", 32)
    fill_type = params.get("fill_type", "NOTHING")
    bpy.ops.mesh.primitive_circle_add(radius=radius, vertices=vertices, fill_type=fill_type)
    obj = bpy.context.active_object
    if "name" in params:
        obj.name = params["name"]
    _apply_transform(obj, params)
    return _obj_summary(obj)


def cmd_create_monkey(params):
    bpy.ops.mesh.primitive_monkey_add()
    obj = bpy.context.active_object
    if "name" in params:
        obj.name = params["name"]
    _apply_transform(obj, params)
    return _obj_summary(obj)


# ===========================================================
#  TESTO / CURVE
# ===========================================================

def cmd_create_text(params):
    text = params.get("text", "Hello")
    bpy.ops.object.text_add()
    obj = bpy.context.active_object
    obj.data.body = text
    if "extrude" in params:
        obj.data.extrude = params["extrude"]
    if "size" in params:
        obj.data.size = params["size"]
    if "name" in params:
        obj.name = params["name"]
    _apply_transform(obj, params)
    return _obj_summary(obj)


def cmd_create_bezier_curve(params):
    bpy.ops.curve.primitive_bezier_curve_add()
    obj = bpy.context.active_object
    if "name" in params:
        obj.name = params["name"]
    _apply_transform(obj, params)
    return _obj_summary(obj)


# ===========================================================
#  TRASFORMAZIONI
# ===========================================================

def cmd_set_location(params):
    obj = _get_obj(params["name"])
    obj.location = Vector(params["location"])
    return _obj_summary(obj)


def cmd_set_rotation(params):
    obj = _get_obj(params["name"])
    obj.rotation_euler = Euler([math.radians(a) for a in params["rotation"]])
    return _obj_summary(obj)


def cmd_set_scale(params):
    obj = _get_obj(params["name"])
    obj.scale = Vector(params["scale"])
    return _obj_summary(obj)


def cmd_translate(params):
    obj = _get_obj(params["name"])
    offset = Vector(params["offset"])
    obj.location += offset
    return _obj_summary(obj)


def cmd_rotate(params):
    obj = _get_obj(params["name"])
    axis = params.get("axis", "Z").upper()
    angle = math.radians(params["angle"])
    idx = {"X": 0, "Y": 1, "Z": 2}[axis]
    obj.rotation_euler[idx] += angle
    return _obj_summary(obj)


def cmd_scale(params):
    obj = _get_obj(params["name"])
    factor = params["factor"]
    if isinstance(factor, (int, float)):
        factor = [factor, factor, factor]
    obj.scale = Vector([obj.scale[i] * factor[i] for i in range(3)])
    return _obj_summary(obj)


# ===========================================================
#  MODIFICATORI
# ===========================================================

def cmd_add_modifier(params):
    obj = _get_obj(params["name"])
    mod_type = params["modifier_type"].upper()
    mod_name = params.get("modifier_name", mod_type.title())
    mod = obj.modifiers.new(name=mod_name, type=mod_type)
    props = params.get("properties", {})
    for key, value in props.items():
        if hasattr(mod, key):
            setattr(mod, key, value)
    return {"object": obj.name, "modifier": mod.name, "type": mod.type}


def cmd_apply_modifier(params):
    obj = _get_obj(params["name"])
    mod_name = params["modifier_name"]
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod_name)
    return {"applied": mod_name, "object": obj.name}


def cmd_remove_modifier(params):
    obj = _get_obj(params["name"])
    mod_name = params["modifier_name"]
    mod = obj.modifiers.get(mod_name)
    if mod is None:
        raise ValueError(f"Modificatore '{mod_name}' non trovato su '{obj.name}'.")
    obj.modifiers.remove(mod)
    return {"removed": mod_name, "object": obj.name}


# ===========================================================
#  BOOLEANE
# ===========================================================

def cmd_boolean_operation(params):
    obj_a = _get_obj(params["object_a"])
    obj_b = _get_obj(params["object_b"])
    operation = params.get("operation", "DIFFERENCE").upper()
    result_name = params.get("result_name", f"{obj_a.name}_bool")
    bpy.context.view_layer.objects.active = obj_a
    mod = obj_a.modifiers.new(name="Boolean", type="BOOLEAN")
    mod.operation = operation
    mod.object = obj_b
    bpy.ops.object.modifier_apply(modifier="Boolean")
    if params.get("delete_tool", True):
        bpy.data.objects.remove(obj_b, do_unlink=True)
    obj_a.name = result_name
    return _obj_summary(obj_a)


# ===========================================================
#  MATERIALI
# ===========================================================

def cmd_set_material(params):
    obj = _get_obj(params["name"])
    mat_name = params.get("material_name", f"{obj.name}_mat")
    color = params.get("color", [0.8, 0.8, 0.8, 1.0])
    metallic = params.get("metallic", 0.0)
    roughness = params.get("roughness", 0.5)
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color if len(color) == 4 else color + [1.0]
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    return {"object": obj.name, "material": mat.name, "color": list(color)}


# ===========================================================
#  PARENTING
# ===========================================================

def cmd_set_parent(params):
    child = _get_obj(params["child"])
    parent = _get_obj(params["parent"])
    child.parent = parent
    return {"child": child.name, "parent": parent.name}


def cmd_clear_parent(params):
    obj = _get_obj(params["name"])
    obj.parent = None
    return {"object": obj.name, "parent": None}


# ===========================================================
#  IMPORT / EXPORT
# ===========================================================

def cmd_export_stl(params):
    filepath = params["filepath"]
    selected_only = params.get("selected_only", False)
    if selected_only:
        bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=True)
    else:
        bpy.ops.wm.stl_export(filepath=filepath)
    return {"exported": filepath, "format": "STL"}


def cmd_export_obj(params):
    filepath = params["filepath"]
    bpy.ops.wm.obj_export(filepath=filepath)
    return {"exported": filepath, "format": "OBJ"}


def cmd_export_fbx(params):
    filepath = params["filepath"]
    bpy.ops.export_scene.fbx(filepath=filepath)
    return {"exported": filepath, "format": "FBX"}


def cmd_export_gltf(params):
    filepath = params["filepath"]
    bpy.ops.export_scene.gltf(filepath=filepath)
    return {"exported": filepath, "format": "GLTF"}


def cmd_import_stl(params):
    filepath = params["filepath"]
    bpy.ops.wm.stl_import(filepath=filepath)
    obj = bpy.context.active_object
    if "name" in params and obj:
        obj.name = params["name"]
    return {"imported": filepath, "object": obj.name if obj else None}


def cmd_import_obj(params):
    filepath = params["filepath"]
    bpy.ops.wm.obj_import(filepath=filepath)
    obj = bpy.context.active_object
    return {"imported": filepath, "object": obj.name if obj else None}


def cmd_import_fbx(params):
    filepath = params["filepath"]
    bpy.ops.import_scene.fbx(filepath=filepath)
    obj = bpy.context.active_object
    return {"imported": filepath, "object": obj.name if obj else None}


# ===========================================================
#  RENDERING
# ===========================================================

def cmd_render_image(params):
    filepath = params.get("filepath", os.path.join(tempfile.gettempdir(), "blender_render.png"))
    scene = bpy.context.scene
    scene.render.filepath = filepath
    if "resolution_x" in params:
        scene.render.resolution_x = params["resolution_x"]
    if "resolution_y" in params:
        scene.render.resolution_y = params["resolution_y"]
    if "samples" in params and hasattr(scene, "cycles"):
        scene.cycles.samples = params["samples"]
    bpy.ops.render.render(write_still=True)
    return {"rendered": filepath}


def cmd_set_camera(params):
    cam = None
    for obj in bpy.data.objects:
        if obj.type == "CAMERA":
            cam = obj
            break
    if cam is None:
        bpy.ops.object.camera_add()
        cam = bpy.context.active_object
    if "location" in params:
        cam.location = Vector(params["location"])
    if "rotation" in params:
        cam.rotation_euler = Euler([math.radians(a) for a in params["rotation"]])
    if "focal_length" in params:
        cam.data.lens = params["focal_length"]
    bpy.context.scene.camera = cam
    return {"camera": cam.name, "location": list(cam.location)}


def cmd_add_light(params):
    light_type = params.get("type", "POINT").upper()
    energy = params.get("energy", 1000)
    color = params.get("color", [1.0, 1.0, 1.0])
    location = params.get("location", [0, 0, 5])
    bpy.ops.object.light_add(type=light_type, location=location)
    obj = bpy.context.active_object
    obj.data.energy = energy
    obj.data.color = color[:3]
    if "name" in params:
        obj.name = params["name"]
    return {"light": obj.name, "type": light_type, "energy": energy}


def cmd_set_render_settings(params):
    scene = bpy.context.scene
    if "engine" in params:
        scene.render.engine = params["engine"].upper()
    if "resolution_x" in params:
        scene.render.resolution_x = params["resolution_x"]
    if "resolution_y" in params:
        scene.render.resolution_y = params["resolution_y"]
    if "samples" in params and hasattr(scene, "cycles"):
        scene.cycles.samples = params["samples"]
    if "film_transparent" in params:
        scene.render.film_transparent = params["film_transparent"]
    return {
        "engine": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    }


# ===========================================================
#  SCRIPTING LIBERO
# ===========================================================

def cmd_run_script(params):
    script = params["script"]
    exec_globals = {"bpy": bpy, "math": math, "Vector": Vector, "Euler": Euler, "Matrix": Matrix}
    exec_locals = {}
    exec(script, exec_globals, exec_locals)
    result = exec_locals.get("result", "Script eseguito.")
    if not isinstance(result, (str, int, float, bool, list, dict, type(None))):
        result = str(result)
    return {"script_result": result}


# ===========================================================
#  SERVER TCP
# ===========================================================

def _handle_client(client_socket):
    try:
        buffer = b""
        while True:
            chunk = client_socket.recv(65536)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                    result_holder = [None]
                    done_event = threading.Event()

                    def execute_in_main():
                        result_holder[0] = _handle_command(data)
                        done_event.set()
                        return None

                    bpy.app.timers.register(execute_in_main, first_interval=0.0)
                    done_event.wait(timeout=60.0)

                    if result_holder[0] is None:
                        response = {"ok": False, "error": "Timeout 60s."}
                    else:
                        response = result_holder[0]
                except json.JSONDecodeError as e:
                    response = {"ok": False, "error": f"JSON non valido: {e}"}

                response_bytes = json.dumps(response).encode("utf-8") + b"\n"
                client_socket.sendall(response_bytes)
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        client_socket.close()


def _server_loop():
    global _server_socket, _running
    _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _server_socket.settimeout(1.0)
    try:
        _server_socket.bind((HOST, PORT))
        _server_socket.listen(5)
        print(f"[MCP Bridge] Server TCP in ascolto su {HOST}:{PORT}")
        while _running:
            try:
                client_socket, addr = _server_socket.accept()
                print(f"[MCP Bridge] Connessione da {addr}")
                t = threading.Thread(target=_handle_client, args=(client_socket,), daemon=True)
                t.start()
            except socket.timeout:
                continue
    except OSError as e:
        print(f"[MCP Bridge] Errore server: {e}")
    finally:
        if _server_socket:
            _server_socket.close()
        print("[MCP Bridge] Server TCP arrestato.")


# ===========================================================
#  PANNELLO UI BLENDER
# ===========================================================

class MCP_OT_StartServer(bpy.types.Operator):
    bl_idname = "mcp.start_server"
    bl_label = "Avvia Server MCP"

    def execute(self, context):
        global _server_thread, _running
        if _running:
            self.report({"WARNING"}, "Server gia in esecuzione.")
            return {"CANCELLED"}
        _running = True
        _server_thread = threading.Thread(target=_server_loop, daemon=True)
        _server_thread.start()
        self.report({"INFO"}, f"Server MCP avviato su {HOST}:{PORT}")
        return {"FINISHED"}


class MCP_OT_StopServer(bpy.types.Operator):
    bl_idname = "mcp.stop_server"
    bl_label = "Arresta Server MCP"

    def execute(self, context):
        global _running
        if not _running:
            self.report({"WARNING"}, "Server non in esecuzione.")
            return {"CANCELLED"}
        _running = False
        self.report({"INFO"}, "Server MCP arrestato.")
        return {"FINISHED"}


class MCP_PT_Panel(bpy.types.Panel):
    bl_label = "Claude MCP Bridge"
    bl_idname = "MCP_PT_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MCP"

    def draw(self, context):
        layout = self.layout
        if _running:
            layout.label(text=f"Attivo su {HOST}:{PORT}", icon="CHECKMARK")
            layout.operator("mcp.stop_server", icon="PAUSE")
        else:
            layout.label(text="Server non attivo", icon="ERROR")
            layout.operator("mcp.start_server", icon="PLAY")


_classes = (MCP_OT_StartServer, MCP_OT_StopServer, MCP_PT_Panel)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    # Avvio automatico
    global _running, _server_thread
    _running = True
    _server_thread = threading.Thread(target=_server_loop, daemon=True)
    _server_thread.start()


def unregister():
    global _running
    _running = False
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
