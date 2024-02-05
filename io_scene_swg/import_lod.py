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

import base64, os, bpy, time, datetime, math
import bmesh
from mathutils import Matrix, Vector, Color, Quaternion, Euler
from bpy_extras.wm_utils.progress_report import ProgressReport
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from bpy_extras.io_utils import axis_conversion
from bpy_extras import node_shader_utils
from bpy import utils

from . import import_msh
from . import import_flr
from . import swg_types
from . import support
from . import extents
     
def load_new(context,
             filepath,
             *,
             parent=None,
             flip_uv_vertical=False,
             remove_duplicate_verts=True,
             do_floor=True,
             do_collision=True
             ):  

    s=context.preferences.addons[__package__].preferences.swg_root
     
    lodFile = swg_types.LodFile(filepath)
    if not lodFile.load(filepath):
        return {'CANCELLED'}
    
        
    name=os.path.basename(filepath).rsplit( ".", 1 )[ 0 ]
    print(f'Importied lod: {filepath} Flip UV: {flip_uv_vertical}')


    if parent == None:
        parent = bpy.context.scene.collection

    collection = bpy.data.collections.new(name)
    parent.children.link(collection)

    lods = bpy.data.collections.new("LODs")
    collection.children.link(lods)

    hardpoints = bpy.data.collections.new("Hardpoints")
    collection.children.link(hardpoints)
    
    if do_floor:
        floorCol = bpy.data.collections.new("Floor")
        collection.children.link(floorCol)
        if lodFile.floor != None:
            floor_path = support.find_file(lodFile.floor, s)
            if floor_path:
                flr = import_flr.import_flr(context, floor_path, collection=floorCol ) 
            else:
                print(f"Didn't find floor_file: {lodFile.floor}")

    rtw = bpy.data.collections.new("Radar/Test/Write")
    collection.children.link(rtw)

    if lodFile.radar:
        support.add_rtw_mesh(rtw, lodFile.radar, "Radar")
    if lodFile.testshape:
        support.add_rtw_mesh(rtw, lodFile.testshape, "Test")
    if lodFile.writeshape:
        support.add_rtw_mesh(rtw, lodFile.writeshape, "Write")


    for id, lod in lodFile.lods.items():
        lod[2] = os.path.join("appearance",lod[2])
        file = support.find_file(lod[2], s)
        if file == None:
            print(f"Couldn't find mesh path: {lod[2]}")
            continue
        elif file.endswith(".msh"):
            print(f"Importing mesh: {lod[2]} from {file}")
            obj = import_msh.import_msh(context, file, lods, flip_uv_vertical, remove_duplicate_verts, True)
            obj['distance'] = lod[1]
        else:
            print(f"Unhandled LOD Child type: {file}")

    if do_collision:
        collision = bpy.data.collections.new("Collision")
        collection.children.link(collision)
        support.add_collision_to_collection(collision, lodFile.collision)    

    for hpnts in lodFile.hardpoints:     
        support.create_hardpoint_obj(hpnts[12], hpnts[0:12], collection = hardpoints)

    return ('SUCCESS', collection)
