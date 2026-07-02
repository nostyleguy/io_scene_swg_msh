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
import time
import math
import mathutils
from .swg_types import FloorEdgeType, FloorFile, FloorTri, PathGraph, PathGraphNode, PathNodeType
from .support import convert_vector3, getChildren
from mathutils import Vector

SNAP_MAX_DIST_BELOW = 3.0
SNAP_MAX_DIST_ABOVE = 1.0

def _snap_to_floor(pos, flr):
    """Snap a position's Y to the floor surface, preserving XZ.
    Matches Maya's vertical ray cast (FloorBuilder.cpp:597-623):
    prefer floor below within 3.0, fall back to above within 1.0."""
    best_below_y = None
    best_below_dist = float('inf')
    best_above_y = None
    best_above_dist = float('inf')
    ray_down = Vector((0.0, -1.0, 0.0))
    ray_up = Vector((0.0, 1.0, 0.0))
    for tri in flr.tris:
        corners = [Vector(flr.verts[i]) for i in [tri.corner1, tri.corner2, tri.corner3]]
        # Search below
        hit = mathutils.geometry.intersect_ray_tri(corners[0], corners[1], corners[2], ray_down, pos, True)
        if hit is not None:
            dist = pos.y - hit.y
            if dist <= SNAP_MAX_DIST_BELOW and dist < best_below_dist:
                best_below_dist = dist
                best_below_y = hit.y
        # Search above
        hit = mathutils.geometry.intersect_ray_tri(corners[0], corners[1], corners[2], ray_up, pos, True)
        if hit is not None:
            dist = hit.y - pos.y
            if dist <= SNAP_MAX_DIST_ABOVE and dist < best_above_dist:
                best_above_dist = dist
                best_above_y = hit.y
    if best_below_y is not None:
        return best_below_y
    return best_above_y

def export_flr(context, filepath):
    objects = context.selected_objects

    if not objects:
        return {'CANCELLED'}

    for ob in objects:
        if ob.type != 'MESH':
            continue
        dirname = os.path.dirname(filepath)
        fullpath = os.path.join(dirname, ob.name + ".flr")
        result, _ = export_one(fullpath, ob, [])
        if 'FINISHED' not in result:
            return {'CANCELLED'}
    return {'FINISHED'}

def build_floor(current_obj, portal_objects):
    """Build a FloorFile in memory from a Blender mesh object. Does not write to disk."""
    globalPortalIndices = [p[1] for p in portal_objects]

    flr = FloorFile(None)

    me = current_obj.to_mesh()

    # Find the tris in the "fallthrough" face map
    fallthrough_map_index = None
    if current_obj.face_maps:
        for face_map in current_obj.face_maps:
            if face_map.name.lower() == "fallthrough":
                fallthrough_map_index = face_map.index
    if fallthrough_map_index is None:
        print("Warning! No 'fallthrough' FaceMap found, no triangles can be marked as fallthrough!")
    else:
        print(f"{current_obj.name} has 'fallthrough' facemap. Good to go")

    face_maps_by_index = None
    if current_obj.data.face_maps.active:
        face_maps_by_index = [m_face_map.value for m_face_map in current_obj.data.face_maps.active.data]

    for v in me.vertices:
        flr.verts.append(convert_vector3([v.co[0], v.co[1], v.co[2]]))

    flr.tris = create_floor_triangles_from_mesh(current_obj, me, portal_objects)
    if flr.tris is None:
        return None

    # Mark fallthrough tris now that they're created
    for ft in flr.tris:
        if fallthrough_map_index is not None and face_maps_by_index is not None:
            ft.fallthrough = (face_maps_by_index[ft.index] == fallthrough_map_index)
        else:
            ft.fallthrough = False

    pathGraph = PathGraph()
    flr.pathGraph = pathGraph
    children = getChildren(current_obj)
    if children:
        print(f"Should build PathGraph from {children} children")
        index = 0
        for child in children:
            if child.name.startswith("CellWaypoint"):
                node = PathGraphNode()
                node.index = index
                node.type = PathNodeType.CellWaypoint
                node.debug_name = child.name
                node.radius = child['radius']
                converted = Vector(convert_vector3(child.location))
                # Small fixed jitter to avoid landing exactly on floor edges,
                # which causes ambiguous point-in-triangle tests. Matches
                # Maya exporter (FloorBuilder.cpp:593).
                converted += Vector((0.007, 0.0, 0.003))
                snapped_y = _snap_to_floor(converted, flr)
                if snapped_y is not None:
                    converted.y = snapped_y
                node.position = [converted.x, converted.y, converted.z]
                pathGraph.nodes.append(node)
                index += 1

    portalNames = [p[0].name for p in portal_objects]
    flr.add_portal_nodes(globalPortalIndices, portalNames)
    flr.prepare_connectivity()
    flr.make_waypoint_connections()
    flr.prune_redundant_edges()
    flr.add_portal_edges()

    return flr

