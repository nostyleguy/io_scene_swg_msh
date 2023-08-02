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
    "version": (2, 0, 16),
    "blender": (2, 81, 6),
    "location": "File > Import-Export",
    "description": "Import-Export SWG .msh and .mgn",
    "warning": "",
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
else:
    from . import support
    from . import extents
    from . import swg_types
    from . import nsg_iff
    from . import vertex_buffer_format
    from . import swg_types
    from . import vector3D
    from . import import_msh
    from . import export_msh
    from . import import_mgn
    from . import export_mgn
    from . import import_lod

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

import bpy, os, functools, base64
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty

class SWGPreferences(AddonPreferences):
    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    swg_root: StringProperty(
        name="SWG Client Extract Dir (should contain dirs like 'appearance', 'shader', 'texture', etc.",
        subtype='FILE_PATH',
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "swg_root")

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

@orientation_helper(axis_forward='-Z', axis_up='Y')
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
            default=False,
            )

    files: CollectionProperty(
            type=bpy.types.OperatorFileListElement,
            options={'HIDDEN', 'SKIP_SAVE'},
        )
            
    def execute(self, context):
        #from . import import_msh
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            "files",
                                            "filepath"))

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix

              
        for f in self.files:   
            dirname = os.path.dirname(self.filepath)
            filepath = os.path.join(dirname, f.name)
            

            print(f'IMPORTING: {self.filepath} {filepath}')
            result = import_msh.load_new(context, filepath, **keywords)

        # if 'ERROR' in result:
        #     self.report({'ERROR'}, 'Something went wrong importing MESH')
        #     return {'CANCELLED'}
        
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
        layout.prop(operator, 'remove_duplicate_verts')


@orientation_helper(axis_forward='-Z', axis_up='Y')
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

    global_scale: FloatProperty(
            name="Scale",
            min=0.01, max=1000.0,
            default=1.0,
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
        #from . import export_msh
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
        layout.prop(operator, 'axis_forward')
        layout.prop(operator, 'axis_up')
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

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
                                        
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
    filter_glob: StringProperty(
            default="*.mgn",
            options={'HIDDEN'},
            )

    do_tangents : BoolProperty(name='DOT3', description="Include DOT3 tangent vectors.", default=True) 
    
    def execute(self, context):
        from . import export_mgn

        keywords = self.as_keywords(ignore=("check_existing","filter_glob"))
        print(f"Keyword args: {str(keywords)}")
        result = export_mgn.export_mgn(context, **keywords)
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

@orientation_helper(axis_forward='-Z', axis_up='Y')
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
            description="SWG seems to interprte the DDS vertical axis opposite as Blender does. Need to flip UVs on import AND export to be able to use Blender UV mapping without being destructive.",
            default=True,
            )
    remove_duplicate_verts: BoolProperty(
            name="Remove Duplicate Verts",
            description="Attempt to remove verts that are probably duplicates (within 0.0001 units of each other)",
            default=False,
            )

    files: CollectionProperty(
            type=bpy.types.OperatorFileListElement,
            options={'HIDDEN', 'SKIP_SAVE'},
        )
            
    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            "files",
                                            "filepath"))

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix

              
        for f in self.files:   
            dirname = os.path.dirname(self.filepath)
            filepath = os.path.join(dirname, f.name) 

            print(f'IMPORTING: {self.filepath} {filepath}')    
            result = import_lod.load_new(context, filepath, **keywords)
            if 'ERROR' in result:
                self.report({'ERROR'}, 'Something went wrong importing LOD')
                return {'CANCELLED'}
        
        return {'FINISHED'}

    def draw(self, context):
        pass

def import_operators(self, context):
    self.layout.operator(ImportMGN.bl_idname, text="SWG Animated Mesh (.mgn)")
    self.layout.operator(ImportMSH.bl_idname, text="SWG Static Mesh (.msh)")
    #self.layout.operator(ImportLOD.bl_idname, text="SWG Static Level of Detail (.lod)")

