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
import time, datetime, array, functools
from . import vector3D
from . import swg_types
from . import vertex_buffer_format
from . import data_types

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

def save(context,
         filepath,
         *,
         global_matrix=None,
         flip_uv_vertical=False
         ):
         
    s=context.preferences.addons[__package__].preferences.swg_root
    #s="E:/SWG_Legends_Dev/clientside_git_repo/"
    #print(f"Root: {str(s)}")

    newMsh = swg_types.SWGMesh(filepath, s)
    start = time.time()
    print(f'Exporting msh: {filepath} Flip UV: {flip_uv_vertical}')

    def veckey2d(n, v):
        return round(n[0], 4), round(n[1], 4), round(n[2], 4), round(v[0], 4), round(v[1], 4) 
    
    objects = context.selected_objects

    if not (len(objects) == 1):
        return {'CANCELLED'}

    current_obj = None
    for ob_main in objects:
        obs = [(ob_main, ob_main.matrix_world)]
        for ob, ob_mat in obs:
            if ob.type != 'MESH':
                return False
            else:
                current_obj = ob
                if hasattr(current_obj.data, "transform"):
                    current_obj.data.transform(ob_mat)
                
    me = current_obj.to_mesh() 
    me.transform(global_matrix @ ob_mat)
    mesh_triangulate(me)    
    me.calc_normals_split()

    t_ln = array.array(data_types.ARRAY_FLOAT64, (0.0,)) * len(me.loops) * 3
    me.loops.foreach_get("normal", t_ln)
    normals = list(map(list, zip(*[iter(t_ln)]*3)))   
    uv_maps=[]
    
    for layer in me.uv_layers:
        uv_maps.append(layer.data[:])

    t_ln = array.array(data_types.ARRAY_FLOAT64, [0.0,]) * len(me.loops) * 3
    uv_names = [uvlayer.name for uvlayer in me.uv_layers]

    for name in uv_names:
        me.calc_tangents(uvmap=name)

    extreme_g_x = None
    extreme_g_y = None
    extreme_g_z = None
            
    extreme_l_x = None
    extreme_l_y = None
    extreme_l_z = None

    #If negative scaling, we have to invert the normals...
    if ob_mat.determinant() < 0.0:
        me.flip_normals()

    faces_by_material = {}
    for polygon in me.polygons:
        if not polygon.material_index in faces_by_material:
            faces_by_material[polygon.material_index] = []   
        faces_by_material[polygon.material_index].append(polygon)


    for mat_index, face_list in faces_by_material.items():

        material = current_obj.material_slots[mat_index].material            
        thisSPS = swg_types.SPS(mat_index, f'shader/{material.name}.sht', 0, [], [])

        uvSets = 1
        if "UVSets" in material:
            uvSets = material["UVSets"]

        doDOT3 = False
        if "DOT3" in material:
            doDOT3 = material["DOT3"]
        thisSPS.flags = vertex_buffer_format.setPosition(thisSPS.flags, True)
        thisSPS.flags = vertex_buffer_format.setNormal(thisSPS.flags, True)
        thisSPS.flags = vertex_buffer_format.setNumberOfTextureCoordinateSets(thisSPS.flags, uvSets)

        doColor0 = "Color0" in material and (material["Color0"] == 1)
        thisSPS.flags = vertex_buffer_format.setColor0(thisSPS.flags, doColor0)
        doColor1 = "Color1" in material and (material["Color1"] == 1)
        thisSPS.flags = vertex_buffer_format.setColor1(thisSPS.flags, doColor1)

        for i in range(0, uvSets):
            thisSPS.flags = vertex_buffer_format.setTextureCoordinateSetDimension(thisSPS.flags, i, 2)

        if doDOT3:
            uv_dim = vertex_buffer_format.getNumberOfTextureCoordinateSets(thisSPS.flags) + 1
            thisSPS.flags = vertex_buffer_format.setNumberOfTextureCoordinateSets(thisSPS.flags, uv_dim)
            thisSPS.flags = vertex_buffer_format.setTextureCoordinateSetDimension(thisSPS.flags, uv_dim - 1, 4)

        unique_verts={}
        last_unique_vert_index=0
        for face_index, face in enumerate(face_list):

            p1 = p2 = p3 = None
            for uv_index, l_index in enumerate(face.loop_indices):
                v = me.vertices[face.vertices[uv_index]]
                normal = normals[l_index]

                test_uv = uv_maps[0][l_index].uv
                rounded = face.vertices[uv_index], veckey2d(normal, test_uv)
                if rounded not in unique_verts:
                    unique_verts[rounded] = last_unique_vert_index
                    last_unique_vert_index += 1

                    swg_v = swg_types.SWGVertex()
                    swg_v.pos = vector3D.Vector3D(-v.co[0], v.co[1], v.co[2])
                    swg_v.normal = vector3D.Vector3D(-normal[0], normal[1], normal[2])

                    if doColor0:
                        swg_v.color0 = me.vertex_colors["color0"].data[l_index].color                        

                    if doColor1:
                        swg_v.color1 = me.vertex_colors["color1"].data[l_index].color

                    for i in range(0, uvSets):
                        uv = me.uv_layers[i].data[l_index].uv

                        if flip_uv_vertical:
                            uv[1] = (1.0 - uv[1])

                        swg_v.texs.append(uv)

                    if doDOT3:
                        loop = me.loops[l_index]
                        tang = loop.tangent
                        swg_v.texs.append([ -tang[0], tang[1], tang[2], loop.bitangent_sign])

                    thisSPS.verts.append(swg_v)

                if p1 == None:
                    p1 = unique_verts[rounded]
                elif p2 == None:
                    p2 = unique_verts[rounded]
                elif p3 == None:
                    p3 = unique_verts[rounded]
                    thisSPS.tris.append(swg_types.Triangle(p3, p2, p1))
                    p1 = p2 = p3 = None

                if extreme_g_x == None or -v.co[0] > extreme_g_x:
                    extreme_g_x = -v.co[0]
                if extreme_l_x == None or -v.co[0] < extreme_l_x:
                    extreme_l_x = -v.co[0]
                if extreme_g_y == None or v.co[1] > extreme_g_y:
                    extreme_g_y = v.co[1]
                if extreme_l_y == None or v.co[1] < extreme_l_y:
                    extreme_l_y = v.co[1]
                if extreme_g_z == None or v.co[2] > extreme_g_z:
                    extreme_g_z = v.co[2]
                if extreme_l_z == None or v.co[2] < extreme_l_z:
                    extreme_l_z = v.co[2]        
            
        print(f"SPS {str(thisSPS.no)}: Unique Verts: {str(len(unique_verts))} UV Channels: {str(vertex_buffer_format.getNumberOfTextureCoordinateSets(thisSPS.flags))} Has flags {str(thisSPS.flags)}") 
        newMsh.spss.append(thisSPS)            
    
    newMsh.extents.append((extreme_g_x, extreme_g_y, extreme_g_z))
    newMsh.extents.append((extreme_l_x, extreme_l_y, extreme_l_z))

    for ob in bpy.data.objects: 
        if ob.parent == current_obj: 
            if ob.type != 'MESH' and ob.type == 'EMPTY' and ob.empty_display_type == "ARROWS":
                newMsh.hardpoints.append([
                ob.matrix_world[0][0], ob.matrix_world[0][1], ob.matrix_world[0][2], ob.matrix_world[0][3],
                ob.matrix_world[2][0], ob.matrix_world[2][1], ob.matrix_world[2][2], ob.matrix_world[2][3],
                ob.matrix_world[1][0], ob.matrix_world[1][1], ob.matrix_world[1][2], ob.matrix_world[1][3], ob.name])

    if "Collision" in current_obj:
        col_bytes = base64.b64decode(current_obj["Collision"])
        newMsh.collision = col_bytes
    if "Floor" in current_obj:
        newMsh.floor = current_obj["Floor"]

    print(f"Assembling final IFF ... ")
    newMsh.write(filepath)
    now = time.time()
    print(f"Successfully wrote: {filepath} Duration: " + str(datetime.timedelta(seconds=(now-start))))

    return {'FINISHED'}