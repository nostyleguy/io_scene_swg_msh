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

bl_info = {
	"name": "NSG SWG Tools",
	"author": "Nick Rafalski",
	"version": (3, 0, 9),
	"blender": (2, 81, 6),
	"location": "File > Import-Export",
	"description": "Import-Export SWG .msh, .mgn, .lod and .pob",
	"warning": "NOT Compatible with Blender 4.x yet! Features that use Face Maps (MGN occlusion, floor fallthroughs) will fail!",
	"doc_url": "None",
	"support": 'COMMUNITY',
	"category": "Import-Export",
}

if "bpy" in locals():
	import importlib
	importlib.reload(support)
	importlib.reload(extents)
	importlib.reload(swg_types)
	importlib.reload(nsg_iff)
	importlib.reload(vertex_buffer_format)
	importlib.reload(vector3D)
	importlib.reload(import_msh)
	importlib.reload(export_msh)
	importlib.reload(import_mgn)
	importlib.reload(export_mgn)
	importlib.reload(import_lod)
	importlib.reload(export_lod)
	importlib.reload(import_flr)
	importlib.reload(export_flr)
	importlib.reload(import_pob)
	importlib.reload(export_pob)
	importlib.reload(import_skt)
	importlib.reload(export_skt)
	importlib.reload(export_lmg)
	importlib.reload(export_sat)
else:
	from . import support
	from . import extents
	from . import swg_types
	from . import nsg_iff
	from . import vertex_buffer_format
	from . import vector3D
	from . import import_msh
	from . import export_msh
	from . import import_mgn
	from . import export_mgn
	from . import import_lod
	from . import export_lod
	from . import import_flr
	from . import export_flr
	from . import import_pob
	from . import export_pob
	from . import import_skt
	from . import export_skt
	from . import export_lmg
	from . import export_sat

from glob import glob
import bpy
from bpy.props import (
		BoolProperty,
		FloatProperty,
		StringProperty,
		EnumProperty,
		CollectionProperty
		)
from bpy_extras.io_utils import (
		ImportHelper,
		ExportHelper,
		orientation_helper,
		path_reference_mode,
		axis_conversion,
		)

import bpy, os, functools, base64, bmesh, math
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty
from mathutils import Vector, Matrix
import bpy
from bpy.types import (
	Gizmo,
	GizmoGroup,
)

def import_swg_file(context, file):
	obj=None
	SWG_ROOT=context.preferences.addons[__package__].preferences.swg_root
	fullpath = support.find_file(file, SWG_ROOT)
	if file.endswith(".apt"):
		apt = swg_types.AptFile(fullpath, "")	
	elif file.endswith(".lod"):
		lod = swg_types.LodFile(fullpath)
	elif file.endswith(".msh"):
		msh = swg_types.SWGMesh(fullpath, SWG_ROOT)
	else:
		print(f"Unhandled file extension in import_swg_file: {file}")
	
	return obj

class SWGPreferences(AddonPreferences):
	# this must match the add-on name, use '__package__'
	# when defining this in a submodule of a python package.
	bl_idname = __name__

	swg_root: StringProperty(
		name="SWG Client Extract Dir (should contain dirs like 'appearance', 'shader', 'texture', etc.",
		subtype='FILE_PATH',
	)

	convert_tex_to_png: BoolProperty(
		name="Convert Loaded Textures to PNG",
		description="When loading textures, copy and convert them from DDS to PNG format.",
		default=False,
	)

	def draw(self, context):
		layout = self.layout
		layout.prop(self, "swg_root")
		layout.prop(self, "convert_tex_to_png")

class OBJECT_OT_addon_prefs_swg(Operator):
	"""Display SWG Preferences"""
	bl_idname = "object.addon_swg_prefs"
	bl_label = "SWG Preferences"
	bl_options = {'REGISTER', 'UNDO'}
	

	def execute(self, context):
		preferences = context.preferences
		addon_prefs = preferences.addons[__name__].preferences

		info = f"Name: {__name__} Path: {addon_prefs.swg_root}"

		self.report({'INFO'}, info)
		print(info)

		return {'FINISHED'}

class ImportMSH(bpy.types.Operator, ImportHelper):
	"""Load a SWG Msh File"""
	bl_idname = "import_scene.msh"
	bl_label = "Import Msh"
	bl_options = {'PRESET', 'UNDO'}

	filename_ext = ".msh"
	filter_glob: StringProperty(
				default="*.msh",
				options={'HIDDEN'},
		)

	flip_uv_vertical: BoolProperty(
			name="Flip UV Vertically",
			description="SWG seems to interprte the DDS vertical axis opposite as Blender does. Need to flip UVs on import AND export to be able to use Blender UV mapping without being destructive.",
			default=True,
			)
	remove_duplicate_verts: BoolProperty(
			name="Remove Duplicate Verts",
			description="Attempt to remove verts that are probably duplicates (within 0.0001 units of each other)",
			default=True,
			)

	files: CollectionProperty(
			type=bpy.types.OperatorFileListElement,
			options={'HIDDEN', 'SKIP_SAVE'},
		)
			
	def execute(self, context):
		keywords = self.as_keywords(ignore=("filter_glob",
											"files",
											"filepath"))

			  
		for f in self.files:   
			dirname = os.path.dirname(self.filepath)
			filepath = os.path.join(dirname, f.name)
			

			print(f'IMPORTING: {self.filepath} {filepath}')
			result = import_msh.load_new(context, filepath, **keywords)

		# if 'ERROR' in result:
		#	 self.report({'ERROR'}, 'Something went wrong importing MESH')
		#	 return {'CANCELLED'}
		
		return {'FINISHED'}

	def draw(self, context):
		pass

class MSH_PT_import_option(bpy.types.Panel):
	bl_space_type = 'FILE_BROWSER'
	bl_region_type = 'TOOL_PROPS'
	bl_label = "Options"
	bl_parent_id = "FILE_PT_operator"

	@classmethod
	def poll(cls, context):
		sfile = context.space_data
		operator = sfile.active_operator

		return operator.bl_idname == "IMPORT_SCENE_OT_msh"

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		sfile = context.space_data
		operator = sfile.active_operator
		layout.prop(operator, 'flip_uv_vertical')
		layout.prop(operator, 'remove_duplicate_verts')

class ExportMSH(bpy.types.Operator, ExportHelper):
	"""Save a SWG .msh File"""

	bl_idname = "export_scene.msh"
	bl_label = 'Export Msh'
	bl_description = "Export SWG Mesh. Note, the filename you give won't be used, but the directory will. The final .msh filename(s) will be whatever the name of the Blender object is"
	bl_options = {'PRESET'}

	filename_ext = ".msh"
	filter_glob: StringProperty(
			default="*.msh",
			options={'HIDDEN'},
			)
	flip_uv_vertical: BoolProperty(
			name="Flip UV Vertically",
			description="SWG seems to flip DDS vertical axis, but blender doesn't. Need to flip UVs on import and export to be able to use Blender UV mapping without being destructive",
			default=True,
			)

	def invoke(self, context, _event):
		import os
		if not self.filepath:
			blend_filepath = context.blend_data.filepath
			if not blend_filepath:
				blend_filepath = "THE BLENDER OBJECT NAME WILL BE USED AS THE FILENAME, EXPORTED INTO THIS DIRECTORY!"
			else:
				blend_filepath = os.path.splitext(blend_filepath)[0]

			self.filepath = blend_filepath + self.filename_ext

		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

	def execute(self, context):
		keywords = self.as_keywords(ignore=("filter_glob",
											"check_existing"
											))
		return export_msh.save(context, **keywords)

	def draw(self, context):
		pass

class MSH_PT_export_option(bpy.types.Panel):
	bl_space_type = 'FILE_BROWSER'
	bl_region_type = 'TOOL_PROPS'
	bl_label = "Option"
	bl_parent_id = "FILE_PT_operator"

	@classmethod
	def poll(cls, context):
		sfile = context.space_data
		operator = sfile.active_operator
		return operator.bl_idname == "EXPORT_SCENE_OT_msh"

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		sfile = context.space_data
		operator = sfile.active_operator
		layout.prop(operator, 'flip_uv_vertical')

