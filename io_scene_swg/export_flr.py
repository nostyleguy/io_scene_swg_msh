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
import mathutils

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



def export_flr(context,
         filepath,
         global_matrix=None
         ):

    objects = context.selected_objects

    if len(objects) == 0:
        return {'CANCELLED'}

    portal_objects = [obj for obj in bpy.context.scene.objects if "PORTAL" in obj.name]
    
    current_obj = None
    for ob_main in objects:
        obs = [(ob_main, ob_main.matrix_world)]
        for ob, ob_mat in obs:
            if ob.type != 'MESH':
                continue
            else:
                dirname = os.path.dirname(filepath)
                fullpath = os.path.join(dirname, ob.name+".msh")
                result = export_one(fullpath, context, ob, ob_mat, global_matrix, portal_objects)
                if not 'FINISHED' in result:
                    return {'CANCELLED'}
    return {'FINISHED'}

def export_one(fullpath, context, current_obj, ob_mat, global_matrix, portal_objects):    
    start = time.time()
    dirname = os.path.dirname(fullpath)
    fullpath = os.path.join(dirname, current_obj.name+".flr")
    flr = swg_types.FloorFile(fullpath)

    me = current_obj.to_mesh() 
    #me.transform(global_matrix @ ob_mat)

    # Lets find the tris in the "fallthrough" face map first..
    FALLTHROUGH_MAP_INDEX=None
    if len(current_obj.face_maps) > 0:    
        face_maps = current_obj.face_maps 
        for map in face_maps:
            if map.name.lower() == "fallthrough":
                FALLTHROUGH_MAP_INDEX = map.index
    if FALLTHROUGH_MAP_INDEX == None:
        print("Warning! No 'fallthrough' FaceMap found, no triangles can be marked as fallthrough!")
    else:
        print(f"{current_obj.name} has 'fallthrough' facemap. Good to go")

    face_maps_by_index=[m_face_map.value for m_face_map in current_obj.data.face_maps.active.data]

    print(f"Portal objects: {', '.join([obj.name for obj in portal_objects])}")
    for v in me.vertices:
        flr.verts.append([-v.co[0], v.co[2], -v.co[1]])

    edge_types={}
    for edge in me.edges:  
        reversed=list(edge.vertices)
        reversed.reverse()
        if edge.use_freestyle_mark == True:
            edge_types[tuple(edge.vertices)] = swg_types.FloorTri.Crossable
            edge_types[tuple(reversed)] = swg_types.FloorTri.Crossable
        elif edge.use_seam == True:
            edge_types[tuple(edge.vertices)] = swg_types.FloorTri.Uncrossable
            edge_types[tuple(reversed)] = swg_types.FloorTri.Uncrossable
        elif edge.use_edge_sharp == True:
            edge_types[tuple(edge.vertices)] = swg_types.FloorTri.WallTop
            edge_types[tuple(reversed)] = swg_types.FloorTri.WallTop               
        elif edge.crease > 0.9:
            edge_types[tuple(edge.vertices)] = swg_types.FloorTri.WallBase
            edge_types[tuple(reversed)] = swg_types.FloorTri.WallBase
        else:
            edge_types[tuple(edge.vertices)] = swg_types.FloorTri.Uncrossable
            edge_types[tuple(reversed)] = swg_types.FloorTri.Uncrossable


    tested=0
    for t1 in me.polygons:
        if(len(t1.vertices) != 3):
            print(f"Error. Triangle {t1.index} has {len(t1.vertices)} vertices. Only triangles supported!")
            return {'CANCELLED'}

        ft = swg_types.FloorTri()
        ft.index = t1.index
        ft.corner1 = t1.vertices[0]
        # ft.corner2 = t1.vertices[1]
        # ft.corner3 = t1.vertices[2]
        ft.corner2 = t1.vertices[2]
        ft.corner3 = t1.vertices[1]

        # t1e1 = set([t1.vertices[0],t1.vertices[1]])
        # t1e2 = set([t1.vertices[1],t1.vertices[2]])
        # t1e3 = set([t1.vertices[2],t1.vertices[0]])
        t1e1 = set([t1.vertices[0],t1.vertices[2]])
        t1e2 = set([t1.vertices[2],t1.vertices[1]])
        t1e3 = set([t1.vertices[1],t1.vertices[0]])

        # find the edge types
        ft.edgeType1 = edge_types[tuple(t1e1)]
        ft.edgeType2 = edge_types[tuple(t1e2)]
        ft.edgeType3 = edge_types[tuple(t1e3)]

        for t2 in [x for x in me.polygons if x.index != t1.index]:
            # t2e1 = set([t2.vertices[0],t2.vertices[1]])
            # t2e2 = set([t2.vertices[1],t2.vertices[2]])
            # t2e3 = set([t2.vertices[2],t2.vertices[0]])
            t2e1 = set([t2.vertices[0],t2.vertices[2]])
            t2e2 = set([t2.vertices[2],t2.vertices[1]])
            t2e3 = set([t2.vertices[1],t2.vertices[0]])

            if t1e1 in [t2e1, t2e2, t2e3]:
                ft.nindex1 = t2.index
            if t1e2 in [t2e1, t2e2, t2e3]:
                ft.nindex2 = t2.index
            if t1e3 in [t2e1, t2e2, t2e3]:
                ft.nindex3 = t2.index

        ft.normal = [t1.normal.x, -t1.normal.z, -t1.normal.y]
        ft.fallthrough = (face_maps_by_index[t1.index] == FALLTHROUGH_MAP_INDEX)   

        for portalIndex, portalObj in enumerate(portal_objects):
            if portalObj.type != 'MESH':
                print(f"{portalObj.name} is not a MESH, skipping!")
                continue
            else:
                if (ft.nindex1 != -1) and (ft.nindex2 != -1) and (ft.nindex3 != -1):
                    # non-boundary triangle, skip
                    continue

                portalMesh = portalObj.to_mesh() 
                for portalTri in portalMesh.polygons:
                    portalVerts = [portalMesh.vertices[p].co for p in portalTri.vertices] 
                    floortVerts = [me.vertices[p].co for p in t1.vertices]

                    if(mathutils.geometry.intersect_tri_tri_2d(floortVerts[0], floortVerts[1], floortVerts[2], portalVerts[0], portalVerts[1], portalVerts[2])):
                        print(f"Intersection found: floorTri {t1.index}, portalMesh {portalObj.name}: tri {portalTri.index}")
                        
                        closestPt1 = mathutils.geometry.closest_point_on_tri(floortVerts[0], portalVerts[0], portalVerts[1], portalVerts[2])
                        closestPt2 = mathutils.geometry.closest_point_on_tri(floortVerts[1], portalVerts[0], portalVerts[1], portalVerts[2])
                        closestPt3 = mathutils.geometry.closest_point_on_tri(floortVerts[2], portalVerts[0], portalVerts[1], portalVerts[2])
                        
                        dist0 = math.fabs(mathutils.geometry.distance_point_to_plane(floortVerts[0], portalVerts[0], portalTri.normal))
                        #print(f" Distance0: {dist0}")
                        dist1 = math.fabs(mathutils.geometry.distance_point_to_plane(floortVerts[1], portalVerts[0], portalTri.normal))
                        #print(f" Distance1: {dist1}")
                        dist2 = math.fabs(mathutils.geometry.distance_point_to_plane(floortVerts[2], portalVerts[0], portalTri.normal))
                        #print(f" Distance2: {dist2}")

                        if(dist0 < 0.01 and dist1 < 0.01):
                            ft.portalId3 = portalIndex
                            print(f"edge3 ({floortVerts[0]}, {floortVerts[1]}) is touching portal {portalIndex}!")
                        if(dist1 < 0.01 and dist2 < 0.01):
                            ft.portalId2 = portalIndex
                            print(f"edge2 ({floortVerts[1]}, {floortVerts[2]}) is touching portal {portalIndex}!")
                        if(dist2 < 0.01 and dist0 < 0.01):
                            ft.portalId1 = portalIndex
                            print(f"edge1 ({floortVerts[2]}, {floortVerts[0]}) is touching portal {portalIndex}!")
                        
                        # if (ft.nindex1 == -1):
                        #     tested += 1
                        #     edgePair = list(t1e1)
                        #     vA = me.vertices[edgePair[0]].co
                        #     vB = me.vertices[edgePair[1]].co
                        #     print(f"Testing floorTri {t1.index}, edge: {1}, nindex1: {ft.nindex1}: {edgePair} ({vA}, {vB}) against portalMesh {portalObj.name}: tri {portalTri.index}")
                        
                        # if (ft.nindex2 == -1):
                        #     tested += 1
                        #     edgePair = list(t1e2)
                        #     vA = me.vertices[edgePair[0]].co
                        #     vB = me.vertices[edgePair[1]].co
                        #     print(f"Testing floorTri {t1.index}, edge {2}, nindex2: {ft.nindex2}: {edgePair} ({vA}, {vB}) against portalMesh {portalObj.name}: tri {portalTri.index}")
                        
                        # if (ft.nindex3 == -1):
                        #     tested += 1
                        #     edgePair = list(t1e3)
                        #     vA = me.vertices[edgePair[0]].co
                        #     vB = me.vertices[edgePair[1]].co
                        #     print(f"Testing floorTri {t1.index}, edge {3}, nindex3: {ft.nindex3}: {edgePair} ({vA}, {vB}) against portalMesh {portalObj.name}: tri {portalTri.index}")

                        # for i, edgePair in enumerate([list(l) for l in [t1e1, t1e2, t1e3]]):
                        #     vA = me.vertices[edgePair[0]].co
                        #     vB = me.vertices[edgePair[1]].co
                        #     tested += 1
                        # for j in range(0, len(portalVerts)):
                        #     pA = portalVerts[j]
                        #     pB = portalVerts[(j+1)%len(portalVerts)]
                        #     print(f"   Against Portal Edge: ({pA}, {pB})")

        flr.tris.append(ft)

    print(f"Tested edges: {tested}")
    flr.write()
    now = time.time()
    print(f"Successfully wrote: {fullpath} Duration: " + str(datetime.timedelta(seconds=(now-start))))

    return {'FINISHED'}