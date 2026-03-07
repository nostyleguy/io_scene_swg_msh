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
import bpy, base64
from . import swg_types
from . import support
from bpy.props import *
from bpy_extras.io_utils import unpack_list, unpack_face_list
from mathutils import Vector, Quaternion, Matrix, Euler
import math

def import_mgn( context, 
                filepath, 
                *,      
                global_matrix=None):

    swg_root = context.preferences.addons[__package__].preferences.swg_root

    mgn = swg_types.SWGMgn(filepath, swg_root)
    mgn.load()

    mesh_name = filepath.split('\\')[-1].split('.')[0]
    mesh = bpy.data.meshes.new(mesh_name)
        
    edges=[]
    blender_verts = []
    blender_norms = []
    for v in mgn.positions:
        blender_verts.append([v[0],v[1],v[2]])

    for n in mgn.normals:
        blender_norms.append([n[0],n[1],-n[2]])
    
    scene_object = bpy.data.objects.new(mesh_name, mesh)
    context.collection.objects.link(scene_object)

    faces_by_material=[]
    normals=[]
    tris = []
    tris_flat = []
    uvs_flat = []
    for pid, psdt in enumerate(mgn.psdts):
        mat_name = psdt.stripped_shader_name()
        material = None
        
        for mat in bpy.data.materials:
            if mat.name == mat_name:
                material = mat

        if material == None:
            material = bpy.data.materials.new(psdt.stripped_shader_name()) 
        if psdt.real_shader: 
           tex_to_png = context.preferences.addons[__package__].preferences.convert_tex_to_png
           support.configure_material_from_swg_shader(material, psdt.real_shader, swg_root, tex_to_png) 

        mesh.materials.append(material)

        faces_by_material.append([])

        for prim in psdt.prims:
            for tri in prim:
                p1 = psdt.pidx[tri.p3]
                p2 = psdt.pidx[tri.p2]
                p3 = psdt.pidx[tri.p1]
                
                normals.append(blender_norms[psdt.nidx[tri.p3]])
                normals.append(blender_norms[psdt.nidx[tri.p2]])
                normals.append(blender_norms[psdt.nidx[tri.p1]])

                tris_flat.append(p1)
                tris_flat.append(p2)
                tris_flat.append(p3)
                tris.append([p1, p2, p3])
                faces_by_material[pid].append((p1, p2, p3))


                for uv_layer_num in range(0, psdt.num_uvs):                    
                    if psdt.uv_dimensions[uv_layer_num] != 2:
                        print(f"*** Warning *** Not handling UV layer {uv_layer_num} with dimension: {psdt.uv_dimensions[uv_layer_num]}")
                        continue 
                    if len(uvs_flat) <= uv_layer_num:
                        uvs_flat.append([])
                    
                    uvs_flat[uv_layer_num].append(psdt.uvs[uv_layer_num][tri.p3])
                    uvs_flat[uv_layer_num].append(psdt.uvs[uv_layer_num][tri.p2])
                    uvs_flat[uv_layer_num].append(psdt.uvs[uv_layer_num][tri.p1])

    mesh.from_pydata(blender_verts, edges, tris)
    mesh.use_auto_smooth = True
    mesh.normals_split_custom_set(normals)
    mesh.transform(global_matrix)
    
    if mgn.occlusion_zones:
        for i, ozc in enumerate(mgn.occlusion_zones):
            face_map = scene_object.face_maps.new(name=ozc[0])
            face_map.add(ozc[1])   

    for flist in mesh.polygons: 
        for id, face_list in enumerate(faces_by_material):
            if flist.vertices[:] in face_list:
                flist.material_index = id

    for i, uvs in enumerate(uvs_flat):
        print(f'UV Layer: {i} -- lengths of UVs ({len(uvs)}) and Tri indecies ({len(tris_flat)})')
        if len(uvs) != len(tris_flat):
            print(f'*** WARNING *** UV Layer: {i} -- Unmatched lengths of UVs ({len(uvs)}) and Tri indecies ({len(tris_flat)}). Skipping!')
            continue

        uvlayer = mesh.uv_layers.new(name=f'UVMap-{str(i)}')
        mesh.uv_layers.active = uvlayer
        
        print(f"Adding uv layer with size: {str(len(uvlayer.data))} for mesh with {str(len(mesh.polygons))} tris")
        for ind, vert in enumerate(tris_flat):
            try:
                uv = [uvs[ind][0], 1 - uvs[ind][1]]
                uvlayer.data[ind].uv = uv
            except Exception as e:
                print(f"Exception importing UVs: " + str(e))
    vgs = {}
    for i, bone in enumerate(mgn.joint_names):
        vg = scene_object.vertex_groups.new(name=bone)
        vgs[i] = vg

    for i, vertex_weights in enumerate(mgn.vertex_weights):
        sum=0
        for weight in vertex_weights:
            #if sum + weight[1] > 1.0:
            #    weight[1] = (1.0 - sum)
            #    print(f"Capped bone weight contribution of: {i} {weight[0]} to {weight[1]}!")
            vgs[weight[0]].add([i], weight[1], 'ADD')
    
    scene_object.shape_key_add(name='Basis')
    for i, blend in enumerate(mgn.blends):
        sk = scene_object.shape_key_add(name=blend.name)
        for vert in blend.positions:
            id = vert[0]
            delta = [vert[1][0], vert[1][1], -vert[1][2]]
            delta_v = Vector(delta)
            sk.data[id].co = scene_object.data.vertices[id].co + (global_matrix @ delta_v)
    
    for i, skel in enumerate(mgn.skeletons):
        scene_object[f'SKTM_{i}'] = skel

    #print(f"Occulusions: {str(mgn.occlusions)}")
    for zone in mgn.occlusions:
        scene_object["OZN_"+zone[0]] = zone[2]

    scene_object[f'OCC_LAYER'] = mgn.occlusion_layer

    if mgn.binary_hardpoints:
        scene_object["HPTS"] = base64.b64encode(mgn.binary_hardpoints).decode('ASCII')

    if mgn.binary_trts:
        scene_object["TRTS"] = base64.b64encode(mgn.binary_trts).decode('ASCII')

    if mgn.static_hardpoints:
        for hpnt in mgn.static_hardpoints:
            hpntadded = bpy.data.objects.new(name=hpnt.name, object_data=None)
            location = Vector([-hpnt.position[0], hpnt.position[1], hpnt.position[2]])
            orientation =  Quaternion(hpnt.orientation).to_euler()
            orientation = Euler((orientation.x, orientation.y + math.radians(180.0), orientation.z),'XYZ')
            hpntadded.matrix_world = global_matrix @ Matrix.LocRotScale(location, orientation, Vector([1, 1, 1]))
            hpntadded.empty_display_type = "ARROWS"
            hpntadded.empty_display_size = 0.1 #small display
            hpntadded.parent = scene_object
            bpy.context.collection.objects.link(hpntadded)

    if mgn.dynamic_hardpoints:
        for hpnt in mgn.dynamic_hardpoints:
            hpntadded = bpy.data.objects.new(name=hpnt.name, object_data=None)
            location = Vector([-hpnt.position[0], hpnt.position[1], hpnt.position[2]])
            orientation =  Quaternion(hpnt.orientation).to_euler()
            orientation = Euler((orientation.x, orientation.y + math.radians(180.0), orientation.z),'XYZ')
            hpntadded.matrix_world = global_matrix @ Matrix.LocRotScale(location, orientation, Vector([1, 1, 1]))
            hpntadded.empty_display_type = "PLAIN_AXES"
            hpntadded.empty_display_size = 0.1 #small display
            hpntadded.parent = scene_object
            bpy.context.collection.objects.link(hpntadded)

    
    mesh.validate()
    mesh.update()   
    print(f"After validate/update. Mesh from {str(len(tris))} tris now has polygons: {str(len(mesh.polygons))}")

    return {'FINISHED'}