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
from .support import convert_vector3
from .swg_types import FloorEdgeType, PathNodeType
from .export_flr import export_one, create_floor_triangles_from_mesh
from .export_pob import is_portal_passable


def _get_builtin_shader(name, fallback):
	"""Get a GPU builtin shader, falling back for older Blender versions."""
	import gpu
	try:
		return gpu.shader.from_builtin(name)
	except ValueError:
		return gpu.shader.from_builtin(fallback)


def _setup_gpu_state():
	import gpu
	gpu.state.blend_set('ALPHA')
	gpu.state.depth_test_set('ALWAYS')
	gpu.state.depth_mask_set(False)


def _restore_gpu_state():
	import gpu
	gpu.state.line_width_set(1.0)
	gpu.state.depth_mask_set(True)
	gpu.state.depth_test_set('NONE')
	gpu.state.blend_set('NONE')


def _draw_legend(entries, title=None):
	"""Draw a 2D color legend overlay in the bottom-left of the viewport.

	entries: list of (color_tuple, label_string)
	title: optional title string shown above entries
	"""
	import gpu
	import blf
	from gpu_extras.batch import batch_for_shader

	font_id = 0
	font_size = 14
	swatch_size = 12
	padding = 10
	line_height = 20
	margin = 20

	try:
		blf.size(font_id, font_size)
	except TypeError:
		blf.size(font_id, font_size, 72)

	max_label_width = 0
	for _color, label in entries:
		w, _h = blf.dimensions(font_id, label)
		max_label_width = max(max_label_width, w)
	if title:
		tw, _th = blf.dimensions(font_id, title)
		max_label_width = max(max_label_width, tw)

	box_width = padding + swatch_size + padding + max_label_width + padding
	num_lines = len(entries) + (1 if title else 0)
	box_height = padding + num_lines * line_height + padding

	x0 = margin
	y0 = margin

	shader = _get_builtin_shader('UNIFORM_COLOR', '2D_UNIFORM_COLOR')
	gpu.state.blend_set('ALPHA')

	bg_verts = [(x0, y0), (x0 + box_width, y0),
				(x0 + box_width, y0 + box_height), (x0, y0 + box_height)]
	batch = batch_for_shader(shader, 'TRIS', {"pos": bg_verts},
							indices=[(0, 1, 2), (0, 2, 3)])
	shader.uniform_float("color", (0.0, 0.0, 0.0, 0.7))
	batch.draw(shader)

	y = y0 + box_height - padding
	if title:
		y -= line_height
		blf.position(font_id, x0 + padding, y + 2, 0)
		blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
		blf.draw(font_id, title)

	for color, label in entries:
		y -= line_height
		sx = x0 + padding
		sy = y + 2
		swatch_verts = [(sx, sy), (sx + swatch_size, sy),
						(sx + swatch_size, sy + swatch_size), (sx, sy + swatch_size)]
		batch = batch_for_shader(shader, 'TRIS', {"pos": swatch_verts},
								indices=[(0, 1, 2), (0, 2, 3)])
		shader.uniform_float("color", color)
		batch.draw(shader)

		blf.position(font_id, sx + swatch_size + padding, y + 2, 0)
		blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
		blf.draw(font_id, label)

	gpu.state.blend_set('NONE')


def _tag_redraw_3d(context):
	for area in context.screen.areas:
		if area.type == 'VIEW_3D':
			area.tag_redraw()


def _gather_portal_objects(obj):
	"""Gather passable portal objects from sibling Portals collections."""
	portal_objects = []
	for col in obj.users_collection:
		for child in col.children:
			if not child.name.startswith("Portals"):
				continue
			for pid, candidate in enumerate(child.objects):
				if candidate.type != 'MESH' or not is_portal_passable(candidate):
					continue
				portal_objects.append([candidate, pid])
	return portal_objects


