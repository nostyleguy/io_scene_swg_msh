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
from . import support
import mathutils

from mathutils import Matrix, Vector, Color
from bpy_extras import io_utils, node_shader_utils

from bpy_extras.wm_utils.progress_report import (
    ProgressReport,
    ProgressReportSubstep,
)

def export_flr(context, filepath):

    objects = context.selected_objects

    if len(objects) == 0:
        return {'CANCELLED'}

    for ob in objects:
        if ob.type != 'MESH':
            continue
        else:
            dirname = os.path.dirname(filepath)
            fullpath = os.path.join(dirname, ob.name+".flr")
            result, flr = export_one(fullpath, ob, [])
            if not 'FINISHED' in result:
                return {'CANCELLED'}
    return {'FINISHED'}

def export_one(fullpath, current_obj, portal_objects, use_object_name=True):    
    start = time.time()    
    print(f'Exporting Flr: {fullpath}')

    # List of global (building-wide) portal idecies, indexed by the local (cell) portal index. 
    # A cell with 2 portals; IDs 2 and 3, will be '[2,3]' so we can convert the local portal index to the global one easily
    globalPortalIndecies=[]
    for p in portal_objects:
        globalPortalIndecies.append(p[1])


    if use_object_name:
        dirname = os.path.dirname(fullpath)
        fullpath = os.path.join(dirname, current_obj.name+".flr")
        
    if not os.path.exists(os.path.dirname(fullpath)):
                os.makedirs(os.path.dirname(fullpath))

    flr = swg_types.FloorFile(fullpath)

    me = current_obj.to_mesh()

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

    face_maps_by_index=None
    if current_obj.data.face_maps.active:
        face_maps_by_index=[m_face_map.value for m_face_map in current_obj.data.face_maps.active.data]

    #print(f"Portal objects: {', '.join([pair[0].name for pair in portal_objects])}")
    for v in me.vertices:
        flr.verts.append(support.convert_vector3([v.co[0], v.co[1], v.co[2]]))

    flr.tris = create_floor_triangles_from_mesh(current_obj, me, portal_objects)

    # Mark fallthrough tris now that they're created:
    for ft in flr.tris:
        if face_maps_by_index != None:
            ft.fallthrough = (face_maps_by_index[ft.index] == FALLTHROUGH_MAP_INDEX) 
        else:
            ft.fallthrough = False

    pathGraph = swg_types.PathGraph()
    flr.pathGraph = pathGraph
    if len(support.getChildren(current_obj)) > 0:
        # portals=[]
        print(f"Should build PathGraph from {support.getChildren(current_obj)} children")
        waypoints=[]
        index=0
        for child in support.getChildren(current_obj):
            if child.name.startswith("CellWaypoint"):
                node = swg_types.PathGraphNode()
                node.index = index   
                node.type = 1
                node.radius = child['radius']
                converted = Vector(support.convert_vector3(child.location))
                node.position = [converted.x, converted.y, converted.z]
                pathGraph.nodes.append(node)         
                index += 1
        
        
    flr.add_portal_nodes(globalPortalIndecies)
    flr.make_waypoint_connections()
    flr.prune_redundant_edges()
    flr.add_portal_edges()    

    flr.write()
    now = time.time()
    print(f"Successfully wrote: {fullpath} Duration: " + str(datetime.timedelta(seconds=(now-start))))

    return {'FINISHED'}, flr