def export_one(fullpath, current_obj, portal_objects, use_object_name=True):
    start = time.time()
    print(f'Exporting Flr: {fullpath}')

    if use_object_name:
        dirname = os.path.dirname(fullpath)
        fullpath = os.path.join(dirname, current_obj.name + ".flr")

    os.makedirs(os.path.dirname(fullpath) or '.', exist_ok=True)

    flr = build_floor(current_obj, portal_objects)
    if flr is None:
        return {'CANCELLED'}, None

    flr.path = fullpath
    flr.write()
    elapsed = time.time() - start
    print(f"Successfully wrote: {fullpath} Duration: {elapsed:.3f}s")

    return {'FINISHED'}, flr

def _closest_point_on_segment(point, seg_a, seg_b):
    """Return the closest point on line segment seg_a->seg_b to point."""
    ab = seg_b - seg_a
    len_sq = ab.dot(ab)
    if len_sq < 1e-12:
        return seg_a.copy()
    t = max(0.0, min(1.0, (point - seg_a).dot(ab) / len_sq))
    return seg_a + ab * t

def _closest_point_on_polygon(point, poly_verts):
    """Return the closest point on a polygon (edges + interior) to point."""
    # Check edges first
    best_dist_sq = float('inf')
    best_point = poly_verts[0].copy()
    n = len(poly_verts)
    for i in range(n):
        cp = _closest_point_on_segment(point, poly_verts[i], poly_verts[(i + 1) % n])
        d = (cp - point).length_squared
        if d < best_dist_sq:
            best_dist_sq = d
            best_point = cp

    # Check interior projection — project onto polygon plane and test containment
    normal = (poly_verts[1] - poly_verts[0]).cross(poly_verts[2] - poly_verts[0])
    len_sq = normal.dot(normal)
    if len_sq > 1e-12:
        normal_n = normal / math.sqrt(len_sq)
        dist = (point - poly_verts[0]).dot(normal_n)
        projected = point - normal_n * dist
        if _point_in_polygon(projected, poly_verts, normal_n):
            d = (projected - point).length_squared
            if d < best_dist_sq:
                best_point = projected
    return best_point

def _point_in_polygon(point, poly_verts, normal):
    """Test if a point (assumed coplanar) lies inside a convex polygon."""
    n = len(poly_verts)
    for i in range(n):
        edge = poly_verts[(i + 1) % n] - poly_verts[i]
        to_point = point - poly_verts[i]
        if edge.cross(to_point).dot(normal) < 0:
            return False
    return True

def _match_segment_to_poly(a, b, poly_verts):
    """
    Match a floor edge segment to a portal polygon using the same 3-test
    approach as the engine's FloorMesh::matchSegmentToPoly.
    """
    # Test 1 — Project both endpoints onto the portal plane. If both
    # projections land inside the polygon and are within 10cm of the
    # plane, it's a match.
    normal = (poly_verts[1] - poly_verts[0]).cross(poly_verts[2] - poly_verts[0])
    len_sq = normal.dot(normal)
    if len_sq > 1e-12:
        normal_n = normal / math.sqrt(len_sq)
        dist_a = (a - poly_verts[0]).dot(normal_n)
        dist_b = (b - poly_verts[0]).dot(normal_n)
        a2 = a - normal_n * dist_a
        b2 = b - normal_n * dist_b
        if _point_in_polygon(a2, poly_verts, normal_n) and _point_in_polygon(b2, poly_verts, normal_n):
            if abs(dist_a) < 0.1 and abs(dist_b) < 0.1:
                return True

    # Test 2 — Check if both endpoints are within 5cm of any single
    # portal edge segment.
    n = len(poly_verts)
    for i in range(n):
        pa = poly_verts[i]
        pb = poly_verts[(i + 1) % n]
        a2 = _closest_point_on_segment(a, pa, pb)
        b2 = _closest_point_on_segment(b, pa, pb)
        if (a2 - a).length < 0.05 and (b2 - b).length < 0.05:
            return True

    # Test 3 — Check if both endpoints are within 1cm of the polygon.
    a2 = _closest_point_on_polygon(a, poly_verts)
    b2 = _closest_point_on_polygon(b, poly_verts)
    if (a2 - a).length < 0.01 and (b2 - b).length < 0.01:
        return True

    return False

