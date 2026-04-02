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
import bmesh
from mathutils import Vector

from .swg_types import FloorEdgeType, FloorFile
from . import support

def import_flr(context, filepath, collection=None):
    flr = FloorFile(filepath)
    flr.load()

    name = os.path.basename(filepath).rsplit(".", 1)[0]
    mesh = bpy.data.meshes.new(name=f'{name}-mesh')
    obj = bpy.data.objects.new(name, mesh)

    if collection is None:
        collection = context.collection
    collection.objects.link(obj)

    verts = []
    edges = []
    tris = []
    edge_types = {}

    for vert in flr.verts:
        verts.append(Vector(support.convert_vector3([vert[0], vert[1], vert[2]])))

    for tri in flr.tris:
        tris.append([tri.corner1, tri.corner3, tri.corner2])

        edges.append([tri.corner1, tri.corner2])
        edge_types[frozenset((tri.corner1, tri.corner2))] = tri.edgeType1

        edges.append([tri.corner2, tri.corner3])
        edge_types[frozenset((tri.corner2, tri.corner3))] = tri.edgeType2

        edges.append([tri.corner3, tri.corner1])
        edge_types[frozenset((tri.corner3, tri.corner1))] = tri.edgeType3

    mesh.from_pydata(verts, edges, tris)
    mesh.update()
    mesh.validate()

    face_map = obj.face_maps.new(name="fallthrough")
    face_map.add([x.index for x in flr.tris if x.fallthrough])

    for edge in mesh.edges:
        edge_type = edge_types[frozenset(edge.vertices)]
        if edge_type == FloorEdgeType.Uncrossable:
            edge.use_seam = True
        elif edge_type == FloorEdgeType.WallBase:
            edge.use_edge_sharp = True

    bm = bmesh.new()
    bm.from_mesh(mesh)
    crease_layer = bm.edges.layers.crease.verify()
    for edge in bm.edges:
        key = frozenset(v.index for v in edge.verts)
        edge_type = edge_types[key]
        if edge_type == FloorEdgeType.WallTop:
            edge[crease_layer] = 1.0
    bm.to_mesh(mesh)
    bm.free()

    if flr.pathGraph is not None:
        support.create_pathgraph(collection, flr.pathGraph, obj, True)

    return obj