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

from . import vector3D
from . import swg_types
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
    
    for ob_main in objects:
        obs = []
        obs = [(ob_main, ob_main.matrix_world)]
            
        curr_sps_number = 0
        for ob, ob_mat in obs:
            if ob.type != 'MESH':
                continue           
            
            curr_sps_number += 1
            shader="shader/defaultappearance.sht"
            if "Shader" in ob:
                shader = ob["Shader"] 
            if "Collision" in ob:
                col_bytes = base64.b64decode(ob["Collision"])
                newMsh.collision = col_bytes
            
            thisSPS = swg_types.SPS(curr_sps_number, shader, 0, [], [])
            
            me = ob.to_mesh()
            me.transform(global_matrix @ ob_mat)
            #bm = bmesh.new()
            #bm.from_mesh(me)
            #uv_layer = bm.loops.layers.uv.active
            mesh_triangulate(me)
            # i = 0
            # for face in bm.faces:
            #     print(f'New face {i} ...')
            #     i += 1
            #     for vert in face.loops:
            #         # here are the UV coords
            #         print(f' Vert: {vert[uv_layer].uv}')

            #mesh_triangulate(me)
            #me.calc_loop_triangles()

            #If negative scaling, we have to invert the normals...
            if ob_mat.determinant() < 0.0:
                me.flip_normals()
            
            faceuv = len(me.uv_layers) > 0
            if faceuv:
                uv_layer = me.uv_layers.active.data[:]

            me_verts = me.vertices[:]
            loops = me.loops
            
            #print("Mesh:" , str(me))
            face_index_pairs = [(face, index) for index, face in enumerate(me.polygons)]
            uv_face_mapping = [None] * len(face_index_pairs)
            uv_dict = {}
            uv_get = uv_dict.get
            uv_unique_count = 0
            uv0s={}
            if not (len(face_index_pairs) + len(me.vertices)):  # Make sure there is somthing to write
                # clean up
                bpy.data.meshes.remove(me)
                continue  # dont bother with this mesh.             
            
            # in case removing some of these dont get defined.
            # UV
                # in case removing some of these dont get defined.
            uv = f_index = uv_index = uv_key = uv_val = uv_ls = None

            uv_face_mapping = [None] * len(face_index_pairs)

            final_uvs=[]
            uv_dict = {}
            uv_get = uv_dict.get
            i = 0
            for f, f_index in face_index_pairs:
                #print(f'New face: {str(i)}: {f}')
                i += 1
                uv_ls = uv_face_mapping[f_index] = []
                p1 = p2 = p3 = None
                for uv_index, l_index in enumerate(f.loop_indices):
                    #print(f'  New uv: {str(uv_index)}: {l_index}')
                    uv = uv_layer[l_index].uv
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

            del uv_dict, uv, f_index, uv_index, uv_ls, uv_get, uv_key, uv_val
            # Only need uv_unique_count and uv_face_mapping

            # NORMAL, Smooth/Non smoothed.
            # if EXPORT_NORMALS:
            #     no_key = no_val = None
            #     normals_to_idx = {}
            #     no_get = normals_to_idx.get
            #     loops_to_normals = [0] * len(loops)
            #     for f, f_index in face_index_pairs:
            #         for l_idx in f.loop_indices:
            #             no_key = veckey3d(loops[l_idx].normal)
            #             no_val = no_get(no_key)
            #             if no_val is None:
            #                 no_val = normals_to_idx[no_key] = no_unique_count
            #                 fw('vn %.4f %.4f %.4f\n' % no_key)
            #                 no_unique_count += 1
            #             loops_to_normals[l_idx] = no_val
            #     del normals_to_idx, no_get, no_key, no_val
            # else:
            #     loops_to_normals = []
            totverts = totuvco = totno = 1     
            
            for f, f_index in face_index_pairs:
                f_v = [(vi, me_verts[v_idx], l_idx)
                        for vi, (v_idx, l_idx) in enumerate(zip(f.vertices, f.loop_indices))]

                for vi, v, li in f_v:
                    # print("where is this shit: %d %d/%d" % (li, v.index,
                    #                 uv_face_mapping[f_index][vi],
                    #                 ))
                    # print(f' That vert is: {str(v.co)} uv is: {str(final_uvs[uv_face_mapping[f_index][vi]])}')

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
                    swg_v.normal = vector3D.Vector3D(v.normal[0], v.normal[2], v.normal[1])
                    swg_v.texs.append(final_uvs[uv_face_mapping[f_index][vi]])
                    thisSPS.verts.append(swg_v)
            
            # for tri in me.loop_triangles:
            #     #print(f'Tri: {tri}')
            #     thisSPS.tris.append(swg_types.Triangle(tri.vertices[0], tri.vertices[1], tri.vertices[2]))

            # #print("uvs: %s" % str(uv0s))
            # i=0
            # for vert in me_verts:
            #     if extreme_g_x == None or -vert.co[0] > extreme_g_x:
            #         extreme_g_x = -vert.co[0]
            #     if extreme_l_x == None or -vert.co[0] < extreme_l_x:
            #         extreme_l_x = -vert.co[0]
            #     if extreme_g_y == None or vert.co[1] > extreme_g_y:
            #         extreme_g_y = vert.co[1]
            #     if extreme_l_y == None or vert.co[1] < extreme_l_y:
            #         extreme_l_y = vert.co[1]
            #     if extreme_g_z == None or vert.co[2] > extreme_g_z:
            #         extreme_g_z = vert.co[2]
            #     if extreme_l_z == None or vert.co[2] < extreme_l_z:
            #         extreme_l_z = vert.co[2]
            
            #     msh_vert = swg_types.SWGVertex()
            #     msh_vert.pos = swg_types.vector3D.Vector3D(-vert.co[0], vert.co[1], vert.co[2])
            #     msh_vert.normal = swg_types.vector3D.Vector3D(vert.normal[0], vert.normal[2], vert.normal[1])

            #     try:
            #         uv=uv0s[i]
            #         msh_vert.texs = [[uv[0],uv[1]]]
            #         if flip_uv_vertical:
            #             msh_vert.texs[0][1] = (1.0 - msh_vert.texs[0][1])
            #     except:
            #         print(f'Exception writing UV: {i}')

            #     thisSPS.verts.append(msh_vert)
            #     #print('Exported Vert: %d : Pos: %s Norm: %s UV: %s' % (i, msh_vert.pos, msh_vert.normal, msh_vert.texs))
            #     i += 1

            # for i in range(0, len(thisSPS.verts)):
            #     print(f'Vert {i}: {thisSPS.verts[i]}')
            # for i in range(0, len(thisSPS.tris)):
            #     print(f'Tri {i}: {thisSPS.tris[i]}')
            newMsh.spss.append(thisSPS)   
    
    newMsh.extents.append((extreme_g_x, extreme_g_y, extreme_g_z))
    newMsh.extents.append((extreme_l_x, extreme_l_y, extreme_l_z))
    newMsh.write(filepath) 

    return {'FINISHED'}