def create_floor_triangles_from_mesh(obj, me, portal_objects):
    tris = []
    edge_types = {}
    for edge in me.edges:
        key = frozenset(edge.vertices)
        edge_types[key] = FloorEdgeType.Crossable
        if edge.use_seam:
            edge_types[key] = FloorEdgeType.Uncrossable
        elif edge.use_edge_sharp:
            edge_types[key] = FloorEdgeType.WallBase
        elif edge.crease > 0.9:
            edge_types[key] = FloorEdgeType.WallTop

    # Build edge-to-triangle adjacency map for O(1) neighbor lookups
    edge_adj = {}
    for poly in me.polygons:
        verts = poly.vertices
        n = len(verts)
        for i in range(n):
            edge_key = frozenset((verts[i], verts[(i + 1) % n]))
            edge_adj.setdefault(edge_key, []).append(poly.index)

    # Cache portal meshes to avoid repeated to_mesh() calls
    portal_cache = []
    for portalIndex, (portalObj, pid) in enumerate(portal_objects):
        if portalObj.type != 'MESH':
            continue
        portal_cache.append((portalIndex, portalObj, pid, portalObj.to_mesh()))

    usedPortals = set()
    for t1 in me.polygons:
        if len(t1.vertices) != 3:
            print(f"Error. Triangle {t1.index} has {len(t1.vertices)} vertices. Only triangles supported!")
            return None

        ft = FloorTri()
        ft.index = t1.index
        ft.corner1 = t1.vertices[0]
        ft.corner2 = t1.vertices[2]
        ft.corner3 = t1.vertices[1]

        t1e1 = frozenset([t1.vertices[0],t1.vertices[2]])
        t1e2 = frozenset([t1.vertices[2],t1.vertices[1]])
        t1e3 = frozenset([t1.vertices[1],t1.vertices[0]])

        # find the edge types
        ft.edgeType1 = edge_types[t1e1]
        ft.edgeType2 = edge_types[t1e2]
        ft.edgeType3 = edge_types[t1e3]

        for edge_key, attr in [(t1e1, 'nindex1'), (t1e2, 'nindex2'), (t1e3, 'nindex3')]:
            for tri_idx in edge_adj.get(edge_key, []):
                if tri_idx != t1.index:
                    setattr(ft, attr, tri_idx)
                    break

        ft.normal = convert_vector3([-t1.normal.x, -t1.normal.y, -t1.normal.z])        

        # For each boundary edge, test against all portal polygons using
        # the same 3-test approach as the engine's matchSegmentToPoly:
        #   Test 1: Project onto portal plane, check inside polygon & within 10cm
        #   Test 2: Close to a portal edge segment within 5cm
        #   Test 3: Close to nearest point on portal polygon within 1cm
        edges_and_neighbors = [
            (Vector(me.vertices[ft.corner1].co), Vector(me.vertices[ft.corner2].co), ft.nindex1, 'portalId1'),
            (Vector(me.vertices[ft.corner2].co), Vector(me.vertices[ft.corner3].co), ft.nindex2, 'portalId2'),
            (Vector(me.vertices[ft.corner3].co), Vector(me.vertices[ft.corner1].co), ft.nindex3, 'portalId3'),
        ]

        for edgeA, edgeB, neighborIdx, portalIdAttr in edges_and_neighbors:
            if neighborIdx != -1:
                continue

            matched = False
            for portalIndex, portalObj, pid, portalMesh in portal_cache:
                for portalTri in portalMesh.polygons:
                    portalVerts = [Vector(portalMesh.vertices[p].co) for p in portalTri.vertices]

                    if _match_segment_to_poly(edgeA, edgeB, portalVerts):
                        print(f"   Intersection found: floorTri {t1.index}, Edge: {edgeA} - {edgeB} portalMesh {portalObj.name}: tri {portalTri.index} {portalIdAttr} = {pid}")
                        setattr(ft, portalIdAttr, portalIndex)
                        usedPortals.add(portalObj)
                        matched = True
                        break
                if matched:
                    break

        tris.append(ft)    

    unusedCount = 0
    for portalObj, pid in portal_objects:
        if portalObj not in usedPortals:
            print(f"Warning: Didn't use portal: {portalObj.name}")
            unusedCount += 1

    if unusedCount == 0 and portal_objects:
        print(f"{obj.name}: all passable portals were used!")

    return tris