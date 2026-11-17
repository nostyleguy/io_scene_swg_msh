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
from . import extents
from . import support

from mathutils import Matrix, Vector, Color
from bpy_extras import io_utils, node_shader_utils

from bpy_extras.wm_utils.progress_report import (
	ProgressReport,
	ProgressReportSubstep,
)

def mesh_triangulate(me):
	bm = bmesh.new()
	bm.from_mesh(me)
	ngons = [f for f in bm.faces if len(f.verts) > 4]
	bmesh.ops.triangulate(bm, faces=ngons if ngons else bm.faces)
	bm.to_mesh(me)
	bm.free()

def save(context, filepath, *, flip_uv_vertical=False):
	objects = context.selected_objects

	if len(objects) == 0:
		print(f"Nothing selected. Aborting!")
		return {'CANCELLED'}
	else:
		print(f"Objects to export: {len(objects)}")

	for ob in objects:
		print(f"Exporting: {ob.name}")
		if ob.type != 'MESH':
			print(f"Skipping {ob.name} with type: {ob.type}")
			continue
		else:
			dirname = os.path.dirname(filepath)
			fullpath = os.path.join(dirname, ob.name+".msh")
			extract_dir=context.preferences.addons[__package__].preferences.swg_root
			result = export_one(fullpath, extract_dir, ob, flip_uv_vertical)
			if not 'FINISHED' in result:
				return {'CANCELLED'}
	return {'FINISHED'}

def export_one(fullpath, extract_dir, obj, flip_uv_vertical):
	newMsh = swg_types.SWGMesh(fullpath, extract_dir)
	start = time.time()
	print(f'Exporting msh: {fullpath} Flip UV: {flip_uv_vertical}')

	me = obj.to_mesh()

	# Only invoke BMesh triangulation if the mesh contains 5+ sided ngons
	# (which calc_tangents does not support). Otherwise calc_loop_triangles()
	# handles tris and quads non-destructively without altering custom normals
	# or deleting opposite-winding faces that share vertices.
	if any(len(p.vertices) > 4 for p in me.polygons):
		mesh_triangulate(me)

	# If negative scaling, invert the normals before extracting loop normals, tangents, and loop triangles
	if obj.matrix_world.determinant() < 0.0:
		me.flip_normals()

	me.calc_loop_triangles()
	me.calc_normals_split()

	for layer in me.vertex_colors:
		print(f"Color layer: {layer.name}")

	t_ln = array.array(data_types.ARRAY_FLOAT64, (0.0,)) * len(me.loops) * 3
	me.loops.foreach_get("normal", t_ln)
	normals = list(map(list, zip(*[iter(t_ln)]*3)))

	uv_names = [uvlayer.name for uvlayer in me.uv_layers]
	if uv_names:
		me.calc_tangents(uvmap=uv_names[0])

	faces_by_material = {}
	for tri in me.loop_triangles:
		if tri.material_index not in faces_by_material:
			faces_by_material[tri.material_index] = []
		faces_by_material[tri.material_index].append(tri)

	for index in faces_by_material:
		print(f"Faces_by_material[{index}]: {len(faces_by_material[index])}")
	
	this_mat_index=0
	total_tris=0
	total_verts=0
	for mat_index, face_list in faces_by_material.items():
		try:
			material = obj.material_slots[mat_index].material
		except :
			print(f"Asked for material index: {mat_index} but we only have {len(obj.material_slots)}. Won't do anything with {len(faces_by_material[mat_index])} triangles I guess")
			continue

		thisSPS = swg_types.SPS(this_mat_index, f'shader/{material.name}.sht', 0, [], [])

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

		color0_layer = None
		if doColor0:
			if "color0" in me.vertex_colors:
				color0_layer = me.vertex_colors["color0"].data
			elif len(me.vertex_colors) > 0:
				color0_layer = me.vertex_colors[0].data

		color1_layer = None
		if doColor1:
			if "color1" in me.vertex_colors:
				color1_layer = me.vertex_colors["color1"].data
			elif len(me.vertex_colors) > 1:
				color1_layer = me.vertex_colors[1].data

		num_uv_layers = min(uvSets, len(me.uv_layers))

		unique_verts = {}
		last_unique_vert_index = 0
		for face_index, face in enumerate(face_list):
			p1 = p2 = p3 = None
			for uv_index, l_index in enumerate(face.loops):
				vert_idx = face.vertices[uv_index]
				v = me.vertices[vert_idx]
				normal = normals[l_index]

				uvs = []
				for i in range(0, num_uv_layers):
					uv = me.uv_layers[i].data[l_index].uv.copy()
					if flip_uv_vertical:
						uv[1] = (1.0 - uv[1])
					uvs.append(uv)
				while len(uvs) < uvSets:
					uvs.append(Vector((0.0, 0.0)))

				color0_val = tuple(color0_layer[l_index].color) if color0_layer is not None else ((1.0, 1.0, 1.0, 1.0) if doColor0 else None)
				color1_val = tuple(color1_layer[l_index].color) if color1_layer is not None else ((1.0, 1.0, 1.0, 1.0) if doColor1 else None)

				if doDOT3 and uv_names:
					loop = me.loops[l_index]
					tang = support.convert_vector3(loop.tangent)
					dot3_val = [*tang, loop.bitangent_sign]
					dot3_key = (round(tang[0], 4), round(tang[1], 4), round(tang[2], 4), round(loop.bitangent_sign, 4))
				elif doDOT3:
					dot3_val = [1.0, 0.0, 0.0, 1.0]
					dot3_key = (1.0, 0.0, 0.0, 1.0)
				else:
					dot3_val = None
					dot3_key = None

				norm_key = (round(normal[0], 4), round(normal[1], 4), round(normal[2], 4))
				uv_key = tuple((round(uv[0], 4), round(uv[1], 4)) for uv in uvs)
				c0_key = tuple(round(c, 4) for c in color0_val) if color0_val is not None else None
				c1_key = tuple(round(c, 4) for c in color1_val) if color1_val is not None else None

				rounded = (vert_idx, norm_key, uv_key, c0_key, c1_key, dot3_key)
				if rounded not in unique_verts:
					unique_verts[rounded] = last_unique_vert_index
					last_unique_vert_index += 1

					swg_v = swg_types.SWGVertex()
					swg_v.pos = Vector(support.convert_vector3(v.co))
					swg_v.normal = Vector(support.convert_vector3(normal))
					
					if doColor0:
						swg_v.color0 = color0_val

					if doColor1:
						swg_v.color1 = color1_val

					for uv in uvs:
						swg_v.texs.append(uv)

					if doDOT3:
						swg_v.texs.append(dot3_val)

					thisSPS.verts.append(swg_v)
					total_verts += 1

				if p1 == None:
					p1 = unique_verts[rounded]
				elif p2 == None:
					p2 = unique_verts[rounded]
				elif p3 == None:
					p3 = unique_verts[rounded]
					thisSPS.tris.append(swg_types.Triangle(p3, p2, p1))
					total_tris += 1
					p1 = p2 = p3 = None	
			
		print(f"SPS {str(thisSPS.no)}: Unique Verts: {str(len(unique_verts))} UV Channels: {str(vertex_buffer_format.getNumberOfTextureCoordinateSets(thisSPS.flags))} Has flags {str(thisSPS.flags)}") 
		newMsh.spss.append(thisSPS)	 
		this_mat_index += 1

	newMsh.extents = get_extents(obj, me)
	obj.to_mesh_clear()

	for ob in bpy.data.objects: 
		if ob.parent == obj: 
			if ob.type != 'MESH' and ob.type == 'EMPTY' and ob.empty_display_type == "ARROWS":
				newMsh.hardpoints.append(support.hardpoint_from_obj(ob))

	newMsh.write(fullpath)
	now = time.time()
	print(f"total_tris: {total_tris} total_verts: {total_verts} Successfully wrote: {fullpath} Duration: " + str(datetime.timedelta(seconds=(now-start))))

	return {'FINISHED'}

