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

from . import vertex_buffer_format
from . import swg_types
from . import support

def images_in_tree(node_tree):
	for node in node_tree.nodes:
		if hasattr(node, "image"):
			yield node.image
		if hasattr(node, "node_tree"):
			yield from images_in_tree(node.node_tree)

def all_images():
	for mat in bpy.data.materials:
		if mat.use_nodes:
			return set(filter(None, images_in_tree(mat.node_tree)))

def rotate_object(obj, rot_mat):
	# decompose world_matrix's components, and from them assemble 4x4 matrices
	orig_loc, orig_rot, orig_scale = obj.matrix_world.decompose()
	#
	orig_loc_mat   = Matrix.Translation(orig_loc)
	orig_rot_mat   = orig_rot.to_matrix().to_4x4()
	orig_scale_mat = (Matrix.Scale(orig_scale[0],4,(1,0,0)) @ 
					  Matrix.Scale(orig_scale[1],4,(0,1,0)) @ 
					  Matrix.Scale(orig_scale[2],4,(0,0,1)))
	#
	# assemble the new matrix
	obj.matrix_world = orig_loc_mat @ rot_mat @ orig_rot_mat @ orig_scale_mat

def import_msh(context,
			   filepath,
			   parent=None,
			   flip_uv_vertical=False,
			   remove_duplicate_verts=True,
			   just_the_mesh = False,
	):  

	print(f'Importing msh: {filepath} Flip UV: {flip_uv_vertical}')

	swg_root = context.preferences.addons[__package__].preferences.swg_root
	msh = swg_types.SWGMesh(filepath, swg_root)
	if not msh.load():
		return {'CANCELLED'}
	
		
	name=os.path.basename(filepath).rsplit( ".", 1 )[ 0 ]
	mesh = bpy.data.meshes.new(name=f'{name}-mesh')
	obj = bpy.data.objects.new(name, mesh)

	if parent == None:
		parent = bpy.context.scene.collection
	
	parent.objects.link(obj)

	faces_by_material = {}
	materials_by_face_index = []
	normals=[]
	verts = []   
	color0 = []
	color1 = []
	uvs_by_depth = {}

	highest_vert_ind=0
	global_loop_index=0
	
	any_sps_has_color0 = False
	any_sps_has_color1 = False
	for index, sps in enumerate(msh.spss):
		
		num_uv_sets = sps.getNumUVSets()
		for i in range(0, num_uv_sets):
			if i not in uvs_by_depth.keys():
				uvs_by_depth[i] = {}

		faces_by_material[index] = []
		mat_name = sps.stripped_shader_name()
		material = None
		
		for mat in bpy.data.materials:
			if mat.name == mat_name:
				material = mat

		if material == None:
			material = bpy.data.materials.new(sps.stripped_shader_name()) 

		material["DOT3"] = sps.hasDOT3()
		material["UVSets"] = num_uv_sets
		material["Color0"] = sps.hasColor0()
		material["Color1"] = sps.hasColor1()

		if sps.real_shader:
			tex_to_png = context.preferences.addons[__package__].preferences.convert_tex_to_png
			support.configure_material_from_swg_shader(material, sps.real_shader, swg_root, tex_to_png) 

		mesh.materials.append(material)

		uvs = []
		for ind, vert in enumerate(sps.verts):
			verts.append(support.convert_vector3(vert.pos))

		for tri in sps.tris:
			p3 = tri.p3 + highest_vert_ind
			p2 = tri.p2 + highest_vert_ind
			p1 = tri.p1 + highest_vert_ind
			faces_by_material[index].append((p3, p2, p1))
			p3n = sps.verts[tri.p3].normal
			p2n = sps.verts[tri.p2].normal
			p1n = sps.verts[tri.p1].normal		   
			normals.append(support.convert_vector3([p3n.x, p3n.y, p3n.z]))
			normals.append(support.convert_vector3([p2n.x, p2n.y, p2n.z]))
			normals.append(support.convert_vector3([p1n.x, p1n.y, p1n.z]))

			for loop_index, vert_index in enumerate([tri.p3, tri.p2, tri.p1]):
				vert = sps.verts[vert_index]

				if sps.hasColor0():
					any_sps_has_color0 = True
					color0.append(vert.color0)
				else:
					color0.append([1,1,1,1])
					
				if sps.hasColor1():
					any_sps_has_color1 = True
					color1.append(vert.color1)
				else:
					color1.append([1,1,1,1])

				for uvi in range(0, num_uv_sets):
					uv = vert.texs[uvi] 
					uvs_by_depth[uvi][global_loop_index] = uv
					#print(f"SPS {index}, Vert {global_loop_index} UV: {uvi} = {Vector(uv)}")

				global_loop_index += 1

			materials_by_face_index.append(index)
		highest_vert_ind += len(sps.verts)
	mesh.from_pydata(verts, [], sum(faces_by_material.values(), []))

	for flist in mesh.polygons:
		flist.material_index = materials_by_face_index[flist.index]

	mesh.use_auto_smooth = True
	mesh.normals_split_custom_set(normals)
	
	for depth, uvs in uvs_by_depth.items():		
		uv_layer = mesh.uv_layers.new(name=f'uvmap-{depth}')
		for loop in mesh.loops:
			try:
				uv_layer.data[loop.index].uv = [0.0,0.0]
			except:
				print(f"*** UVMap: {uv_layer.name} Couldn't default loop: {loop.index}")

		for loop_index, uv in uvs.items():
			uv_layer.data[loop_index].uv = [uv[0], (uv[1] if not flip_uv_vertical else (1.0 - uv[1]))]

	if any_sps_has_color0:
		mesh.vertex_colors.new(name="color0")
		color_layer = mesh.vertex_colors["color0"]
		try:
			for idx in range(0, len(color0)):
				color_layer.data[idx].color = color0[idx]
				c=color_layer.data[idx].color
		except:
			print(f"Warning! Color0 only has {len(color0)} but need {len(color_layer.data)}")

	if any_sps_has_color1:
		mesh.vertex_colors.new(name="color1")
		color_layer = mesh.vertex_colors["color1"]
		try:
			for idx in range(0, len(color1)):
				color_layer.data[idx].color = color1[idx] 
		except:
			print(f"Warning! Color1 only has {len(color1)} but need {len(color_layer.data)}")

	if remove_duplicate_verts:
		#print(f"Removing duplicate verts ...")
		bm = bmesh.new()
		bm.from_mesh(mesh)
		before = len(mesh.vertices)
		removed = bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
		bm.to_mesh(mesh)		
		after = len(mesh.vertices)			
		print(f"Removed: {before - after} verts")
		bm.free()
		
	mesh.update() 
	mesh.validate()

	if not just_the_mesh:
		for data in msh.hardpoints:
			support.create_hardpoint_obj(data[12], data[0:12], parent = obj)

	return obj
	 
def load_new(context,
			 filepath,
			 *,	 
			 global_matrix=None,
			 flip_uv_vertical=False,
			 remove_duplicate_verts=True,
			 ):  

	obj = import_msh(context, filepath, None, flip_uv_vertical, remove_duplicate_verts)
	return {'FINISHED'}