class MGN_PT_import_option(bpy.types.Panel):
	bl_space_type = 'FILE_BROWSER'
	bl_region_type = 'TOOL_PROPS'
	bl_label = "Options"
	bl_parent_id = "FILE_PT_operator"

	@classmethod
	def poll(cls, context):
		sfile = context.space_data
		operator = sfile.active_operator
		return operator.bl_idname == "IMPORT_SCENE_OT_mgn"

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		sfile = context.space_data
		operator = sfile.active_operator
		layout.prop(operator, "axis_forward")
		layout.prop(operator, "axis_up")

@orientation_helper(axis_forward='Z', axis_up='Y')
class ImportMGN(bpy.types.Operator, ImportHelper):
	"""Load a SWG MGN File"""
	bl_idname = "import_scene.mgn"
	bl_label = "Import Mgn"
	bl_options = {'PRESET', 'UNDO'}

	filename_ext = ".mgn"
	filter_glob: StringProperty(
				default="*.mgn",
				options={'HIDDEN'},
		)

	def execute(self, context):
		keywords = self.as_keywords(ignore=("axis_forward",
											"axis_up",
											"filter_glob",))

		global_matrix = (Matrix.Scale(1, 4) @
						 axis_conversion(to_forward=self.axis_forward,
										 to_up=self.axis_up,
										 ).to_4x4())
										
		keywords["global_matrix"] = global_matrix

		result = import_mgn.import_mgn(context, **keywords)
		if 'ERROR' in result:
			self.report({'ERROR'}, 'Something went wrong importing MGN')
			return {'CANCELLED'}
		
		return {'FINISHED'}

	def draw(self, context):
		pass

class ExportMGN(bpy.types.Operator, ExportHelper):
	'''Export MGN object'''
	bl_idname='export_scene.mgn'
	bl_label='Export Mgn'
	bl_options = {'PRESET'}

	bl_description = 'Export a SWG Animated Mesh.'

	filename_ext = ".mgn"
	filter_glob: StringProperty(default="*.mgn", options={'HIDDEN'})
	do_tangents : BoolProperty(name='DOT3', description="Include DOT3 tangent vectors.", default=True)
	
	def invoke(self, context, _event):
		import os
		if not self.filepath:
			blend_filepath = context.blend_data.filepath
			if not blend_filepath:
				blend_filepath = "THE BLENDER OBJECT NAME WILL BE USED AS THE FILENAME, EXPORTED INTO THIS DIRECTORY!"
			else:
				blend_filepath = os.path.splitext(blend_filepath)[0]

			self.filepath = blend_filepath + self.filename_ext

		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

	def execute(self, context):
		from . import export_mgn

		keywords = self.as_keywords(ignore=("check_existing","filter_glob"))
		print(f"Keyword args: {str(keywords)}")
		result = export_mgn.save(context, **keywords)
		if 'ERROR' in result:
			self.report({'ERROR'}, 'Something went wrong exporting MGN')
			return {'CANCELLED'}
		
		return {'FINISHED'}

	def draw(self, context):
		pass

class MGN_PT_export_option(bpy.types.Panel):
	bl_space_type = 'FILE_BROWSER'
	bl_region_type = 'TOOL_PROPS'
	bl_label = "Options"
	bl_parent_id = "FILE_PT_operator"

	@classmethod	
	def poll(cls, context):
		sfile = context.space_data
		operator = sfile.active_operator
		return operator.bl_idname == "EXPORT_SCENE_OT_mgn"

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.
		sfile = context.space_data
		operator = sfile.active_operator
		layout.prop(operator, 'do_tangents')

class ImportLOD(bpy.types.Operator, ImportHelper):
	"""Load a SWG LOD File"""
	bl_idname = "import_scene.lod"
	bl_label = "Import Lod"
	bl_options = {'PRESET', 'UNDO'}

	filename_ext = ".lod"
	filter_glob: StringProperty(
				default="*.lod",
				options={'HIDDEN'},
		)

	flip_uv_vertical: BoolProperty(
			name="Flip UV Vertically",
			description="SWG seems to interpret the DDS vertical axis opposite as Blender does. Need to flip UVs on import AND export to be able to use Blender UV mapping without being destructive.",
			default=True,
			)
	remove_duplicate_verts: BoolProperty(
			name="Remove Duplicate Verts",
			description="Attempt to remove verts that are probably duplicates (within 0.0001 units of each other)",
			default=True,
			)

	files: CollectionProperty(
			type=bpy.types.OperatorFileListElement,
			options={'HIDDEN', 'SKIP_SAVE'},
		)
			
	def execute(self, context):
		keywords = self.as_keywords(ignore=("filter_glob",
											"files",
											"filepath"))			  
		for f in self.files:   
			dirname = os.path.dirname(self.filepath)
			filepath = os.path.join(dirname, f.name) 
			result = import_lod.load_new(context, filepath, parent = None, **keywords)
			if 'ERROR' in result:
				self.report({'ERROR'}, 'Something went wrong importing LOD')
				return {'CANCELLED'}		
		return {'FINISHED'}

	def invoke(self, context, _event):
		
		if context.preferences.addons[__package__].preferences.swg_root != "":			
			self.filepath = context.preferences.addons[__package__].preferences.swg_root +"/appearance/lod/"
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

	def draw(self, context):
		pass

class LOD_PT_import_option(bpy.types.Panel):
	bl_space_type = 'FILE_BROWSER'
	bl_region_type = 'TOOL_PROPS'
	bl_label = "LOD Options"
	bl_parent_id = "FILE_PT_operator"

	@classmethod
	def poll(cls, context):
		sfile = context.space_data
		operator = sfile.active_operator

		return operator.bl_idname == "IMPORT_SCENE_OT_lod"

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		sfile = context.space_data
		operator = sfile.active_operator
		
		layout.prop(operator, 'flip_uv_vertical')
		layout.prop(operator, 'remove_duplicate_verts')

class ExportLOD(bpy.types.Operator, ExportHelper):
	"""Save a SWG .lod File"""

	bl_idname = "export_scene.lod"
	bl_label = 'Export Lod'
	bl_description = "Export SWG Mesh. Note, the filename you give won't be used, but the directory will. The final .lod filename(s) will be whatever the name of the Blender object is"
	bl_options = {'PRESET'}

	filename_ext = ".lod"
	filter_glob: StringProperty(
			default="*.lod",
			options={'HIDDEN'},
			)

	flip_uv_vertical: BoolProperty(
			name="Flip UV Vertically",
			description="SWG seems to flip DDS vertical axis, but blender doesn't. Need to flip UVs on import and export to be able to use Blender UV mapping without being destructive",
			default=True,
			)

	export_children: BoolProperty(
			name="Export Children",
			description="When checked, will export children (under 'LODs') to individual .msh files. Uncheck to save export time if you only modified collision/hardpoints/floor/etc.",
			default=True,
			)

	def invoke(self, context, _event):
		
		if context.preferences.addons[__package__].preferences.swg_root != "":			
			self.filepath = context.preferences.addons[__package__].preferences.swg_root +"/appearance/lod/"

		self.filepath += "THE BLENDER COLLECTION NAME WILL BE USED AS THE FILENAME, EXPORTED INTO THIS DIRECTORY!"

		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

	def execute(self, context):
		keywords = self.as_keywords(ignore=("filter_glob",
											"check_existing"
											))
		return export_lod.save(context, **keywords)

	def draw(self, context):
		pass

class LOD_PT_export_option(bpy.types.Panel):
	bl_space_type = 'FILE_BROWSER'
	bl_region_type = 'TOOL_PROPS'
	bl_label = "Option"
	bl_parent_id = "FILE_PT_operator"

	@classmethod
	def poll(cls, context):
		sfile = context.space_data
		operator = sfile.active_operator

		return operator.bl_idname == "EXPORT_SCENE_OT_lod"

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		sfile = context.space_data
		operator = sfile.active_operator
		
		layout.prop(operator, 'flip_uv_vertical')
		layout.prop(operator, 'export_children')

