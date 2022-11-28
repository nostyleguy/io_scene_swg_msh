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
    "name": "SWG Mesh (.msh) Import/Export",
    "author": "Nick Rafalski",
    "version": (1, 0, 2),
    "blender": (2, 81, 6),
    "location": "File > Import-Export",
    "description": "Import-Export SWG .msh",
    "warning": "",
    "doc_url": "None",
    "support": 'COMMUNITY',
    "category": "Import-Export",
}

if "bpy" in locals():
        import importlib
        importlib.reload(import_msh)
        importlib.reload(export_msh)
else:
        from . import import_msh
        from . import export_msh


import bpy
from bpy.props import (
        BoolProperty,
        FloatProperty,
        StringProperty,
        EnumProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        orientation_helper,
        path_reference_mode,
        axis_conversion,
        )


@orientation_helper(axis_forward='Z', axis_up='Y')
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

    def execute(self, context):
        from . import import_msh        

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            ))

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix

        # if bpy.data.is_saved and context.preferences.filepaths.use_relative_paths:
        #     import os
        #     keywords["relpath"] = os.path.dirname(bpy.data.filepath)

        result = import_msh.load_new(context, **keywords)
        if 'ERROR' in result:
                self.report({'ERROR'}, 'Something went wrong importing MESH')
                return {'CANCELLED'}
        
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

        layout.prop(operator, "axis_forward")
        layout.prop(operator, "axis_up")
        layout.prop(operator, 'flip_uv_vertical')


@orientation_helper(axis_forward='Z', axis_up='Y')
class ExportMSH(bpy.types.Operator, ExportHelper):
    """Save a SWG .msh File"""

    bl_idname = "export_scene.msh"
    bl_label = 'Export Msh'
    bl_options = {'PRESET'}

    filename_ext = ".msh"
    filter_glob: StringProperty(
            default="*.msh",
            options={'HIDDEN'},
            )

    # context group
    use_selection: BoolProperty(
            name="Selection Only",
            description="Export selected objects only",
            default=False,
            )

    global_scale: FloatProperty(
            name="Scale",
            min=0.01, max=1000.0,
            default=1.0,
            )

    #path_mode: path_reference_mode

    flip_uv_vertical: BoolProperty(
            name="Flip UV Vertically",
            description="SWG seems to flip DDS vertical axis, but blender doesn't. Need to flip UVs on import and export to be able to use Blender UV mapping without being destructive",
            default=True,
            )

    def execute(self, context):
        from . import export_msh
        from mathutils import Matrix
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "global_scale",
                                            "filter_glob",
                                            "check_existing"
                                            ))

        global_matrix = (Matrix.Scale(self.global_scale, 4) @
                         axis_conversion(to_forward=self.axis_forward,
                                         to_up=self.axis_up,
                                         ).to_4x4())

        keywords["global_matrix"] = global_matrix
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

        layout.prop(operator, 'global_scale')
        #layout.prop(operator, 'path_mode')
        layout.prop(operator, 'axis_forward')
        layout.prop(operator, 'axis_up')
        layout.prop(operator, 'use_selection')
        layout.prop(operator, 'flip_uv_vertical')

def menu_func_import(self, context):
    self.layout.operator(ImportMSH.bl_idname, text="SWG Static Mesh (.msh)")

def menu_func_export(self, context):
    self.layout.operator(ExportMSH.bl_idname, text="SWG Static Mesh (.msh)")

classes = (
    ImportMSH,
    MSH_PT_import_option,
    ExportMSH,
    MSH_PT_export_option
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