def create_floor_triangles_from_mesh(obj, me, portal_objects):
    tris=[]
    edge_types={}
    for edge in me.edges:  
        reversed=list(edge.vertices)
        reversed.reverse()
        # Start it as crossable always..
        edge_types[tuple(edge.vertices)] = swg_types.FloorTri.Crossable
        edge_types[tuple(reversed)] = swg_types.FloorTri.Crossable
        if edge.use_seam == True:
            edge_types[tuple(edge.vertices)] = swg_types.FloorTri.Uncrossable
            edge_types[tuple(reversed)] = swg_types.FloorTri.Uncrossable
        elif edge.use_edge_sharp == True:
            edge_types[tuple(edge.vertices)] = swg_types.FloorTri.WallBase
            edge_types[tuple(reversed)] = swg_types.FloorTri.WallBase               
        elif edge.crease > 0.9:
            edge_types[tuple(edge.vertices)] = swg_types.FloorTri.WallTop
            edge_types[tuple(reversed)] = swg_types.FloorTri.WallTop

    usedPortals = []
    for t1 in me.polygons:
        if(len(t1.vertices) != 3):
            print(f"Error. Triangle {t1.index} has {len(t1.vertices)} vertices. Only triangles supported!")
            return {'CANCELLED'}

        ft = swg_types.FloorTri()
        ft.index = t1.index
        ft.corner1 = t1.vertices[0]
        ft.corner2 = t1.vertices[2]
        ft.corner3 = t1.vertices[1]

        t1e1 = set([t1.vertices[0],t1.vertices[2]])
        t1e2 = set([t1.vertices[2],t1.vertices[1]])
        t1e3 = set([t1.vertices[1],t1.vertices[0]])

        # find the edge types
        ft.edgeType1 = edge_types[tuple(t1e1)]
        ft.edgeType2 = edge_types[tuple(t1e2)]
        ft.edgeType3 = edge_types[tuple(t1e3)]

        for t2 in [x for x in me.polygons if x.index != t1.index]:
            t2e1 = set([t2.vertices[0],t2.vertices[2]])
            t2e2 = set([t2.vertices[2],t2.vertices[1]])
            t2e3 = set([t2.vertices[1],t2.vertices[0]])

            if t1e1 in [t2e1, t2e2, t2e3]:
                ft.nindex1 = t2.index
            if t1e2 in [t2e1, t2e2, t2e3]:
                ft.nindex2 = t2.index
            if t1e3 in [t2e1, t2e2, t2e3]:
                ft.nindex3 = t2.index

        ft.normal = support.convert_vector3([t1.normal.x, t1.normal.y, t1.normal.z])        

        for portalIndex, pair in enumerate(portal_objects):
            portalObj = pair[0]
            pid=pair[1]
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
                    p1InTri = mathutils.geometry.intersect_point_tri(floortVerts[0], portalVerts[0], portalVerts[1], portalVerts[2])
                    dist0 = (p1InTri - floortVerts[0]).length < 0.01 if p1InTri != None else False
                    p2InTri = mathutils.geometry.intersect_point_tri(floortVerts[1], portalVerts[0], portalVerts[1], portalVerts[2])
                    dist1 = (p2InTri - floortVerts[1]).length < 0.01 if p2InTri != None else False
                    p3InTri = mathutils.geometry.intersect_point_tri(floortVerts[2], portalVerts[0], portalVerts[1], portalVerts[2])
                    dist2 = (p3InTri - floortVerts[2]).length < 0.01 if p3InTri != None else False
                    #print(f"FloorTri {t1.index} p0 ({t1.vertices[0]} = {floortVerts[0]} is in portal: {portalObj.name} tri {portalTri.index} at {p1InTri} Dist: {dist0}")
                    #print(f"FloorTri {t1.index} p1 ({t1.vertices[1]} = {floortVerts[1]} is in portal: {portalObj.name} tri {portalTri.index} at {p2InTri} Dist: {dist1}")
                    #print(f"FloorTri {t1.index} p2 ({t1.vertices[2]} = {floortVerts[2]} is in portal: {portalObj.name} tri {portalTri.index} at {p3InTri} Dist: {dist2}")
                    if dist0 and dist1:
                        print(f"   Intersection found: floorTri {t1.index}, Edge: {ft.corner1} - {ft.corner2} portalMesh {portalObj.name}: tri {portalTri.index} portalId3 = {pid}")
                        ft.portalId3 = portalIndex
                        usedPortals.append(portalObj)
                    if dist1 and dist2:
                        print(f"   Intersection found: floorTri {t1.index}, Edge: {ft.corner2} - {ft.corner3} portalMesh {portalObj.name}: tri {portalTri.index} portalId2 = {pid}")
                        ft.portalId2 = portalIndex
                        usedPortals.append(portalObj)
                    if dist2 and dist0:
                        print(f"   Intersection found: floorTri {t1.index}, Edge: {ft.corner3} - {ft.corner1} portalMesh {portalObj.name}: tri {portalTri.index} portalId1 = {pid}")
                        ft.portalId1 = portalIndex
                        usedPortals.append(portalObj)

        tris.append(ft)    

    unusedCount = 0
    for portal in portal_objects:
        if portal[0] not in usedPortals:
            print(f"Warning: Didn't used portal: {portal[0].name}")
            unusedCount += 1
    
    if unusedCount == 0:
        print(f"{obj.name}: all passsable portals were used!")

    return tris