class ExportLMG(bpy.types.Operator, ExportHelper):
	"""Save a SWG .lmg File"""

	bl_idname = "export_scene.lmg"
	bl_label = 'Export LMG'
	bl_description = "Export SWG Animated Meshes. Note, the filename you give won't be used, but the directory will. The final .lmg filename will be whatever the name of the Blender collection is."
	bl_options = {'PRESET'}

	filename_ext = ".lmg"
	filter_glob: StringProperty(default="*.lmg", options={'HIDDEN'})
	
	export_mesh_objects: BoolProperty(
			name="Export Mesh Objects",
			description="When checked, will export mesh objects to individual .mgn files. Uncheck to save export time if you haven't modified the mesh objects.",
			default=True,
			)
	
	do_tangents : BoolProperty(name='DOT3', description="Include DOT3 tangent vectors.", default=True)

	def invoke(self, context, _event):
		
		if context.preferences.addons[__package__].preferences.swg_root != "":			
			self.filepath = context.preferences.addons[__package__].preferences.swg_root +"/appearance/mesh/"

		self.filepath += "THE BLENDER COLLECTION NAME WILL BE USED AS THE FILENAME, EXPORTED INTO THIS DIRECTORY!"

		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

	def execute(self, context):
		keywords = self.as_keywords(ignore=("filter_glob", "check_existing"))
		return export_lmg.save(context, **keywords)

	def draw(self, context):
		pass

class LMG_PT_export_option(bpy.types.Panel):
	bl_space_type = 'FILE_BROWSER'
	bl_region_type = 'TOOL_PROPS'
	bl_label = "Option"
	bl_parent_id = "FILE_PT_operator"

	@classmethod
	def poll(cls, context):
		sfile = context.space_data
		operator = sfile.active_operator
		return operator.bl_idname == "EXPORT_SCENE_OT_lod"

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.
		sfile = context.space_data
		operator = sfile.active_operator
		layout.prop(operator, 'export_mesh_objects')
		layout.prop(operator, 'do_tangents')

class ImportPOB(bpy.types.Operator, ImportHelper):
	"""Load a SWG POB File"""
	bl_idname = "import_scene.pob"
	bl_label = "Import POB"
	bl_options = {'PRESET', 'UNDO'}

	filename_ext = ".pob"
	filter_glob: StringProperty(
				default="*.pob",
				options={'HIDDEN'},
		)

	flip_uv_vertical: BoolProperty(
			name="Flip UV Vertically",
			description="SWG seems to interprte the DDS vertical axis opposite as Blender does. Need to flip UVs on import AND export to be able to use Blender UV mapping without being destructive.",
			default=True,
			)
	remove_duplicate_verts: BoolProperty(
			name="Remove Duplicate Verts",
			description="Attempt to remove verts that are probably duplicates (within 0.0001 units of each other)",
			default=True,
			)

	files: CollectionProperty(
			type=bpy.types.OperatorFileListElement,
			options={'HIDDEN', 'SKIP_SAVE'},
		)
			
	def execute(self, context):
		keywords = self.as_keywords(ignore=("filter_glob",
											"files",
											"filepath"))
			  
		for f in self.files:   
			dirname = os.path.dirname(self.filepath)
			filepath = os.path.join(dirname, f.name) 

			print(f'IMPORTING: {self.filepath} {filepath}')	
			result = import_pob.load_new(context, filepath, **keywords)
			if 'ERROR' in result:
				self.report({'ERROR'}, 'Something went wrong importing LOD')
				return {'CANCELLED'}
		
		return {'FINISHED'}

	def draw(self, context):
		pass

class POB_PT_import_option(bpy.types.Panel):
	bl_space_type = 'FILE_BROWSER'
	bl_region_type = 'TOOL_PROPS'
	bl_label = "POB Import Options"
	bl_parent_id = "FILE_PT_operator"

	@classmethod
	def poll(cls, context):
		sfile = context.space_data
		operator = sfile.active_operator

		return operator.bl_idname == "IMPORT_SCENE_OT_pob"

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		sfile = context.space_data
		operator = sfile.active_operator
		layout.prop(operator, 'flip_uv_vertical')
		layout.prop(operator, 'remove_duplicate_verts')

class ExportPOB(bpy.types.Operator, ExportHelper):
	"""Save a SWG .pob File"""

	bl_idname = "export_scene.pob"
	bl_label = 'Export Pob'
	bl_description = "Export SWG Pob. Note, the filename you give won't be used, but the directory will. The final .pob filename will be whatever the name of the Blender object is"
	bl_options = {'PRESET'}

	filename_ext = ".pob"
	filter_glob: StringProperty(
			default="*.pob",
			options={'HIDDEN'},
			)

	flip_uv_vertical: BoolProperty(
			name="Flip UV Vertically",
			description="SWG seems to flip DDS vertical axis, but blender doesn't. Need to flip UVs on import and export to be able to use Blender UV mapping without being destructive",
			default=True,
			)

	export_children: BoolProperty(
			name="Export Children",
			description="When checked, will export children (under 'LODs') to individual .msh files. Uncheck to save export time if you only modified collision/hardpoints/floor/etc.",
			default=True,
			)
	
	use_imported_crc: BoolProperty(
			name="Use Imported Crc",
			description="Only valid on POBs originally imported from SWG. This will keep the same Crc (hash) as them, which is necessary to keep them synced in World Snapshots",
			default=False,
			)

	def invoke(self, context, _event):
		import os
		if not self.filepath:
			blend_filepath = context.blend_data.filepath
			if not blend_filepath:
				blend_filepath = "THE BLENDER OBJECT NAME WILL BE USED AS THE FILENAME, EXPORTED INTO THIS DIRECTORY!"
			else:
				blend_filepath = os.path.splitext(blend_filepath)[0]

			self.filepath = blend_filepath + self.filename_ext

		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

	def execute(self, context):
		keywords = self.as_keywords(ignore=("filter_glob",
											"check_existing"
											))
		result = export_pob.save(context, **keywords)
		if result['status'] == 'ERROR':
			self.report({'ERROR'}, result['message'])
			return {'CANCELLED'}
		else:
			return {'FINISHED'}

	def draw(self, context):
		pass

class POB_PT_export_option(bpy.types.Panel):
	bl_space_type = 'FILE_BROWSER'
	bl_region_type = 'TOOL_PROPS'
	bl_label = "Option"
	bl_parent_id = "FILE_PT_operator"

	@classmethod
	def poll(cls, context):
		sfile = context.space_data
		operator = sfile.active_operator

		return operator.bl_idname == "EXPORT_SCENE_OT_pob"

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		sfile = context.space_data
		operator = sfile.active_operator
		
		layout.prop(operator, 'flip_uv_vertical')
		layout.prop(operator, 'export_children')
		layout.prop(operator, 'use_imported_crc')

class ImportSKT(bpy.types.Operator, ImportHelper):
	"""Load a SWG SKT File"""
	bl_idname = "import_scene.skt"
	bl_label = "Import Skt"
	bl_options = {'PRESET', 'UNDO'}

	filename_ext = ".skt"
	filter_glob: StringProperty(default = "*.skt", options = {'HIDDEN'},)

	lod_0_only: BoolProperty(
			name="LOD 0 Only",
			description="Skeleton files typically contain multiple levels of detail to improve performance. Enabling this option to only load the highest detail skeleton.",
			default=False,
			)
	
	connect_bones: BoolProperty(
			name="Connect Bones",
			description="SWG skeletons use joints rather than bones. The difference is they have only a position and direction but no length. Sometimes it may provide a more accurate auto weight paint to a mesh if the bones are connected. Enabling this option connects bones' tails to their children.",
			default=False,
			)
	
	show_bone_names: BoolProperty(
			name="Show Bone Names",
			description="Toggles bone name visibility.",
			default=False,
			)
	
	show_bone_axes: BoolProperty(
			name="Show Bone Axes",
			description="Toggles bone axis visibility. Useful for joint rotation debugging.",
			default=False,
			)

	files: CollectionProperty(type = bpy.types.OperatorFileListElement, options = {'HIDDEN', 'SKIP_SAVE'},)

	def execute(self, context):
		keywords = self.as_keywords(ignore=("filter_glob",
											"files",
											"filepath"))
		
		for f in self.files:   
			dirname = os.path.dirname(self.filepath)
			filepath = os.path.join(dirname, f.name)
			print(f'IMPORTING: {self.filepath} {filepath}')
			result = import_skt.import_skt(context, filepath, **keywords)
		
		return {'FINISHED'}

	def draw(self, context):
		pass

