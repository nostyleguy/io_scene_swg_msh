# MIT License
#
# Copyright (c) 2022 Nick Rafalski
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import bpy
import base64
import bmesh
import time, datetime, array, functools, math
from . import vector3D
from . import swg_types
from . import vertex_buffer_format
from . import data_types
from . import export_flr
from . import export_msh
from . import support
from . import extents

from mathutils import Matrix, Vector, Color
from bpy_extras import io_utils, node_shader_utils

from bpy_extras.wm_utils.progress_report import (
    ProgressReport,
    ProgressReportSubstep,
)

def mesh_triangulate(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()

def save(context, filepath, *, flip_uv_vertical=False, export_children=True):
    collection = bpy.context.view_layer.active_layer_collection.collection
    if collection != None:
        dirname = os.path.dirname(filepath)
        fullpath = os.path.join(dirname, collection.name+".lod")
        extract_dir=context.preferences.addons[__package__].preferences.swg_root
        return export_one(fullpath, extract_dir, collection, flip_uv_vertical, export_children)
    else:
        return {'CANCELLED'}

def export_one(fullpath, extract_dir, collection, flip_uv_vertical, export_children):
    lodName = os.path.basename(fullpath).replace('.lod','')
    print(f"LOD Name: {lodName}")

    appearanceDirname = os.path.dirname(os.path.dirname(fullpath))

    lodFile = swg_types.LodFile(fullpath)
    start = time.time()
    print(f'Exporting lod: {fullpath} Flip UV: {flip_uv_vertical}')
    
    meshCol = None
    hardpointsCol = None
    collisionCol = None
    floorCol = None
    rtwCol = None

    for child in collection.children:
        if child.name.startswith("LODs"):
            meshCol = child
        elif child.name.startswith("Hardpoints"):
            hardpointsCol = child
        elif child.name.startswith("Collision"):
            collisionCol = child
        elif child.name.startswith("Floor"):
            floorCol = child
        elif child.name.startswith("Radar/Test/Write"):
            rtwCol = child

    if meshCol == None:
        print("Error. No 'LODs' collection. Aborting!")
        return {'CANCELLED'}

    total_extents = None
    for obj in meshCol.all_objects:
        # skip nested objects. We only want ones that are directly under the collection, which won't have a parent.
        if obj.parent:
            continue
        print(f"Getting extents for: {obj.name}")
        obj_extents = export_msh.get_extents(obj)
        if total_extents == None:
            total_extents = obj_extents
        else:
            print(f'Expanding with extents from {obj.name} {obj_extents.min} to {obj_extents.max}')
            total_extents.expand(obj_extents)

    if total_extents != None:
        lodFile.extents = total_extents
    else:
        lodFile.extents = extents.NullExtents()
        print(f"Error! Computed NO extents for LOD. Was there no geometry??")

    min_distances=[]
    for child in meshCol.objects:
        if not 'distance' in child:
            print(f"Error. LOD Child: {child.name} doesn't have 'distance' CustomProperty. Please set it!")
            return {'CANCELLED'}
        min_distances.append((child, child['distance']))

    sorted_min_distances = sorted(min_distances, key=lambda x: x[1])
    
    last_min=0
    current_lod_index=0
    for item in sorted_min_distances:
        obj=item[0]
        dist=item[1]
        reference = f'mesh/{lodName}_l{current_lod_index}.msh'
        mshPath = f'{appearanceDirname}/{reference}'
        print(f"Should export {reference} with distance: {last_min} - {dist}")
        lodFile.lods[current_lod_index] = [last_min, dist, reference]
        last_min = dist
        current_lod_index += 1
    
        if export_children:            
            if not os.path.exists(os.path.dirname(mshPath)):
                os.makedirs(os.path.dirname(mshPath))
            print(f"Exporting msh {obj.name} to {mshPath}")
            export_msh.export_one(mshPath, extract_dir, obj, flip_uv_vertical)

    if collisionCol:
        lodFile.collision = support.create_extents_from_collection(collisionCol)
    else:
        lodFile.collision = extents.NullExtents()
        
    
    if hardpointsCol:
        for ob in hardpointsCol.all_objects:
            if ob.type == 'EMPTY' and ob.empty_display_type == "ARROWS":
                lodFile.hardpoints.append(support.hardpoint_from_obj(ob))

    if floorCol != None and len(floorCol.all_objects) > 0:
        if len(floorCol.all_objects) > 1:
            print(f"Warning! Floor Collection ({floorCol.name}) has more than 1 object. Will only export the first MESH-type object as the floor!")
        
        floor = None
        for obj in floorCol.all_objects:
            if obj.type == "MESH":
                floor = obj
                print(f"Floor is: {obj.name}")
                break

        if floor == None:
            print(f"Error! None of the objects in Floor Collection ({floorCol.name}) are meshes. No floor will be exported!")
        else:
            lodFile.floor = f'appearance/collision/{floor.name}.flr'
            print(f"Dirname: {appearanceDirname}")
            floorPath = f'{appearanceDirname}/collision/{floor.name}.flr'
            if not os.path.exists(os.path.dirname(floorPath)):
                os.makedirs(os.path.dirname(floorPath))
            print(f"Exporting floor {floor.name} to {floorPath}")
            export_flr.export_one(floorPath, floor, [])

    if rtwCol != None:
        for obj in rtwCol.all_objects:
            if obj.type == "MESH" and obj.name.startswith("Radar"):
                lodFile.radar = support.obj_to_idtl(obj)
            if obj.type == "MESH" and obj.name.startswith("Test"):
                lodFile.testshape = support.obj_to_idtl(obj)
            if obj.type == "MESH" and obj.name.startswith("Write"):
                lodFile.writeshape = support.obj_to_idtl(obj)
    else:
        print(f"Warning! No 'Radar/Test/Write' collection. Won't have any of those.")

    print(f"Assembling final IFF ... ")
    lodFile.write(fullpath)
    now = time.time()
    print(f"Successfully wrote: {fullpath} Duration: " + str(datetime.timedelta(seconds=(now-start))))
    
    apt = swg_types.AptFile(f"{appearanceDirname}/{lodName}.apt", f"appearance/lod/{lodName}.lod")
    apt.write()

    return {'FINISHED'}

def get_extents(collection):

    for child in collection.children:
        if child.name.startswith("LODs"):
            meshCol = child

    if meshCol == None:
        print("Error. No 'LODs' collection. Aborting!")
        return None

    total_extents = None
    for obj in meshCol.objects:
        print(f"Getting extents for: {obj.name}")
        obj_extents = export_msh.get_extents(obj)
        if total_extents == None:
            total_extents = obj_extents
        else:
            print(f'Expanding with extents from {obj.name} {obj_extents.min} to {obj_extents.max}')
            total_extents.expand(obj_extents)

    return total_extents

def avg_vert_position_in_blender(collection):
    for child in collection.children:
        if child.name.startswith("LODs"):
            meshCol = child

    if meshCol == None:
        print("Error. No 'LODs' collection. Aborting!")
        return None

    if len(meshCol.objects) > 0:
        sum = export_msh.avg_vert_position_in_blender(meshCol.objects[0])
        for obj in meshCol.objects[1:0]:
            sum += export_msh.avg_vert_position_in_blender(obj)
        return sum / len(meshCol.objects)
    else:
        return None