def export_operators(self, context):
    self.layout.operator(ExportMGN.bl_idname, text="SWG Animated Mesh (.mgn)")
    self.layout.operator(ExportMSH.bl_idname, text="SWG Static Mesh (.msh)")

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
        s=context.preferences.addons[__package__].preferences.swg_root
        print(f"invoke with: {context.active_object.name}")     
        for slot in context.active_object.material_slots:
            mat = slot.material    
            path=f'shader/{mat.name}.sht'        
            real_shader_path = support.find_file(path,s)
            if real_shader_path:
                shader = swg_types.SWGShader(real_shader_path)
                support.configure_material_from_swg_shader(mat,shader, s)
            else:
                print(f"WARNING: Couldn't locate real shader path for: {path}")

        return {'FINISHED'}

class SWG_Add_Material_Operator(bpy.types.Operator):
    bl_idname = "object.swg_add_material"
    bl_label = "Add SWG Shader as Material"
    bl_description = '''If this option is disabled, you need to set the "SWG Client Extract Dir" property in the add-on preferences, and have 1 object selected'''
 

    filename_ext = ".sht"
    filter_glob : StringProperty(
        default="*.sht",
        options={'HIDDEN'},
        )
    filepath: StringProperty(default="*.sht",subtype='FILE_PATH')

    
    @classmethod
    def poll(cls, context):
        return context.active_object != None and (context.preferences.addons[__package__].preferences.swg_root != "")

    def execute(self, context):
        s=context.preferences.addons[__package__].preferences.swg_root
        context.active_object.data.materials.append(None)
        shader = swg_types.SWGShader(support.clean_path(self.properties.filepath))
        material = bpy.data.materials.new(shader.stripped_shader_name()) 
        context.active_object.material_slots[len(context.active_object.material_slots)-1].material = material
        support.configure_material_from_swg_shader(material, shader, s)
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
    filter_glob : StringProperty(
        default="*.apt",
        options={'HIDDEN'},
        )
    filepath: StringProperty(default="test.apt",subtype='FILE_PATH')

    @classmethod
    def poll(cls, context):
        return context.active_object != None


    def execute(self, context): 

        apt_path =  self.properties.filepath 
        apt_reference = (functools.reduce(os.path.join,["mesh", context.active_object.name]) + ".msh").lower()
        print(f"Writing apt: {apt_path} For mesh: {apt_reference}")
        apt = swg_types.AptFile(apt_path, apt_reference)
        apt.write()
        return {'FINISHED'}

    def invoke(self, context, event):
        default_filename=context.active_object.name.lower()+".apt"
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
    filter_glob : StringProperty(
        default="*.sat",
        options={'HIDDEN'},
        )
    filepath: StringProperty(default="test.sat",subtype='FILE_PATH')

    num_lods: IntProperty(
            name="Number LODs",
            min=1, max=10,
            default=1,
            )
    @classmethod
    def poll(cls, context):
        return context.active_object != None


    def execute(self, context): 

        sat_path =  self.properties.filepath 

        lmg_path = os.path.dirname(sat_path)+"/mesh/"+ context.active_object.name.lower()+".lmg"
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
    filter_glob : StringProperty(
        default="*.skt",
        options={'HIDDEN'},
        )
    filepath: StringProperty(default="test.skt",subtype='FILE_PATH')

    @classmethod
    def poll(cls, context):
        return context.active_object != None

    def execute(self, context): 
        skt_path =  self.properties.filepath
        skt = swg_types.SktFile(skt_path)
        skt.load()
        print(f"SKT: {skt}")

        for bone in skt.bones:
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
    filter_glob : StringProperty(
        default="*.mgn",
        options={'HIDDEN'},
        )
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

        for bone in mgn.bone_names:
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
        # default_filename=context.active_object.name.lower()+".skt"
        # self.filepath = default_filename        
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
 

    # filename_ext = ".mgn"
    # filter_glob : StringProperty(
    #     default="*.mgn",
    #     options={'HIDDEN'},
    #     )
    # filepath: StringProperty(default="test.mgn",subtype='FILE_PATH')

    @classmethod
    def poll(cls, context):
        return context.active_object != None

    # def execute(self, context): 
    #     mgn_path =  self.properties.filepath
    #     mgn = swg_types.SWGMgn(mgn_path,context.preferences.addons[__package__].preferences.swg_root)
    #     mgn.load()
    #     scene_object = context.active_object
    #     print(f"mgn: {mgn}")

    #     for bone in mgn.bone_names:
    #         vg = scene_object.vertex_groups.new(name=bone)

    #     scene_object.shape_key_add(name='Basis')
    #     for i, blend in enumerate(mgn.blends):
    #         sk = scene_object.shape_key_add(name=blend.name)
        
    #     for i, skel in enumerate(mgn.skeletons):
    #         scene_object[f'SKTM_{i}'] = skel

    #     for zone in mgn.occlusions:
    #         scene_object["OZN_"+zone[0]] = zone[2]

    #     scene_object[f'OCC_LAYER'] = mgn.occlusion_layer

    #     if mgn.binary_hardpoints:
    #         scene_object["HPTS"] = base64.b64encode(mgn.binary_hardpoints).decode('ASCII')

    #     if mgn.binary_trts:
    #         scene_object["TRTS"] = base64.b64encode(mgn.binary_trts).decode('ASCII')

    #     if mgn.occlusion_zones:
    #         for i, ozc in enumerate(mgn.occlusion_zones):
    #             face_map = scene_object.face_maps.new(name=ozc[0])
    #             face_map.add(ozc[1])

    #     return {'FINISHED'}

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
            "rarm":"ValveBiped.Bip01_R_UpperArm",
            "rforearm":"ValveBiped.Bip01_R_Forearm",
            "rulna":"ValveBiped.Bip01_R_Ulna",
            "rwrist":"ValveBiped.Bip01_R_Hand",
            "rthigh":"ValveBiped.Bip01_R_Thigh",
            "rshin":"ValveBiped.Bip01_R_Calf",
            "rankle":"ValveBiped.Bip01_R_Foot",
            "rclav":"ValveBiped.Bip01_R_Clavicle",
            "rtoe":"ValveBiped.Bip01_R_Toe0",
        }
        
        scene_object = context.active_object
        print(f"Swapping bones on: {scene_object.name}")
        for vg in scene_object.vertex_groups:
            if vg.name in swg_to_source_map:
                vg.name = swg_to_source_map[vg.name]

        return {'FINISHED'}
 
    def draw(self, context):
        pass