class SKT_PT_import_option(bpy.types.Panel):
	bl_space_type = 'FILE_BROWSER'
	bl_region_type = 'TOOL_PROPS'
	bl_label = "SKT Options"
	bl_parent_id = "FILE_PT_operator"

	@classmethod
	def poll(cls, context):
		sfile = context.space_data
		operator = sfile.active_operator

		return operator.bl_idname == "IMPORT_SCENE_OT_skt"

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		sfile = context.space_data
		operator = sfile.active_operator
		
		layout.prop(operator, 'lod_0_only')
		layout.prop(operator, 'connect_bones')
		layout.prop(operator, 'show_bone_names')
		layout.prop(operator, 'show_bone_axes')

class ExportSKT(bpy.types.Operator, ExportHelper):
	"""Save a SWG .skt File"""
	bl_idname = "export_scene.skt"
	bl_label = 'Export Skt'
	bl_description = "Export SWG Skeleton. Note, the filename you give won't be used, but the directory will. The final .skt filename will be the name of the Blender collection."
	bl_options = {'PRESET'}

	filename_ext = ".skt"
	filter_glob: StringProperty(default="*.skt", options={'HIDDEN'})

	def invoke(self, context, _event):
		if context.preferences.addons[__package__].preferences.swg_root != "":			
			self.filepath = context.preferences.addons[__package__].preferences.swg_root +"/appearance/skeleton/"

		self.filepath += "THE BLENDER COLLECTION NAME WILL BE USED AS THE FILENAME, EXPORTED INTO THIS DIRECTORY!"

		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

	def execute(self, context):
		keywords = self.as_keywords(ignore=("filter_glob", "check_existing"))
		return export_skt.save(context, **keywords)

	def draw(self, context):
		pass

class ExportSAT(bpy.types.Operator, ExportHelper):
	"""Save a SWG .sat File"""

	bl_idname = "export_scene.sat"
	bl_label = 'Export SAT'
	bl_description = "Export SWG Skeletal Appearance Template. Note, the filename you give won't be used, but the directory will. The final .sat filename will be whatever the name of the Blender collection is."
	bl_options = {'PRESET'}

	filename_ext = ".sat"
	filter_glob: StringProperty(default="*.sat", options={'HIDDEN'})

	create_anim_controller : BoolProperty(name='Create Animation Controller', description="Sets the state of the Create Animation Controller setting in the SAT's INFO chunk.", default=True)
	export_lmgs: BoolProperty(name="Export LMGs", description="When checked, will export LMG collections to individual .lmg files.", default=True)
	export_mgns: BoolProperty(name="Export Mesh Objects", description="When checked, will export mesh objects to individual .mgn files.", default=True)
	do_tangents : BoolProperty(name='DOT3', description="Include DOT3 tangent vectors.", default=True)
	export_skts: BoolProperty(name="Export Skeletons", description="When checked, will export skeleton collections to individual .skt files.", default=True)

	def invoke(self, context, _event):
		
		if context.preferences.addons[__package__].preferences.swg_root != "":			
			self.filepath = context.preferences.addons[__package__].preferences.swg_root +"/appearance/mesh/"

		self.filepath += "THE BLENDER COLLECTION NAME WILL BE USED AS THE FILENAME, EXPORTED INTO THIS DIRECTORY!"

		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

	def execute(self, context):
		keywords = self.as_keywords(ignore=("filter_glob", "check_existing"))
		return export_sat.save(context, **keywords)

	def draw(self, context):
		pass

class SAT_PT_export_option(bpy.types.Panel):
	bl_space_type = 'FILE_BROWSER'
	bl_region_type = 'TOOL_PROPS'
	bl_label = "Option"
	bl_parent_id = "FILE_PT_operator"

	@classmethod
	def poll(cls, context):
		sfile = context.space_data
		operator = sfile.active_operator
		return operator.bl_idname == "EXPORT_SCENE_OT_lod"

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.
		sfile = context.space_data
		operator = sfile.active_operator
		layout.prop(operator, 'create_anim_controller')
		layout.prop(operator, 'export_lmgs')
		layout.prop(operator, 'export_mgns')
		layout.prop(operator, 'do_tangents')
		layout.prop(operator, 'export_skts')

def import_operators(self, context):
	self.layout.operator(ImportLOD.bl_idname, text="SWG Static Level of Detail (.lod)")
	self.layout.operator(ImportMSH.bl_idname, text="SWG Static Mesh (.msh)")
	self.layout.operator(ImportMGN.bl_idname, text="SWG Animated Mesh (.mgn)")
	self.layout.operator(ImportSKT.bl_idname, text="SWG Skeleton (.skt)")
	self.layout.operator(ImportPOB.bl_idname, text="SWG Portalized Object (.pob)")

def export_operators(self, context):
	self.layout.operator(ExportLOD.bl_idname, text="SWG Static Level of Detail (.lod)")
	self.layout.operator(ExportMSH.bl_idname, text="SWG Static Mesh (.msh)")
	self.layout.operator(ExportSAT.bl_idname, text="SWG Skeletal Animation Template (.sat)")
	self.layout.operator(ExportLMG.bl_idname, text="SWG Animated Level of Detail (.lmg)")
	self.layout.operator(ExportMGN.bl_idname, text="SWG Animated Mesh (.mgn)")
	self.layout.operator(ExportSKT.bl_idname, text="SWG Skeleton (.skt)")
	self.layout.operator(ExportPOB.bl_idname, text="SWG Portalized Object (.pob)")

def dump(obj, text):
	for attr in dir(obj):
		print("%r.%s = %s" % (obj, attr, getattr(obj, attr)))

# == OPERATORS
class SWG_Load_Materials_Operator(bpy.types.Operator):
	bl_idname = "object.swg_load_materials"
	bl_label = "Find and load materials"
	bl_description = '''Attempts to locate SWG shaders that match material names and set their properties automatically. 
NOTE: If this option is disabled, you need to set the "SWG Client Extract Dir" property in the add-on preferences, and have 1 object selected'''
	
	@classmethod
	def poll(cls, context):
		return context.active_object != None and (context.preferences.addons[__package__].preferences.swg_root != "")

	def invoke(self, context, event):
		swg_root = context.preferences.addons[__package__].preferences.swg_root
		tex_to_png = context.preferences.addons[__package__].preferences.convert_tex_to_png
		print(f"invoke with: {context.active_object.name}")	 
		for slot in context.active_object.material_slots:
			mat = slot.material	
			print(f"Looking for material: {mat.name}")
			path=f'shader/{mat.name}.sht'		
			real_shader_path = support.find_file(path, swg_root)
			if real_shader_path:
				print(f'..found it...')
				shader = swg_types.SWGShader(real_shader_path, swg_root)
				support.configure_material_from_swg_shader(mat,shader, swg_root, tex_to_png)
			else:
				print(f"WARNING: Couldn't locate real shader path for: {path}")

		return {'FINISHED'}