def get_extents(obj, me=None):
	clear_mesh = False
	if me is None:
		me = obj.to_mesh()
		clear_mesh = True
	extreme_g_x = None
	extreme_g_y = None
	extreme_g_z = None
			
	extreme_l_x = None
	extreme_l_y = None
	extreme_l_z = None

	for v in me.vertices:
		c = Vector(support.convert_vector3(v.co))
		if extreme_g_x == None or c[0] > extreme_g_x:
			extreme_g_x = c[0]
		if extreme_l_x == None or c[0] < extreme_l_x:
			extreme_l_x = c[0]
		if extreme_g_y == None or c[1] > extreme_g_y:
			extreme_g_y = c[1]
		if extreme_l_y == None or c[1] < extreme_l_y:
			extreme_l_y = c[1]
		if extreme_g_z == None or c[2] > extreme_g_z:
			extreme_g_z = c[2]
		if extreme_l_z == None or c[2] < extreme_l_z:
			extreme_l_z = c[2]

	if clear_mesh:
		obj.to_mesh_clear()

	return extents.BoxExtents([extreme_l_x, extreme_l_y, extreme_l_z],[extreme_g_x, extreme_g_y, extreme_g_z])

def avg_vert_position_in_blender(obj):
	me = obj.to_mesh() 
	if len(me.vertices) > 0:
		sum = me.vertices[0].co.copy()
		for v in me.vertices[1:]:
			sum += v.co

		result = sum / len(me.vertices)
		obj.to_mesh_clear()
		return result
	else:
		obj.to_mesh_clear()
		return None