def _get_fallthrough_tris(obj, tris):
	"""Return set of triangle indices that are in the fallthrough face map."""
	fallthrough_map_idx = None
	if obj.face_maps:
		for face_map in obj.face_maps:
			if face_map.name.lower() == "fallthrough":
				fallthrough_map_idx = face_map.index

	face_maps_by_index = None
	if obj.data.face_maps.active:
		face_maps_by_index = [fm.value for fm in obj.data.face_maps.active.data]

	fallthrough_tris = set()
	if fallthrough_map_idx is not None and face_maps_by_index is not None:
		for ft in tris:
			if face_maps_by_index[ft.index] == fallthrough_map_idx:
				fallthrough_tris.add(ft.index)
	return fallthrough_tris


class SWG_Visualize_Floor_Pathgraph(bpy.types.Operator):
	bl_idname = "object.swg_visualize_flr_pathgraph"
	bl_label = "Visualize Floor Pathgraph"
	bl_description = '''Visualize how SWG will (probably) connect your CellWaypoints (ESC to dismiss)'''

	# Singleton overlay state — shared across instances so only one overlay
	# is active at a time and the draw callback can access the data.
	_handle = None
	_legend_handle = None
	_edge_verts = []
	_node_points = []
	_node_colors = []

	_type_colors = {
		PathNodeType.CellPortal:       (1.0, 0.5, 0.0, 1.0),
		PathNodeType.CellWaypoint:     (0.0, 1.0, 1.0, 1.0),
		PathNodeType.CellPOI:          (1.0, 0.0, 1.0, 1.0),
		PathNodeType.BuildingEntrance: (1.0, 1.0, 0.0, 1.0),
	}
	_default_color = (0.8, 0.8, 0.8, 1.0)
	_legend_entries = [
		((1.0, 0.5, 0.0, 1.0), "Cell Portal"),
		((0.0, 1.0, 1.0, 1.0), "Cell Waypoint"),
		((1.0, 0.0, 1.0, 1.0), "Cell POI"),
		((1.0, 1.0, 0.0, 1.0), "Building Entrance"),
		((0.8, 0.8, 0.8, 1.0), "Other"),
		((1.0, 1.0, 1.0, 0.6), "Edge"),
	]

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def modal(self, context, event):
		if event.type in {'ESC', 'RIGHTMOUSE'}:
			self._remove_overlay(context)
			return {'CANCELLED'}
		return {'PASS_THROUGH'}

	def _remove_overlay(self, context):
		cls = SWG_Visualize_Floor_Pathgraph
		if cls._handle is not None:
			bpy.types.SpaceView3D.draw_handler_remove(cls._handle, 'WINDOW')
			cls._handle = None
			cls._edge_verts = []
			cls._node_points = []
			cls._node_colors = []
		if cls._legend_handle is not None:
			bpy.types.SpaceView3D.draw_handler_remove(cls._legend_handle, 'WINDOW')
			cls._legend_handle = None
		_tag_redraw_3d(context)

	def execute(self, context):
		cls = SWG_Visualize_Floor_Pathgraph
		if cls._handle is not None:
			self._remove_overlay(context)
			self.report({'INFO'}, "Pathgraph overlay removed")
			return {'FINISHED'}

		tmpFile = os.path.join(os.path.dirname(context.blend_data.filepath), "debugPathgraph.flr")
		objects = context.selected_objects
		all_node_points = []
		all_node_colors = []
		all_edge_verts = []

		for ob in objects:
			if ob.type != 'MESH':
				continue

			portal_objects = _gather_portal_objects(ob)
			result, floor = export_one(tmpFile, ob, portal_objects)
			if 'FINISHED' not in result:
				self.report({'ERROR'}, f"Failed to export .flr from {ob.name}")
				continue

			pgrf = floor.pathGraph

			# Convert node positions (SWG coords -> Blender coords)
			# Track offset so edge indices are correct per-floor
			node_offset = len(all_node_points)
			for node in pgrf.nodes:
				pos = tuple(convert_vector3(node.position))
				all_node_points.append(pos)
				all_node_colors.append(self._type_colors.get(node.type, self._default_color))

			# Build edge line segments
			for edge in pgrf.edges:
				all_edge_verts.append(all_node_points[node_offset + edge.indexA])
				all_edge_verts.append(all_node_points[node_offset + edge.indexB])

		if not all_node_points:
			self.report({'WARNING'}, "No floor meshes found to visualize")
			return {'CANCELLED'}

		cls._edge_verts = all_edge_verts
		cls._node_points = all_node_points
		cls._node_colors = all_node_colors
		cls._handle = bpy.types.SpaceView3D.draw_handler_add(
			cls._draw_callback, (), 'WINDOW', 'POST_VIEW'
		)
		cls._legend_handle = bpy.types.SpaceView3D.draw_handler_add(
			cls._draw_legend_callback, (), 'WINDOW', 'POST_PIXEL'
		)

		context.window_manager.modal_handler_add(self)
		_tag_redraw_3d(context)
		self.report({'INFO'}, "Pathgraph overlay active — press ESC to dismiss")
		return {'RUNNING_MODAL'}

	@staticmethod
	def _draw_callback():
		import gpu
		from gpu_extras.batch import batch_for_shader
		cls = SWG_Visualize_Floor_Pathgraph

		shader = _get_builtin_shader('UNIFORM_COLOR', '3D_UNIFORM_COLOR')
		_setup_gpu_state()

		# Draw edges as white lines
		if cls._edge_verts:
			gpu.state.line_width_set(2.0)
			batch = batch_for_shader(shader, 'LINES', {"pos": cls._edge_verts})
			shader.uniform_float("color", (1.0, 1.0, 1.0, 0.6))
			batch.draw(shader)

		# Draw nodes as colored points
		if cls._node_points:
			gpu.state.point_size_set(12.0)
			shader_flat = _get_builtin_shader('FLAT_COLOR', '3D_FLAT_COLOR')
			batch = batch_for_shader(shader_flat, 'POINTS', {
				"pos": cls._node_points,
				"color": cls._node_colors,
			})
			batch.draw(shader_flat)
			gpu.state.point_size_set(1.0)

		_restore_gpu_state()

	@staticmethod
	def _draw_legend_callback():
		_draw_legend(SWG_Visualize_Floor_Pathgraph._legend_entries, title="Pathgraph")