class SWG_Add_Material_Operator(bpy.types.Operator):
	bl_idname = "object.swg_add_material"
	bl_label = "Add SWG Shader as Material"
	bl_description = '''If this option is disabled, you need to set the "SWG Client Extract Dir" property in the add-on preferences, and have 1 object selected'''

	filename_ext = ".sht"
	filter_glob : StringProperty(default="*.sht", options={'HIDDEN'})
	filepath: StringProperty(default="*.sht",subtype='FILE_PATH')
	
	@classmethod
	def poll(cls, context):
		return context.active_object != None and (context.preferences.addons[__package__].preferences.swg_root != "")

	def execute(self, context):
		swg_root = context.preferences.addons[__package__].preferences.swg_root
		tex_to_png = context.preferences.addons[__package__].preferences.convert_tex_to_png
		context.active_object.data.materials.append(None)
		shader = swg_types.SWGShader(support.clean_path(self.properties.filepath), swg_root)
		material = bpy.data.materials.new(shader.stripped_shader_name()) 
		context.active_object.material_slots[len(context.active_object.material_slots)-1].material = material
		support.configure_material_from_swg_shader(material, shader, swg_root, tex_to_png)
		return {'FINISHED'}
 
	def invoke(self, context, event):
		self.filepath = context.preferences.addons[__package__].preferences.swg_root +"/shader/"
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

	def draw(self, context):
		pass

class SWG_Create_Apt_For_Msh(bpy.types.Operator):
	bl_idname = "object.swg_create_apt_msh"
	bl_label = "Create a SWG .apt for this .msh"
	bl_description = '''If this option is disabled, you need to have 1 object selected'''

	filename_ext = ".apt"
	filter_glob : StringProperty(default="*.apt", options={'HIDDEN'})
	filepath: StringProperty(default="test.apt",subtype='FILE_PATH')

	@classmethod
	def poll(cls, context):
		return context.active_object != None

	def execute(self, context): 
		apt_path =  self.properties.filepath 
		apt_reference = f"appearance/mesh/{context.active_object.name}.msh"
		apt = swg_types.AptFile(apt_path, apt_reference)
		apt.write()
		return {'FINISHED'}

	def invoke(self, context, event):
		default_filename=context.active_object.name+".apt"
		self.filename = default_filename
		self.filepath = default_filename
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
 
	def draw(self, context):
		pass

class SWG_Create_Sat_For_Mgn(bpy.types.Operator):
	bl_idname = "object.swg_create_sat_mgn"
	bl_label = "Create a SWG .sat and .lmg for this .mgn"
	bl_description = '''If this option is disabled, you need to have 1 object selected'''
 

	filename_ext = ".sat"
	filter_glob : StringProperty(default="*.sat", options={'HIDDEN'})
	filepath: StringProperty(default="test.sat",subtype='FILE_PATH')
	num_lods: IntProperty(name="Number LODs", min=1, max=10, default=1)
	
	@classmethod
	def poll(cls, context):
		return context.active_object != None

	def execute(self, context): 
		sat_path =  self.properties.filepath

		lmg_path = os.path.dirname(sat_path) + "/mesh/" + sat_path.split('\\')[-1].split('.')[0] + ".lmg"
		lmg = swg_types.LmgFile(lmg_path, [context.active_object.name.lower()]* self.num_lods)
		lmg.write()

		skels=[]
		for cp in context.active_object.keys():
			if cp.startswith("SKTM_"):
				skels.append(context.active_object[cp])
				print(f"Added SKTM: {context.active_object[cp]}")
		sat = swg_types.SatFile(sat_path, [context.active_object.name.lower()], skels)
		sat.write()

		return {'FINISHED'}

	def invoke(self, context, event):
		default_filename=context.active_object.name.lower()+".sat"
		self.filename = default_filename
		self.filepath = default_filename
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
 
	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		sfile = context.space_data
		operator = sfile.active_operator
		layout.prop(operator, "num_lods")

class SWG_Load_Skeleton_For_MGN(bpy.types.Operator):
	bl_idname = "object.swg_load_skt_mgn"
	bl_label = "Load Bones from skeleton"
	bl_description = '''If this option is disabled, you need to have 1 object selected'''

	filename_ext = ".skt"
	filter_glob : StringProperty(default="*.skt", options={'HIDDEN'})
	filepath: StringProperty(default="test.skt",subtype='FILE_PATH')

	@classmethod
	def poll(cls, context):
		return context.active_object != None

	def execute(self, context): 
		skt_path =  self.properties.filepath
		skt = swg_types.SktFile(skt_path)
		skt.load()
		print(f"SKT: {skt}")

		for bone in skt.joint_names:
			exists = False
			for vg in context.active_object.vertex_groups:
				if vg.name == bone:
					exists = True
					print (f"Skipping re-adding bone: {bone}")
			if not exists:
				context.active_object.vertex_groups.new(name=bone)
				print (f"Added bone: {bone}")

		return {'FINISHED'}

	def invoke(self, context, event):
		# default_filename=context.active_object.name.lower()+".skt"
		# self.filepath = default_filename		
		if context.preferences.addons[__package__].preferences.swg_root != "":			
			self.filepath = context.preferences.addons[__package__].preferences.swg_root +"/appearance/skeleton/"
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
 
	def draw(self, context):
		pass

class SWG_Initialize_MGN_From_Existing(bpy.types.Operator):
	bl_idname = "object.swg_initialize_mgn"
	bl_label = "Initialize MGN data (occlusions, bones, blends) from an existing MGN"
	bl_description = '''If this option is disabled, you need to have 1 object selected'''

	filename_ext = ".mgn"
	filter_glob : StringProperty(default="*.mgn", options={'HIDDEN'})
	filepath: StringProperty(default="test.mgn",subtype='FILE_PATH')

	@classmethod
	def poll(cls, context):
		return context.active_object != None

	def execute(self, context): 
		mgn_path =  self.properties.filepath
		mgn = swg_types.SWGMgn(mgn_path,context.preferences.addons[__package__].preferences.swg_root)
		mgn.load()
		scene_object = context.active_object
		print(f"mgn: {mgn}")
		
		for bone in mgn.joint_names:
			vg = scene_object.vertex_groups.new(name=bone)

		scene_object.shape_key_add(name='Basis')
		for i, blend in enumerate(mgn.blends):
			sk = scene_object.shape_key_add(name=blend.name)
		
		for i, skel in enumerate(mgn.skeletons):
			scene_object[f'SKTM_{i}'] = skel

		for zone in mgn.occlusions:
			scene_object["OZN_"+zone[0]] = zone[2]

		scene_object[f'OCC_LAYER'] = mgn.occlusion_layer

		if mgn.binary_hardpoints:
			scene_object["HPTS"] = base64.b64encode(mgn.binary_hardpoints).decode('ASCII')

		if mgn.binary_trts:
			scene_object["TRTS"] = base64.b64encode(mgn.binary_trts).decode('ASCII')

		if mgn.occlusion_zones:
			for i, ozc in enumerate(mgn.occlusion_zones):
				face_map = scene_object.face_maps.new(name=ozc[0])
				face_map.add(ozc[1])

		return {'FINISHED'}

	def invoke(self, context, event):	 
		if context.preferences.addons[__package__].preferences.swg_root != "":			
			self.filepath = context.preferences.addons[__package__].preferences.swg_root +"/appearance/mesh/"
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
 
	def draw(self, context):
		pass

