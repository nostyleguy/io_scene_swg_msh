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

from bpy_extras.io_utils import unpack_list
from bpy_extras.wm_utils.progress_report import ProgressReport
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from bpy_extras import node_shader_utils
from bpy import utils

from . import import_msh
from . import swg_types
from . import support
from . import extents

def rotate_object(obj, rot_mat):
    # decompose world_matrix's components, and from them assemble 4x4 matrices
    orig_loc, orig_rot, orig_scale = obj.matrix_world.decompose()

    orig_loc_mat   = Matrix.Translation(orig_loc)
    orig_rot_mat   = orig_rot.to_matrix().to_4x4()
    orig_scale_mat = (Matrix.Scale(orig_scale[0],4,(1,0,0)) @ 
                      Matrix.Scale(orig_scale[1],4,(0,1,0)) @ 
                      Matrix.Scale(orig_scale[2],4,(0,0,1)))

    obj.matrix_world = orig_loc_mat @ rot_mat @ orig_rot_mat @ orig_scale_mat
     
def load_new(context,
             filepath,
             *,     
             global_matrix=None,
             parent=None,
             flip_uv_vertical=False,
             remove_duplicate_verts=True,
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

    collision = bpy.data.collections.new("Collision")
    collection.children.link(collision)
    rtw = bpy.data.collections.new("Radar/Test/Write")
    collection.children.link(rtw)

    if lodFile.radar:
        support.add_rtw_mesh(rtw, lodFile.radar, global_matrix, "Radar")
    if lodFile.testshape:
        support.add_rtw_mesh(rtw, lodFile.testshape, global_matrix, "Test")
    if lodFile.writeshape:
        support.add_rtw_mesh(rtw, lodFile.writeshape, global_matrix, "Write")


    for id, lod in lodFile.lods.items():
        lod[2] = os.path.join("appearance",lod[2])
        file = support.find_file(lod[2], s)
        if file == None:
            print(f"Couldn't find mesh path: {lod[2]}")
            continue
        elif file.endswith(".msh"):
            print(f"Importing mesh: {lod[2]} from {file}")
            obj = import_msh.import_msh(context,  file, global_matrix, lods)
        else:
            print(f"Unhandled LOD Child type: {file}")

    support.add_collision_to_collection(collision, lodFile.collision, global_matrix)
    

    for hpnts in lodFile.hardpoints:
        hpntadded = bpy.data.objects.new(name=hpnts[12], object_data=None)
        hpntadded.matrix_world = [
            [hpnts[0], hpnts[8], hpnts[4], 0.0],
            [hpnts[1], hpnts[9], hpnts[5], 0.0],
            [hpnts[2], hpnts[10], hpnts[6], 0.0],
            [hpnts[3], hpnts[11], hpnts[7], 0.0],
        ]
        hpntadded.empty_display_type = "ARROWS"
        #hpntadded.empty_display_size = 0.1
        hpntadded.location[1] *= -1
        hpntadded.rotation_euler[2] +=  math.radians(180.0)

        #hpntadded.parent = obj
        hardpoints.objects.link(hpntadded)

    # obj["Collision"] = base64.b64encode(msh.collision).decode('ASCII')
    # # collisionObj = bpy.data.objects.new(name="COLLISION", object_data=None)
    # # collisionObj.empty_display_type = "SPHERE"
    # # collisionObj.scale=(3,1,2)
    # # collisionObj.empty_display_size = 1
    # # collisionObj.parent = obj
    # #bpy.context.collection.objects.link(collisionObj)

    # obj["Floor"] = msh.floor

    # print(f"Success!")

    return {'FINISHED'}