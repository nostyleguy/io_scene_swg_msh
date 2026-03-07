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
from bpy_extras.wm_utils.progress_report import ProgressReport
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from bpy_extras import node_shader_utils
from bpy import utils

from . import import_lod
from . import import_msh
from . import import_flr
from . import swg_types
from . import support

def load_new(context,
			 filepath,
			 *,
			 flip_uv_vertical=False,
			 remove_duplicate_verts=True
			 ):  

	SWG_ROOT=context.preferences.addons[__package__].preferences.swg_root
	print(f"Loading pob {filepath}")
	pob = swg_types.PobFile(filepath)
	pob.load()		
		
	name=os.path.basename(filepath).rsplit( ".", 1 )[ 0 ]
	collection = bpy.data.collections.new(name)
	bpy.context.scene.collection.children.link(collection)

	if pob.crc != None:
		collection['ship'] = pob.ship
		collection['crc'] = pob.crc

	portal_objs={}
	for cell in pob.cells:			
		cell_collection = bpy.data.collections.new(cell.name)

		cell_collection['can_see_parent'] = cell.can_see_parent
		collection.children.link(cell_collection)

		appearance_path = support.find_file(cell.appearance_file, SWG_ROOT)
		if appearance_path and appearance_path.endswith(".msh"):
			mesh = import_msh.import_msh(context,
			appearance_path,
			parent=cell_collection,
			flip_uv_vertical=flip_uv_vertical,
			remove_duplicate_verts=remove_duplicate_verts,
			)
			mesh.name = f'Appearance_{cell.name}'
		elif appearance_path and appearance_path.endswith(".lod"):
			result = import_lod.load_new(context,
				appearance_path,
				parent=cell_collection,
				flip_uv_vertical=flip_uv_vertical,
				remove_duplicate_verts=remove_duplicate_verts,
				do_collision=False,
				do_floor=False
				)
			if result[0] == 'SUCCESS':
				result[1].name = f'Appearance_{cell.name}'
			else:
				print(f"Error. Erro while importing LOD: {appearance_path}")
				return ('CANCELLED')

		elif appearance_path and appearance_path.endswith(".apt"):
			apt = swg_types.AptFile(appearance_path)
			apt.load()
			referenceFilePath = apt.get_reference_fullpath(SWG_ROOT)

			if referenceFilePath and referenceFilePath.endswith(".msh"):
				mesh = import_msh.import_msh(context,
				referenceFilePath,
				parent=cell_collection,
				flip_uv_vertical=flip_uv_vertical,
				remove_duplicate_verts=False,
				)
				mesh.name = f'Appearance_{cell.name}'
			elif referenceFilePath and referenceFilePath.endswith(".lod"):
				result = import_lod.load_new(context,
					referenceFilePath,
					parent=cell_collection,
					flip_uv_vertical=flip_uv_vertical,
					remove_duplicate_verts=remove_duplicate_verts,
					do_collision=False,
					do_floor=False
					)
				if result[0] == 'SUCCESS':
					result[1].name = f'Appearance_{cell.name}'
				else:
					print(f"Error. Error while importing LOD: {appearance_path}")
					return ('CANCELLED')
			else:
				print(f"Couldn't find referenced file: {apt.reference}")

		# Floor
		#floor_collection = bpy.data.collections.new(f"Floor_{cell.name}")
		#cell_collection.children.link(floor_collection)
		if cell.floor_file:
			floor_path = support.find_file(cell.floor_file, SWG_ROOT)
			if floor_path:
				print(f"Found floor_file: {cell.floor_file} at {floor_path}")
				flr = import_flr.import_flr(context, floor_path, collection=cell_collection) 
				flr.name = f'Floor_{cell.name}'
			else:
				print(f"Didn't find floor_file: {cell.floor_file}")
			
		# Collision:
		collision = bpy.data.collections.new(f"Collision_{cell.name}")
		cell_collection.children.link(collision)   
		if cell.collision:
			support.add_collision_to_collection(collision, cell.collision, False)

		# Create pert-room portal collection and associate portal objects with it
		roomPortals = bpy.data.collections.new(f"Portals_{cell.name}")
		cell_collection.children.link(roomPortals)
		for portalData in cell.portals:
			if not portalData.id in portal_objs:
				# We haven't created this portal object yet, create it 
				portal_objs[portalData.id] = create_portal_number(pob, portalData.id, roomPortals)
			else:
				# We already have created it, just link
				roomPortals.objects.link(portal_objs[portalData.id])
			
			portal_objs[portalData.id]['passable'] = portalData.passable
			if portalData.doorstyle != None:
				if len(support.getChildren(portal_objs[portalData.id])) == 0:
					if portalData.doorhardpoint != None:
						hpntadded = support.create_hardpoint_obj(f"{portal_objs[portalData.id].name}-door", portalData.doorhardpoint, collection = roomPortals, parent = portal_objs[portalData.id])
						hpntadded['doorstyle'] = portalData.doorstyle

		# Lights:
		lightCol = bpy.data.collections.new(f"Lights_{cell.name}")
		cell_collection.children.link(lightCol)
		for lightData in cell.lights:
			light = support.create_light(lightCol, lightData)
				
	# pgrf_collection = bpy.data.collections.new("PathGraph")
	# collection.children.link(pgrf_collection)
	# if pob.pathGraph != None:
	#	 support.create_pathgraph(pgrf_collection, pob.pathGraph, None, True)

	return ('SUCCESS', collection)

def create_portal_number(pob, p_ind, collection):
	portal = pob.portals[p_ind]
	mesh = bpy.data.meshes.new(name=f'p{p_ind}-mesh')
	obj = bpy.data.objects.new(f'p{p_ind}', mesh)
	verts = []
	edges = []
	tris = []

	for ind, vert in enumerate(portal.verts):
		verts.append(Vector(support.convert_vector3([vert.x, vert.y, vert.z])))

	for tri in portal.tris:
		tris.append([tri.p3, tri.p2, tri.p1])

	mesh.from_pydata(verts, edges, tris)		
	mesh.update() 
	mesh.validate()
	collection.objects.link(obj)
	return obj