class SWG_Swap_Bone_Names_To_Source(bpy.types.Operator):
	bl_idname = "object.swg_swap_bone_names_to_source"
	bl_label = "Swap Bone Names to Source Engine"
	bl_description = '''If this option is disabled, you need to have 1 object selected'''

	@classmethod
	def poll(cls, context):
		return context.active_object != None

	def invoke(self, context, event):
		swg_to_source_map={
			"root":"ValveBiped.Bip01_Pelvis",
			"spine1":"ValveBiped.Bip01_Spine",
			"spine2":"ValveBiped.Bip01_Spine1",
			"spine3":"ValveBiped.Bip01_Spine2",
			"neck":"ValveBiped.Bip01_Spine4",
			"head":"ValveBiped.Bip01_Head1",
			"larm":"ValveBiped.Bip01_L_UpperArm",
			"lforearm":"ValveBiped.Bip01_L_Forearm",
			"lulna":"ValveBiped.Bip01_L_Ulna",
			"lwrist":"ValveBiped.Bip01_L_Hand",
			"lthigh":"ValveBiped.Bip01_L_Thigh",
			"lshin":"ValveBiped.Bip01_L_Calf",
			"lankle":"ValveBiped.Bip01_L_Foot",
			"lclav":"ValveBiped.Bip01_L_Clavicle",
			"ltoe":"ValveBiped.Bip01_L_Toe0",
			"lthumb01":"ValveBiped.Bip01_L_Finger0",
			"lthumb02":"ValveBiped.Bip01_L_Finger01",
			"lindex01":"ValveBiped.Bip01_L_Finger1",
			"lindex02":"ValveBiped.Bip01_L_Finger11",
			"lring01":"ValveBiped.Bip01_L_Finger2",
			"lring02":"ValveBiped.Bip01_L_Finger21",
			"rarm":"ValveBiped.Bip01_R_UpperArm",
			"rforearm":"ValveBiped.Bip01_R_Forearm",
			"rulna":"ValveBiped.Bip01_R_Ulna",
			"rwrist":"ValveBiped.Bip01_R_Hand",
			"rthigh":"ValveBiped.Bip01_R_Thigh",
			"rshin":"ValveBiped.Bip01_R_Calf",
			"rankle":"ValveBiped.Bip01_R_Foot",
			"rclav":"ValveBiped.Bip01_R_Clavicle",
			"rtoe":"ValveBiped.Bip01_R_Toe0",
			"rthumb01":"ValveBiped.Bip01_R_Finger0",
			"rthumb02":"ValveBiped.Bip01_R_Finger01",
			"rindex01":"ValveBiped.Bip01_R_Finger1",
			"rindex02":"ValveBiped.Bip01_R_Finger11",
			"rring01":"ValveBiped.Bip01_R_Finger2",
			"rring02":"ValveBiped.Bip01_R_Finger21",
		}
		
		scene_object = context.active_object
		print(f"Swapping bones on: {scene_object.name}")
		for vg in scene_object.vertex_groups:
			if vg.name in swg_to_source_map:
				vg.name = swg_to_source_map[vg.name]

		return {'FINISHED'}
 
	def draw(self, context):
		pass

class SWG_Generate_Blends_From_Other(bpy.types.Operator):
	bl_idname = "object.swg_generate_blends_from_other"
	bl_label = "Generate Blend Shapes from Other"
	bl_description = '''If this option is disabled, you need to have 2 objects selected'''

	@classmethod
	def poll(cls, context):
		return len(context.selected_objects) == 2

	def invoke(self, context, event):
		
		destination = context.active_object
		source = None
		for object in context.selected_objects:
			if object != destination:
				source = object
				break

		print(f"Source: {source.name} Desination {destination.name}")

		if source.type != 'MESH' or destination.type != 'MESH':
			print ("Error. Both selected objects must be meshes!")
			return {'CANCELLED'}

		sm = source.to_mesh()
		dm = destination.to_mesh() 
		if sm == None or dm == None:
			print (f"Error. Couldn't get Mesh from one or the other!")
			return {'CANCELLED'}

		keys = sm.shape_keys
		print(f"Generating Shap Keys on {dm.name} from : {sm.name} number of keys: {str(len(sm.shape_keys.key_blocks))}")

		sverts = sm.vertices
		dverts = dm.vertices

		closest_vert_map={}

		for dv in dverts:
			dist = float('inf')
			closest_vert=None
			for sv in sverts:
				d = (Vector(dv.co) - Vector(sv.co)).magnitude
				if d < dist:
					dist = d
					closest_vert = sv
			closest_vert_map[dv.index] = closest_vert.index

		#print(f"Closest Vert Map:  {str(closest_vert_map)}")

		basis = keys.key_blocks[0].data
		for key in keys.key_blocks:
			sk = destination.shape_key_add(name=key.name)

			# deltas=key.data
			# for i, delta in enumerate(deltas):
			#	 dv = sverts[i].co - delta.co
			#	 print(f"{sm.name} Shape {key.name}: Vert {i} has position {sverts[i].co} delta: {delta.co} diff: {dv}")

			if(key.name == "Basis"):
				print(f"Skipping Basis...")
				continue

			# for each vert in Destination Mesh, add a delta to the Shape key based on its corresponding vert's delta in the same key of the other mesh...
			for vert in dverts:
				corresponding_index = closest_vert_map[vert.index]
				delta = key.data[corresponding_index].co - basis[corresponding_index].co
				#print(f"Key: {sk.name} Vert: {vert.index} Source Vert was: {corresponding_index} with Original Pos: {sverts[corresponding_index].co} Basis: {basis[corresponding_index].co} ShapeKeyPos: {key.data[corresponding_index].co} Delta: {delta} Final: {vert.co+delta}")
				sk.data[vert.index].co = vert.co + delta
			print(f"Completed Generating: {sk.name}")

		return {'FINISHED'}
 
	def draw(self, context):
		pass

class SWG_Load_Flr(bpy.types.Operator):
	bl_idname = "object.swg_load_flr"
	bl_label = "Load Floor File"
	bl_description = '''Loads a floor file'''

	filename_ext = ".flr"
	filter_glob : StringProperty(default="*.flr", options={'HIDDEN'})
	filepath: StringProperty(default="test.flr",subtype='FILE_PATH')

	@classmethod
	def poll(cls, context):
		return True

	def execute(self, context):
		import_flr.import_flr(context, self.properties.filepath)
		return {'FINISHED'}

	def invoke(self, context, event):
		if context.preferences.addons[__package__].preferences.swg_root != "":			
			self.filepath = context.preferences.addons[__package__].preferences.swg_root +"/appearance/collision/"
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
 
	def draw(self, context):		
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.
		sfile = context.space_data

class SWG_Write_Flr(bpy.types.Operator):
	bl_idname = "object.swg_write_flr"
	bl_label = "Write Floor File"
	bl_description = '''Writes a floor file'''

	filename_ext = ".flr"
	filter_glob : StringProperty(default="*.flr", options={'HIDDEN'})
	filepath: StringProperty(default="test.flr",subtype='FILE_PATH')

	@classmethod
	def poll(cls, context):
		return context.active_object != None

	def execute(self, context):
		export_flr.export_flr(context, self.properties.filepath)

		return {'FINISHED'}

	def invoke(self, context, event):
		import os
		blend_filepath = "THE BLENDER OBJECT NAME WILL BE USED AS THE FILENAME, EXPORTED INTO THIS DIRECTORY!"
		self.filepath = blend_filepath + self.filename_ext
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
 
	def draw(self, context):		
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.
		sfile = context.space_data
		operator = sfile.active_operator

class SWG_Visualize_Floor_Pathgraph(bpy.types.Operator):
	bl_idname = "object.swg_visualize_flr_pathgraph"
	bl_label = "Visualize Floor Pathgraph"
	bl_description = '''Visualizes how SWG will (probably) connect your CellWaypoints'''

	@classmethod
	def poll(cls, context):
		return context.active_object != None

	def execute(self, context):
		tmpFile= f"{os.path.dirname(context.blend_data.filepath)}/debugPathgraph.flr"
		objects = context.selected_objects
		floor=None
		for ob in objects:
			if ob.type != 'MESH':
				continue
			else:
				result, floor = export_flr.export_one(tmpFile, ob, [])
				
				if not 'FINISHED' in result:
					return {'ERROR'}
				else:
					break

		if floor == None:
			print(f"Error! Couldn't export .flr from {ob.name}")
			return {'ERROR'}

		print(f"Visualizing pathgraph with {len(floor.pathGraph.nodes)} nodes and {len(floor.pathGraph.edges)} edges...")
		if 'FINISHED' not in result:
			return {'ERROR'}
		else:
			try:
				col = bpy.data.collections["VisualizePathgraph"]
			except KeyError:
				col = bpy.data.collections.new("VisualizePathgraph")
				bpy.context.scene.collection.children.link(col)

			for obj in col.objects:
					bpy.data.objects.remove(obj, do_unlink=True)
			support.create_pathgraph(col, floor.pathGraph)

		return {'FINISHED'}
 
	def draw(self, context):
		pass