class SWG_Debug_Portal_Edges(bpy.types.Operator):
	bl_idname = "object.swg_debug_portal_edges"
	bl_label = "Debug Portal Edges"
	bl_description = '''Visualize which floor triangle edges would get marked as portals (ESC to dismiss)'''

	# Singleton overlay state — shared across instances so only one overlay
	# is active at a time and the draw callback can access the data.
	_handle = None
	_legend_handle = None
	_draw_groups = []
	_legend_entries = [
		((1.0, 1.0, 0.0, 1.0), "Portal"),
		((1.0, 0.0, 0.0, 1.0), "Uncrossable"),
		((1.0, 0.5, 0.0, 1.0), "Wall Base"),
		((1.0, 0.3, 0.0, 1.0), "Wall Top"),
		((0.0, 1.0, 0.0, 1.0), "Fallthrough"),
		((0.4, 0.4, 0.4, 0.8), "Crossable"),
	]

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def modal(self, context, event):
		if event.type in {'ESC', 'RIGHTMOUSE'}:
			self._remove_overlay(context)
			return {'CANCELLED'}
		return {'PASS_THROUGH'}

	def _remove_overlay(self, context):
		cls = SWG_Debug_Portal_Edges
		if cls._handle is not None:
			bpy.types.SpaceView3D.draw_handler_remove(cls._handle, 'WINDOW')
			cls._handle = None
			cls._draw_groups = []
		if cls._legend_handle is not None:
			bpy.types.SpaceView3D.draw_handler_remove(cls._legend_handle, 'WINDOW')
			cls._legend_handle = None
		_tag_redraw_3d(context)

	def execute(self, context):
		cls = SWG_Debug_Portal_Edges
		if cls._handle is not None:
			self._remove_overlay(context)
			self.report({'INFO'}, "Portal edge overlay removed")
			return {'FINISHED'}

		color_buckets = {}
		objects = context.selected_objects
		for obj in objects:
			if obj.type != 'MESH' or not obj.name.startswith("Floor"):
				self.report({'WARNING'}, f"Skipping non 'Floor_' selected object: {obj.name}")
				continue

			portal_objects = _gather_portal_objects(obj)
			me = obj.to_mesh()
			result = create_floor_triangles_from_mesh(obj, me, portal_objects)
			if result is None:
				self.report({'ERROR'}, f"{obj.name} has non-triangle polygons, cannot debug portal edges")
				continue

			fallthrough_tris = _get_fallthrough_tris(obj, result)

			world = obj.matrix_world
			for ft in result:
				is_fallthrough = ft.index in fallthrough_tris
				edges = [
					(ft.corner1, ft.corner2, ft.edgeType1, ft.portalId1),
					(ft.corner2, ft.corner3, ft.edgeType2, ft.portalId2),
					(ft.corner3, ft.corner1, ft.edgeType3, ft.portalId3),
				]
				for vi_a, vi_b, edge_type, portal_id in edges:
					a = tuple(world @ me.vertices[vi_a].co)
					b = tuple(world @ me.vertices[vi_b].co)
					if portal_id != -1:
						color = (1.0, 1.0, 0.0, 1.0)      # Yellow: portal
					elif edge_type == FloorEdgeType.Uncrossable:
						color = (1.0, 0.0, 0.0, 1.0)      # Red: uncrossable
					elif edge_type == FloorEdgeType.WallBase:
						color = (1.0, 0.5, 0.0, 1.0)      # Orange: wall base
					elif edge_type == FloorEdgeType.WallTop:
						color = (1.0, 0.3, 0.0, 1.0)      # Dark orange: wall top
					elif is_fallthrough:
						color = (0.0, 1.0, 0.0, 1.0)      # Green: crossable fallthrough
					else:
						color = (0.2, 0.2, 0.2, 0.15)     # Dim grey: crossable
					color_buckets.setdefault(color, []).extend([a, b])

		if not color_buckets:
			self.report({'WARNING'}, "No floor edges found to visualize")
			return {'CANCELLED'}

		cls._draw_groups = list(color_buckets.items())
		cls._handle = bpy.types.SpaceView3D.draw_handler_add(
			cls._draw_callback, (), 'WINDOW', 'POST_VIEW'
		)
		cls._legend_handle = bpy.types.SpaceView3D.draw_handler_add(
			cls._draw_legend_callback, (), 'WINDOW', 'POST_PIXEL'
		)

		context.window_manager.modal_handler_add(self)
		_tag_redraw_3d(context)
		self.report({'INFO'}, "Portal edge overlay active — press ESC to dismiss")
		return {'RUNNING_MODAL'}

	@staticmethod
	def _draw_callback():
		from gpu_extras.batch import batch_for_shader
		import gpu

		shader = _get_builtin_shader('UNIFORM_COLOR', '3D_UNIFORM_COLOR')
		_setup_gpu_state()
		gpu.state.line_width_set(10.0)

		for color, verts in SWG_Debug_Portal_Edges._draw_groups:
			batch = batch_for_shader(shader, 'LINES', {"pos": verts})
			shader.uniform_float("color", color)
			batch.draw(shader)

		_restore_gpu_state()

	@staticmethod
	def _draw_legend_callback():
		_draw_legend(SWG_Debug_Portal_Edges._legend_entries, title="Portal Edges")
