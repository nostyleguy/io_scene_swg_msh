# SKT Import / Export
#
# Authors:
# Tim "RhapsodyInGeek" Maccabe (https://github.com/RhapsodyInGeek)
# Vera "sinewavey" Lux (https://github.com/sinewavey)
# Nick "NoStyleGuy" Rafalski (https://github.com/nostyleguy)
# (c) 2025
#
# In order to export, make sure a collection with armatures is active. 
# No child armatures will be exported.
# Each armature in the collection is exported as an SKTM (LOD skeleton) packaged in the same SKT file.
# SKTMs are added in view layer descending order, allowing for multiple SKT LODs.

import bpy, os, math, time, datetime
from . import nsg_iff
from bpy.props import *
from mathutils import Vector, Quaternion, Matrix

def save(context, filepath,):
    collection = bpy.context.view_layer.active_layer_collection.collection
    if collection != None:
        dirname = os.path.dirname(filepath)
        fullpath = os.path.join(dirname, collection.name.split(".")[0]+".skt")
        return export_skt(context, fullpath, collection)
    else:
        return {'CANCELLED'}

def swg_quat_to_blender_quat(r):
    q = Quaternion((-r[0], -r[1], r[2], r[3]))
    return q

def export_skt(context, filepath, collection):
    starttime = time.time()
    
    skt_name = os.path.basename(filepath).replace('.skt','')
    print(f"Creating SKT: {skt_name}")
    arm_objs = []

    for obj in collection.all_objects:
        # Skip nested objects. We only want ones directly under the collection.
        if obj.parent:
            continue
        if obj.type == 'ARMATURE':
            arm_objs.append(obj)
    
    if len(arm_objs) == 0:
        return {'CANCELLED'}

    iff = nsg_iff.IFF(initial_size=512000)
    iff.insertForm("SLOD")
    iff.insertForm("0000")

    # Skeleton LOD count
    iff.insertChunk("INFO")
    iff.insert_int16(len(arm_objs))
    iff.exitChunk("INFO")

    for arm in arm_objs:
        print(f"Exporting {arm.name}...")

        arm.select_set(True)
        context.view_layer.objects.active = arm
        arm.rotation_euler = (math.pi * -0.5, 0.0, 0.0)
        bpy.ops.object.transform_apply(rotation=True)

        iff.insertForm("SKTM")
        iff.insertForm("0002")

        bones = []
        bone_translations_org = []
        bone_translations_out = []
        for b in arm.data.bones:
            # Allow the use of control bones like IK
            if b.use_deform:
                bones.append(b)
                t = b.head_local
                if b.parent:
                    t = t - b.parent.head_local
                print(f"{b.name} position: {t}")
                bone_translations_org.append(t)
                bone_translations_out.append(t)
        bone_ct = len(bones)
        
        # Joint Count
        iff.insertChunk("INFO")
        iff.insert_int32(bone_ct)
        iff.exitChunk("INFO")

        # Joint Names
        iff.insertChunk("NAME")
        for b in bones:
            iff.insertChunkString(b.name)
        iff.exitChunk("NAME")
        
        # Joint Parents
        bone_parent_indices = []
        iff.insertChunk("PRNT")
        for b in bones:
            if b.parent:
                for i in range(bone_ct):
                    if b.parent == bones[i]:
                        iff.insert_int32(i)
                        bone_parent_indices.append(i)
                        break
            else:
                bone_parent_indices.append(-1)
                iff.insert_int32(-1)
        iff.exitChunk("PRNT")
        
        identity_quaternion = [1.0, 0.0, 0.0, 0.0] # wxyz is read by SIE as zwxy
        
        # Pre Multiply Rotations
        iff.insertChunk("RPRE")
        for b in bones:
            if "RPRE" in b:
                iff.insertFloatVector4(b["RPRE"])
            else:
                iff.insertFloatVector4(identity_quaternion)
        iff.exitChunk("RPRE")
        
        # Post Multiply Rotations
        iff.insertChunk("RPST")
        for b in bones:
            if "RPST" in b:
                iff.insertFloatVector4(b["RPST"])
            else:
                iff.insertFloatVector4(identity_quaternion)
        iff.exitChunk("RPST")
        
        # Bind Pose Translations
        def process_bone_hierarchy(bone_index, parent_transform=Matrix.Identity(4)):
            if bone_index < 0 or bone_index >= bone_ct:
                return
                
            bone = bones[bone_index]

            rpre = swg_quat_to_blender_quat(bone["RPRE"]) if "RPRE" in b else Quaternion((-1.0, 0.0, 0.0, 0.0))
            rbind = swg_quat_to_blender_quat(bone["BPRO"]) if "BPRO" in b else Quaternion((-1.0, 0.0, 0.0, 0.0))
            rpost = swg_quat_to_blender_quat(bone["RPST"]) if "RPST" in b else Quaternion((-1.0, 0.0, 0.0, 0.0))
            
            # Local transform
            local_translation = bone_translations_org[bone_index]
            rotation_matrix = (rpost @ rbind @ rpre).to_matrix().transposed().to_4x4()
            local_transform = Matrix.Translation(local_translation) @ rotation_matrix

            # Recombine with parent transform
            world_transform = parent_transform @ local_transform

            bone_translations_out[bone_index] = world_transform.translation - parent_transform.translation
            if arm == arm_objs[0]:
                print(f"{bone.name}: \n\tRPRE {rpre}\n\tBPRO {rbind}\n\tRPST {rpost}\n\tBPTR {bone_translations_out[bone_index]}")

            # Transform children
            for i in range(bone_ct):
                if bone_parent_indices[i] == bone_index:
                    process_bone_hierarchy(i, world_transform)
        
        iff.insertChunk("BPTR")
        for i in range(bone_ct):
            if bone_parent_indices[i] < 0:
                process_bone_hierarchy(i)
        for t in bone_translations_out:
            iff.insertFloatVector3([-t.x, t.y, t.z])
        iff.exitChunk("BPTR")

        # Bind Pose Rotations
        iff.insertChunk("BPRO")
        for b in bones:
            if "BPRO" in b:
                iff.insertFloatVector4(b["BPRO"])
            else:
                iff.insertFloatVector4(identity_quaternion)
        iff.exitChunk("BPRO")
        
        # Joint Rotation Order
        iff.insertChunk("JROR")
        for i in range(bone_ct):
            iff.insert_int32(0)
        iff.exitChunk("JROR")

        iff.exitForm("0002")
        iff.exitForm("SKTM")

        context.view_layer.objects.active = arm
        arm.rotation_euler = (math.pi * 0.5, 0.0, 0.0)
        bpy.ops.object.transform_apply(rotation=True)
        arm.select_set(False)
        print(f"{arm.name} export complete\n")
    
    iff.exitForm("0000")
    iff.exitForm("SLOD")

    iff.write(filepath)

    now = time.time()
    print(f"Successfully wrote: {filepath} Duration: " + str(datetime.timedelta(seconds=(now-starttime))))
    return {'FINISHED'}