class SWG_Debug_Portal_Edges(bpy.types.Operator):
	bl_idname = "object.swg_debug_portal_edges"
	bl_label = "Debug Portal Edges"
	bl_description = '''Print info about which floor triangle edges currently would get marked as portals'''

	@classmethod
	def poll(cls, context):
		return context.active_object != None

	def execute(self, context):
		#tmpFile= f"os.path.dirname(context.blend_data.filepath)/debugPathgraph.flr"
		objects = context.selected_objects
		floor=None
		for obj in objects:
			if obj.type != 'MESH' or not obj.name.startswith("Floor"):
				print(f"Skipping non 'Floor_' selected object: {obj.name}")
				continue
			else:
				for col in obj.users_collection:
					for child in col.children:
						if child.name.startswith("Portals"):
							portal_objects = []
							for pid, candidate in enumerate(child.objects):
								if candidate.type != 'MESH' or not export_pob.is_portal_passable(candidate):
									continue
								portal_objects.append([candidate, pid])
							print(f"{obj.name} looking for portals that intersect floor triangles...")
							export_flr.create_floor_triangles_from_mesh(obj, obj.to_mesh(), portal_objects)		

		return {'FINISHED'}
 
	def draw(self, context):
		pass

class SWG_Create_LOD(bpy.types.Operator):
	bl_idname = "object.swg_create_lod"
	bl_label = "Create a basic LOD hierachy"
	bl_description = ''''''
 
	def execute(self, context):
		collection = bpy.data.collections.new("NewLODName")
		bpy.context.scene.collection.children.link(collection)

		child = bpy.data.collections.new("LODs")
		collection.children.link(child)

		child = bpy.data.collections.new("Hardpoints")
		collection.children.link(child)

		child = bpy.data.collections.new("Floor")
		collection.children.link(child)

		child = bpy.data.collections.new("Radar/Test/Write")
		collection.children.link(child)

		child = bpy.data.collections.new("Collision")
		collection.children.link(child)

		return {'FINISHED'}
 
	def draw(self, context):
		pass

class SWG_Add_Distance_CP(bpy.types.Operator):
	bl_idname = "object.swg_add_distance_cp"
	bl_label = "Add 'Distance Custom' Property to selection"
	bl_description = '''Add the 'distance' Custom Property to selected meshes'''
 
	def execute(self, context):
		start=50
		offset=50
		objs = sorted(context.selected_objects, key=lambda x: x.name)
		for obj in objs:
			if obj.type == 'MESH':
				obj['distance'] = start
				start += offset

		return {'FINISHED'}
 
	def draw(self, context):
		pass

class SWG_Create_POB(bpy.types.Operator):
	bl_idname = "object.swg_create_pob"
	bl_label = "Create a basic POB hierachy"
	bl_description = ''''''
 
	def execute(self, context):
		collection = bpy.data.collections.new("NewPOBName")
		bpy.context.scene.collection.children.link(collection)
		collection['ship'] = False

		# r0
		r0 = bpy.data.collections.new("r0")
		collection.children.link(r0)
		r0['can_see_parent'] = False

		app = bpy.data.collections.new("Appearance_r0")
		r0.children.link(app)

		child = bpy.data.collections.new("LODs")
		app.children.link(child)

		child = bpy.data.collections.new("Hardpoints")
		app.children.link(child)

		child = bpy.data.collections.new("Radar/Test/Write")
		app.children.link(child)

		child = bpy.data.collections.new("Collision_r0")
		r0.children.link(child)

		child = bpy.data.collections.new("Lights_r0")
		r0.children.link(child)

		child = bpy.data.collections.new("Portals_r0")
		r0.children.link(child)

		
		#r1
		r1 = bpy.data.collections.new("room1")
		collection.children.link(r1)

		child = bpy.data.collections.new("Collision_room1")
		r1.children.link(child)

		child = bpy.data.collections.new("Lights_room1")
		r1.children.link(child)

		child = bpy.data.collections.new("Portals_room1")
		r1.children.link(child)

		child = bpy.data.collections.new("Objects_room1")
		r1.children.link(child)

		return {'FINISHED'}
 
	def draw(self, context):
		pass

class SWG_Create_POB_Room(bpy.types.Operator):
	bl_idname = "object.swg_create_pob_room"
	bl_label = "Add a room to the current POB hierachy"
	bl_description = ''''''
 
	@classmethod
	def poll(self, context):
		collection = bpy.context.view_layer.active_layer_collection.collection
		return collection != None

	def execute(self, context):		
		collection = bpy.context.view_layer.active_layer_collection.collection		
		name=f'room{len(collection.children)}'
		r1 = bpy.data.collections.new(name)
		r1['can_see_parent'] = True
		collection.children.link(r1)
		child = bpy.data.collections.new(f"Collision_{name}")
		r1.children.link(child)
		child = bpy.data.collections.new(f"Lights_{name}")
		r1.children.link(child)
		child = bpy.data.collections.new(f"Portals_{name}")
		r1.children.link(child)
		child = bpy.data.collections.new(f"Objects_{name}")
		r1.children.link(child)
		return {'FINISHED'}
 
	def draw(self, context):
		pass

class SWG_Portals_Passable(bpy.types.Operator):
	bl_idname = "object.swg_portals_passable"
	bl_label = "Mark selected portals as passable"
	bl_description = "Adds the 'passable' Custom Property to all meshes in the selection, with value of True"
 
	def execute(self, context):
		for obj in context.selected_objects:
			if obj.type == 'MESH':
				obj['passable'] = True

		return {'FINISHED'}
 
	def draw(self, context):
		pass

class SWG_Portals_Unpassable(bpy.types.Operator):
	bl_idname = "object.swg_portals_unpassable"
	bl_label = "Mark selected portals as unpassable"
	bl_description = "Adds the 'passable' Custom Property to all meshes in the selection, with value of False"
 
	def execute(self, context):
		for obj in context.selected_objects:
			if obj.type == 'MESH':
				obj['passable'] = False

		return {'FINISHED'}
 
	def draw(self, context):
		pass

class SWG_Create_POB_Light(bpy.types.Operator):
	bl_idname = "object.swg_create_pob_light"
	bl_label = "Add a POB Light to the active collection"
	bl_description = "Add a light with attenuation, specular, and type flag custom properties to the active collection"
 
	@classmethod
	def poll(self, context):
		collection = bpy.context.view_layer.active_layer_collection.collection
		return collection != None

	def execute(self, context):		
		collection = bpy.context.view_layer.active_layer_collection.collection

		if collection.name.startswith("Lights_") == False:
			print(f"ERROR! Invalid collection! Collection should be a POB \"Lights\" collection!")
			return

		# Create light datablock
		light_data = bpy.data.lights.new(name="light-data", type='POINT')
		light_data.energy = 50
		light_data.color = [0.5,0.5,0.5]

		# Add light properties
		light_data['specular_color'] = [0.0,0.0,0.0]
		light_data.id_properties_ui('specular_color').update(
				default=(0, 0, 0), 
				min=0.0, 
				max=1.0, 
				soft_min=0.0, 
				soft_max=1.0, 
				subtype="COLOR"
			)
		
		light_data['constant_attenuation'] = 1.0
		light_data['linear_attenuation'] = 0.0
		light_data['quadratic_attenuation'] = 0.0

		# Create new object, pass the light data 
		light_name = 'Light.' + collection.name
		light_object = bpy.data.objects.new(name=light_name, object_data=light_data)

		# Link object to collection in context
		collection.objects.link(light_object)

		return {'FINISHED'}
 
	def draw(self, context):
		pass