class SWGMenu(bpy.types.Menu):
    bl_label = "SWG"
    bl_idname = "VIEW3D_MT_SWG_menu"

    def draw(self, context):
        layout = self.layout        
        layout.operator(SWG_Initialize_MGN_From_Existing.bl_idname, text=SWG_Initialize_MGN_From_Existing.bl_label)    
        layout.operator(SWG_Load_Materials_Operator.bl_idname, text=SWG_Load_Materials_Operator.bl_label)
        layout.operator(SWG_Add_Material_Operator.bl_idname, text=SWG_Add_Material_Operator.bl_label)
        layout.operator(SWG_Create_Apt_For_Msh.bl_idname, text=SWG_Create_Apt_For_Msh.bl_label)
        layout.operator(SWG_Create_Sat_For_Mgn.bl_idname, text=SWG_Create_Sat_For_Mgn.bl_label)
        layout.operator(SWG_Swap_Bone_Names_To_Source.bl_idname, text= SWG_Swap_Bone_Names_To_Source.bl_label)

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
    ImportLOD,  
    MGN_PT_import_option,
    SWG_Load_Materials_Operator,
    SWG_Add_Material_Operator,
    SWG_Create_Apt_For_Msh,
    SWG_Create_Sat_For_Mgn,
    SWG_Load_Skeleton_For_MGN,
    SWG_Initialize_MGN_From_Existing,
    SWG_Swap_Bone_Names_To_Source,
    SWGMenu,
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
