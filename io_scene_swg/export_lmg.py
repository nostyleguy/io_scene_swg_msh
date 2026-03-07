import os, bpy
from . import swg_types
from . import export_mgn

def save(context, filepath, *, export_mgns = True, do_tangents = True,):
    collection = bpy.context.view_layer.active_layer_collection.collection
    if collection != None:
        dirname = os.path.dirname(filepath)
        fullpath = os.path.join(dirname, collection.name.split('.')[0] + ".lmg")
        return export_lmg(context, fullpath, collection, export_mgns, do_tangents)
    else:
        return {'CANCELLED'}

def export_lmg(context, filepath, collection, export_mgns = True, do_tangents = True):
    lmg_name = os.path.basename(filepath).replace('.lmg','')
    print(f"LMG Name: {lmg_name}")

    dirname = os.path.dirname(filepath)
    extract_dir = context.preferences.addons[__package__].preferences.swg_root

    skts_col = None
    hardpoints_col = None
    
    mgns = []
    for obj in collection.all_objects:
        if obj.type == 'MESH':
            obj.select_set(True)
            mgns.append(obj.name)
            if export_mgns:
                mgn_filepath = os.path.join(dirname, obj.name + ".mgn")
                export_mgn.export_mgn(mgn_filepath, extract_dir, obj, do_tangents)
            obj.select_set(False)
    if len(mgns) == 0:
        return {'CANCELLED'}

    lmg = swg_types.LmgFile(filepath, mgns)
    lmg.write()
    return {'FINISHED'}