class SWG_Initialize_POB_Interior_Object_Properties(bpy.types.Operator):
	bl_idname = "object.swg_init_pob_obj_props"
	bl_label = "Initialize POB object properties"
	bl_description = "Adds the 'template', 'objvars', 'scripts', 'no_create', and 'location_list' properties to all selected objects"

	def execute(self, context):
		for obj in context.selected_objects:
			obj['template'] = ""
			obj['objvars'] = "$|"
			obj['scripts'] = ""
			obj['no_create'] = 0
			obj['location_list'] = ""
		
		return {'FINISHED'}

	def draw(self, context):
		pass

class SWG_Write_POB_Interior_Buildout(bpy.types.Operator):
	bl_idname = "object.swg_write_pob_interior_buildout"
	bl_label = "Copy active POB Interior buildout to clipboard"
	bl_description = "Write the interior buildout text for the active selected POB collection and copy it to the clipboard"

	@classmethod
	def poll(self, context):
		collection = bpy.context.view_layer.active_layer_collection.collection
		return collection != None
	
	def execute(self, context):		
		collection = bpy.context.view_layer.active_layer_collection.collection
		context.window_manager.clipboard = support.create_interior_buildout(collection)
		return {'FINISHED'}

class SWGMaterialsMenu(bpy.types.Menu):
	bl_label = "Materials"
	bl_idname = "VIEW3D_MT_SWG_materials_menu"

	def draw(self, context):
		layout = self.layout   
		layout.operator(SWG_Load_Materials_Operator.bl_idname, text=SWG_Load_Materials_Operator.bl_label)
		layout.operator(SWG_Add_Material_Operator.bl_idname, text=SWG_Add_Material_Operator.bl_label)

class SWGMshMenu(bpy.types.Menu):
	bl_label = "MSH (static mesh)"
	bl_idname = "VIEW3D_MT_SWG_msh_menu"

	def draw(self, context):
		layout = self.layout   
		layout.operator(SWG_Create_Apt_For_Msh.bl_idname, text=SWG_Create_Apt_For_Msh.bl_label)

class SWGFlrMenu(bpy.types.Menu):
	bl_label = "FLR (floor)"
	bl_idname = "VIEW3D_MT_SWG_flr_menu"

	def draw(self, context):
		layout = self.layout
		#layout.operator(SWG_Load_Flr.bl_idname, text=SWG_Load_Flr.bl_label)
		#layout.operator(SWG_Write_Flr.bl_idname, text=SWG_Write_Flr.bl_label)
		layout.operator(SWG_Visualize_Floor_Pathgraph.bl_idname, text=SWG_Visualize_Floor_Pathgraph.bl_label)
		layout.operator(SWG_Debug_Portal_Edges.bl_idname, text=SWG_Debug_Portal_Edges.bl_label)

class SWGMgnMenu(bpy.types.Menu):
	bl_label = "MGN (animated mesh)"
	bl_idname = "VIEW3D_MT_SWG_mgn_menu"

	def draw(self, context):
		layout = self.layout
		layout.operator(SWG_Create_Sat_For_Mgn.bl_idname, text=SWG_Create_Sat_For_Mgn.bl_label)
		layout.operator(SWG_Swap_Bone_Names_To_Source.bl_idname, text= SWG_Swap_Bone_Names_To_Source.bl_label)
		layout.operator(SWG_Generate_Blends_From_Other.bl_idname, text=SWG_Generate_Blends_From_Other.bl_label)
		layout.operator(SWG_Initialize_MGN_From_Existing.bl_idname, text=SWG_Initialize_MGN_From_Existing.bl_label)

class SWGLodMenu(bpy.types.Menu):
	bl_label = "LOD (level of detail)"
	bl_idname = "VIEW3D_MT_SWG_lod_menu"

	def draw(self, context):
		layout = self.layout
		layout.operator(SWG_Create_LOD.bl_idname, text=SWG_Create_LOD.bl_label)
		layout.operator(SWG_Add_Distance_CP.bl_idname, text=SWG_Add_Distance_CP.bl_label)

class SWGPobMenu(bpy.types.Menu):
	bl_label = "POB (Portalized Object)"
	bl_idname = "VIEW3D_MT_SWG_pob_menu"

	def draw(self, context):
		layout = self.layout
		layout.operator(SWG_Create_POB.bl_idname, text=SWG_Create_POB.bl_label)
		layout.operator(SWG_Create_POB_Room.bl_idname, text=SWG_Create_POB_Room.bl_label)
		layout.operator(SWG_Portals_Passable.bl_idname, text=SWG_Portals_Passable.bl_label)
		layout.operator(SWG_Portals_Unpassable.bl_idname, text=SWG_Portals_Unpassable.bl_label)
		layout.operator(SWG_Create_POB_Light.bl_idname, text=SWG_Create_POB_Light.bl_label)
		layout.operator(SWG_Initialize_POB_Interior_Object_Properties.bl_idname, text=SWG_Initialize_POB_Interior_Object_Properties.bl_label)
		layout.operator(SWG_Write_POB_Interior_Buildout.bl_idname, text=SWG_Write_POB_Interior_Buildout.bl_label)

class SWGMenu(bpy.types.Menu):
	bl_label = "SWG"
	bl_idname = "VIEW3D_MT_SWG_menu"

	def draw(self, context):
		layout = self.layout
		layout.menu(SWGMaterialsMenu.bl_idname)
		layout.menu(SWGMgnMenu.bl_idname)
		layout.menu(SWGMshMenu.bl_idname)
		layout.menu(SWGLodMenu.bl_idname)
		layout.menu(SWGFlrMenu.bl_idname)
		layout.menu(SWGPobMenu.bl_idname)

def draw_item(self, context):
	layout = self.layout
	layout.menu(SWGMenu.bl_idname)

classes = (
	OBJECT_OT_addon_prefs_swg,
	SWGPreferences,
	ImportMSH,
	MSH_PT_import_option,
	ExportMSH,
	MSH_PT_export_option,
	ImportMGN,
	MGN_PT_export_option,
	ExportMGN,  
	MGN_PT_import_option,  
	ImportLOD,
	LOD_PT_import_option,
	ExportLOD,
	LOD_PT_export_option,
	ImportPOB,
	POB_PT_import_option,
	ExportPOB,
	POB_PT_export_option,
	ImportSKT,
	SKT_PT_import_option,
	ExportSKT,
	ExportLMG,
	LMG_PT_export_option,
	ExportSAT,
	SAT_PT_export_option,
	SWG_Load_Materials_Operator,
	SWG_Add_Material_Operator,
	SWG_Create_Apt_For_Msh,
	SWG_Create_Sat_For_Mgn,
	SWG_Load_Skeleton_For_MGN,
	SWG_Initialize_MGN_From_Existing,
	SWG_Swap_Bone_Names_To_Source,
	SWG_Generate_Blends_From_Other,
	SWG_Load_Flr,
	SWG_Write_Flr,
	SWG_Visualize_Floor_Pathgraph,
	SWG_Debug_Portal_Edges,
	SWG_Create_LOD,
	SWG_Add_Distance_CP,
	SWG_Create_POB,
	SWG_Create_POB_Room,
	SWG_Portals_Unpassable,
	SWG_Portals_Passable,
	SWG_Create_POB_Light,
	SWG_Initialize_POB_Interior_Object_Properties,
	SWG_Write_POB_Interior_Buildout,
	SWGMaterialsMenu,
	SWGMgnMenu,
	SWGMshMenu,
	SWGFlrMenu,
	SWGLodMenu,
	SWGPobMenu,
	SWGMenu
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	bpy.types.TOPBAR_MT_file_import.append(import_operators)
	bpy.types.TOPBAR_MT_file_export.append(export_operators)
	bpy.types.VIEW3D_HT_header.append(draw_item)

def unregister():
	bpy.types.TOPBAR_MT_file_import.remove(import_operators)
	bpy.types.TOPBAR_MT_file_export.remove(export_operators)
	bpy.types.VIEW3D_HT_header.remove(draw_item)

	for cls in classes:
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	unregister()
	register()
