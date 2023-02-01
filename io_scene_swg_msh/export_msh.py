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
import time, datetime, array
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
         use_selection=True,
         global_matrix=None,
         flip_uv_vertical=False
         ):
    
    start = time.time()
    print(f'Exporting msh: {filepath} Flip UV: {flip_uv_vertical}')

    def veckey2d(v):
        return round(v[0], 4), round(v[1], 4)

    newMsh = swg_types.SWGMesh(filepath)
    scene = context.scene
    
    if use_selection:
        objects = context.selected_objects
    else:
        objects = scene.objects
    
    #gather information about extrema
    extreme_g_x = None
    extreme_g_y = None
    extreme_g_z = None
            
    extreme_l_x = None
    extreme_l_y = None
    extreme_l_z = None    
            
    curr_sps_number = 0
    for ob_main in objects:
        obs = [(ob_main, ob_main.matrix_world)]
        for ob, ob_mat in obs:
            if ob.type != 'MESH':
                if ob.type == 'EMPTY':
                    if ob.empty_display_type == "ARROWS":
                        #this is a hardpoint, pls
                        newMsh.hardpoints.append([
                        ob.matrix_world[0][0], ob.matrix_world[0][1], ob.matrix_world[0][2], ob.matrix_world[0][3],
                        ob.matrix_world[2][0], ob.matrix_world[2][1], ob.matrix_world[2][2], ob.matrix_world[2][3],
                        ob.matrix_world[1][0], ob.matrix_world[1][1], ob.matrix_world[1][2], ob.matrix_world[1][3], ob.name])
                    if ob.empty_display_type == "CUBE":
                        print("found empty-cube, collision?")
                        print(ob.matrix_world)
                    if ob.empty_display_type == "SPHERE":
                        print("found empty-sphere, collision?")
                        print(ob.matrix_world)
                        newMsh.realCollision.append([
                        ob.matrix_world[0][0], ob.matrix_world[0][1], ob.matrix_world[0][2], ob.matrix_world[0][3],
                        ob.matrix_world[2][0], ob.matrix_world[2][1], ob.matrix_world[2][2], ob.matrix_world[2][3],
                        ob.matrix_world[1][0], ob.matrix_world[1][1], ob.matrix_world[1][2], ob.matrix_world[1][3], "sphere"])
                continue
            

            #If negative scaling, we have to invert the normals...
            if ob_mat.determinant() < 0.0:
                me.flip_normals()

            curr_sps_number += 1

            shader="shader/defaultappearance.sht"
            if "Shader" in ob:
                shader = ob["Shader"] 
            if "Collision" in ob:
                col_bytes = base64.b64decode(ob["Collision"])
                newMsh.collision = col_bytes

            uvSets = 1
            if "UVSets" in ob:
                uvSets = ob["UVSets"]

            doDOT3 = False
            if "DOT3" in ob:
                doDOT3 = ob["DOT3"]
            
            thisSPS = swg_types.SPS(curr_sps_number, shader, 0, [], [])
            
            thisSPS.flags = vertex_buffer_format.setPosition(thisSPS.flags, True)
            thisSPS.flags = vertex_buffer_format.setNormal(thisSPS.flags, True)
            thisSPS.flags = vertex_buffer_format.setNumberOfTextureCoordinateSets(thisSPS.flags, uvSets)
            for i in range(0, uvSets):
                thisSPS.flags = vertex_buffer_format.setTextureCoordinateSetDimension(thisSPS.flags, i, 2)

            if doDOT3:
                uv_dim = vertex_buffer_format.getNumberOfTextureCoordinateSets(thisSPS.flags) + 1
                thisSPS.flags = vertex_buffer_format.setNumberOfTextureCoordinateSets(thisSPS.flags, uv_dim)
                thisSPS.flags = vertex_buffer_format.setTextureCoordinateSetDimension(thisSPS.flags, uv_dim - 1, 4)
            
            print(f"SPS {str(thisSPS.no)}: UVs: {str(vertex_buffer_format.getNumberOfTextureCoordinateSets(thisSPS.flags))} Has flags {str(thisSPS.flags)}")

            me = ob.to_mesh()
            me.transform(global_matrix @ ob_mat)

            mesh_triangulate(me)  
    
            me.calc_normals_split()

            t_ln = array.array(data_types.ARRAY_FLOAT64, (0.0,)) * len(me.loops) * 3
            me.loops.foreach_get("normal", t_ln)
            normals = list(map(list, zip(*[iter(t_ln)]*3)))

            tang_lib = []
            me.calc_tangents()
            t_ln = array.array(data_types.ARRAY_FLOAT64, [0.0,]) * len(me.loops) * 3
            uv_names = [uvlayer.name for uvlayer in me.uv_layers]
            for name in uv_names:
                print(f"Did tangents for UV map: {name}")
                me.calc_tangents(uvmap=name)
            for idx, uvlayer in enumerate(me.uv_layers):
                name = uvlayer.name
                me.loops.foreach_get("tangent", t_ln)  
                tangents = list(map(list, zip(*[iter(t_ln)]*3)))

            for t in tangents:
                t.insert(3, 1.0)
                tang_lib.append(t)
            
            faceuv = len(me.uv_layers) > 0
            if faceuv:
                uv_layer = me.uv_layers.active.data[:]
                #print(f'UVs: {len(me.uv_layers.active.data)}')

            me_verts = me.vertices[:]
            loops = me.loops
            
            #print("Mesh:" , str(me))
            face_index_pairs = [(face, index) for index, face in enumerate(me.polygons)]
            uv_face_mapping = [None] * len(face_index_pairs)
            #print(f"Face Index Pairs: {str(face_index_pairs)}")
            uv_dict = {}
            uv_get = uv_dict.get
            uv_unique_count = 0
            if not (len(face_index_pairs) + len(me.vertices)):  # Make sure there is somthing to write
                # clean up
                bpy.data.meshes.remove(me)
                continue  # dont bother with this mesh.             
            
            
            uv = f_index = uv_index = uv_key = uv_val = uv_ls = None

            uv_face_mapping = [None] * len(face_index_pairs)

            final_uvs=[]
            uv_dict = {}
            uv_get = uv_dict.get
            i = 0

            vert5d = set()
            for f, f_index in face_index_pairs:
                #print(f'New face: {str(i)}: {f}')
                i += 1
                uv_ls = uv_face_mapping[f_index] = []
                p1 = p2 = p3 = None
                for uv_index, l_index in enumerate(f.loop_indices):
                    uv = uv_layer[l_index].uv
                    #print(f' Vert: {loops[l_index].vertex_index} is UV: {str(l_index)}  New uv: {str(uv_index)}: {uv}')
                    vert5d.add((loops[l_index].vertex_index, l_index))
                    if flip_uv_vertical:
                        uv[1] = 1 - uv[1]
                    # include the vertex index in the key so we don't share UV's between vertices,
                    # allowed by the OBJ spec but can cause issues for other importers, see: T47010.

                    # this works too, shared UV's for all verts
                    #~ uv_key = veckey2d(uv)
                    uv_key = loops[l_index].vertex_index, veckey2d(uv)

                    uv_val = uv_get(uv_key)
                    if uv_val is None:
                        uv_val = uv_dict[uv_key] = uv_unique_count
                        #print('vt %.6f %.6f\n' % uv[:])
                        uv_unique_count += 1
                        final_uvs.append(uv)
                    uv_ls.append(uv_val)
                    #print(f'Added uv_ls: {uv_val}')
                    if p1 == None:
                        p1 = l_index
                    elif p2 == None:
                        p2 = l_index
                    elif p3 == None:
                        p3 = l_index
                        thisSPS.tris.append(swg_types.Triangle(p3, p2, p1))
                        p1 = p2 = p3 = None
            #print(f'Unique Verts: {str(vert5d)}')
            del uv_dict, uv, f_index, uv_index, uv_ls, uv_get, uv_key, uv_val               
            
            for f, f_index in face_index_pairs:
                f_v = [(vi, me_verts[v_idx], l_idx)
                        for vi, (v_idx, l_idx) in enumerate(zip(f.vertices, f.loop_indices))]

                for vi, v, li in f_v:

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

                    swg_v = swg_types.SWGVertex()
                    swg_v.pos = vector3D.Vector3D(-v.co[0], v.co[1], v.co[2])
                    #swg_v.normal = vector3D.Vector3D(-v.normal[0], v.normal[1], v.normal[2])
                    swg_v.normal = vector3D.Vector3D(-normals[li][0], normals[li][1], normals[li][2])
                    for i in range(0, uvSets):                        
                        swg_v.texs.append(final_uvs[uv_face_mapping[f_index][vi]])

                    if doDOT3:
                        swg_v.texs.append([-tang_lib[li][0],tang_lib[li][1],tang_lib[li][2],tang_lib[li][3]])
                        print(f"Using tang: {str(li)} from face {str(f_v)}")

                    thisSPS.verts.append(swg_v)
            newMsh.spss.append(thisSPS)
    
    newMsh.extents.append((extreme_g_x, extreme_g_y, extreme_g_z))
    newMsh.extents.append((extreme_l_x, extreme_l_y, extreme_l_z))
       
    print(f"Assembling final IFF ... ")
    newMsh.write(filepath)
    now = time.time()
    print(f"Successfully wrote: {filepath} Duration: " + str(datetime.timedelta(seconds=(now-start))))

    return {'FINISHED'}
