import bpy, os, math, time, datetime
from . import nsg_iff
from bpy.props import *
from mathutils import Vector, Quaternion, Matrix

def save(context, filepath,):
    # tracks = bpy.data.objects['Cube'].animation_data.nla_tracks
    # for track in tracks:
    #     for strip in track.strips:
    #         print(strip.action)
    #         action=strip.action

    #         for fcu in action.fcurves:
    #             print(fcu.data_path + " channel " + str(fcu.array_index))
    #             for keyframe in fcu.keyframe_points:
    #                 print(keyframe.co) #coordinates x,y

    collection = bpy.context.view_layer.active_layer_collection.collection
    if collection != None:
        dirname = os.path.dirname(filepath)
        fullpath = os.path.join(dirname, collection.name.split(".")[0]+".ans")
        return export_ans(context, fullpath)
    else:
        return {'CANCELLED'}

def create_kfat(iff: nsg_iff.IFF, action: bpy.types.Action):
    iff.insertForm("KFAT")
    iff.insertForm("0003")

    iff.insertChunk("INFO")
    iff.insertFloat(30.0)   # FPS
    iff.insert_int32(0) # Frame Count - 1
    iff.insert_int32(0) # Transform Info Count
    iff.insert_int32(0) # Rotation Channel Count
    iff.insert_int32(0) # Static Rotation Count
    iff.insert_int32(0) # Translation Channel Count
    iff.insert_int32(0) # Static Translation Count
    iff.exitChunk("INFO")

    # Transform Info
    iff.insertForm("XFRM")
    for i in range(1):
        iff.insertChunk("XFIN")
        iff.insertChunkString("") # Joint Name
        iff.insert_int8(1) # Has Animated Rotations
        iff.insert_int32(0) # Rotation Channel Index
        iff.insert_uint32(0) # Translation Mask
        iff.insert_int32(0) # X Translation Channel Index
        iff.insert_int32(0) # Y Translation Channel Index
        iff.insert_int32(0) # Z Translation Channel Index
        iff.exitChunk("XFIN")
    iff.exitForm("XFRM")

    # Animation Rotation Channels
    iff.insertForm("AROT")
    for i in range(1):
        iff.insertChunk("QCHN")
        iff.insert_int32(1) # Keyframe Count
        for k in range(1):
            iff.insertFloat(0) # Keyframe
            iff.insertFloatVector4([1.0, 0.0, 0.0, 0.0])
        iff.exitChunk("QCHN")
    iff.exitForm("AROT")

    # Static Rotation Data
    iff.insertChunk("SROT")
    for i in range(1):
        iff.insertFloatVector4([1.0, 0.0, 0.0, 0.0])
    iff.exitChunk("SROT")
    
    # Animated Translation Channels
    iff.insertForm("ATRN")
    for i in range(1):
        iff.insertChunk("CHNL")
        iff.insert_int32(1) # Keyframe Count
        for k in range(1):
            iff.insert_int32(0) # Keyframe
            iff.insertFloat(0) # Value
        iff.exitChunk("CHNL")
    iff.exitForm("ATRN")

    # Static Translation Data
    iff.insertChunk("STRN")
    for i in range(1):
        iff.insertFloat(0)
    iff.exitChunk("STRN")

    # Animation Messages
    iff.insertForm("MSGS")
    iff.insertChunk("INFO")
    iff.insert_int16(0) # Message Count
    iff.exitChunk("INFO")
    for i in range(1):
        iff.insertChunk("MESG")
        iff.insert_int16(1) # Signal Count
        iff.insertChunkString("") # Signal Name
        for s in range(1):
            iff.insert_int16(0) # Trigger Frame
        iff.exitChunk("MESG")
    iff.exitForm("MSGS")

    # Locomotion Translation Data
    iff.insertChunk("LOCT")
    iff.insertFloat(0.0) # Average Speed
    iff.insert_int16(1) # Keyframe Count
    for i in range(1):
        iff.insert_int16(0) # Keyframe
        iff.insertFloatVector3([0.0, 0.0, 0.0]) # Translation
    iff.exitChunk("LOCT")

    # Locomotion Rotation Data
    iff.insertChunk("LOCR")
    iff.insert_int16(1) # Keyframe Count
    for i in range(1):
        iff.insert_int16(0) # Frame
        iff.insertFloatVector4([1.0, 0.0, 0.0, 0.0])
    iff.exitChunk("LOCR")

    iff.exitForm("0003")
    iff.exitForm("KFAT")

    return iff

def create_ckat(iff: nsg_iff.IFF, action: bpy.types.Action):
    iff.insertForm("CKAT")
    iff.insertForm("0001")

    iff.insertChunk("INFO")
    iff.insertFloat(30.0)   # FPS
    iff.insert_int16(0) # Frame Count - 1
    iff.insert_int16(0) # Transform Info Count
    iff.insert_int16(0) # Rotation Channel Count
    iff.insert_int16(0) # Static Rotation Count
    iff.insert_int16(0) # Translation Channel Count
    iff.insert_int16(0) # Static Translation Count
    iff.exitChunk("INFO")

    # Transform Info
    iff.insertForm("XFRM")
    for i in range(1):
        iff.insertChunk("XFIN")
        iff.insertChunkString("") # Joint Name
        iff.insert_int8(1) # Has Animated Rotations
        iff.insert_int16(0) # Rotation Channel Index
        iff.insert_uint8(0) # Translation Mask
        iff.insert_int16(0) # X Translation Channel Index
        iff.insert_int16(0) # Y Translation Channel Index
        iff.insert_int16(0) # Z Translation Channel Index
        iff.exitChunk("XFIN")
    iff.exitForm("XFRM")

    # Animation Rotation Channels
    iff.insertForm("AROT")
    for i in range(1):
        iff.insertChunk("QCHN")
        iff.insert_int32(1) # Keyframe Count
        iff.insert_int8(0) # Compression Format X
        iff.insert_int8(0) # Compression Format Y
        iff.insert_int8(0) # Compression Format Z
        for k in range(1):
            iff.insert_int16(0) # Keyframe
            iff.insert_int32(0) # Compressed Quaternion Rotation
        iff.exitChunk("QCHN")
    iff.exitForm("AROT")

    # Static Rotation Data
    iff.insertChunk("SROT")
    for i in range(1):
        iff.insert_int8(0) # Compression Format X
        iff.insert_int8(0) # Compression Format Y
        iff.insert_int8(0) # Compression Format Z
        iff.insert_int32(0) # Compressed Quaternion Rotation
    iff.exitChunk("SROT")
    
    # Animated Translation Channels
    iff.insertForm("ATRN")
    for i in range(1):
        iff.insertChunk("CHNL")
        iff.insert_int16(1) # Keyframe Count
        for k in range(1):
            iff.insert_int16(0) # Keyframe
            iff.insertFloat(0) # Value
        iff.exitChunk("CHNL")
    iff.exitForm("ATRN")

    # Static Translation Data
    iff.insertChunk("STRN")
    for i in range(1):
        iff.insertFloat(0)
    iff.exitChunk("STRN")

    # Animation Messages
    iff.insertForm("MSGS")
    iff.insertChunk("INFO")
    iff.insert_int16(0) # Message Count
    iff.exitChunk("INFO")
    for i in range(1):
        iff.insertChunk("MESG")
        iff.insert_int16(1) # Signal Count
        iff.insertChunkString("") # Signal Name
        for s in range(1):
            iff.insert_int16(0) # Trigger Frame
        iff.exitChunk("MESG")
    iff.exitForm("MSGS")

    # Locomotion Translation Data
    iff.insertChunk("LOCT")
    iff.insertFloat(0.0) # Average Speed
    iff.insert_int16(1) # Keyframe Count
    for i in range(1):
        iff.insert_int16(0) # Keyframe
        iff.insertFloatVector3([0.0, 0.0, 0.0]) # Translation
    iff.exitChunk("LOCT")

    # Locomotion Rotation Data
    iff.insertChunk("QCHN")
    iff.insert_int16(1) # Keyframe Count
    iff.insert_int8(0) # Compression Format X
    iff.insert_int8(0) # Compression Format Y
    iff.insert_int8(0) # Compression Format Z
    for i in range(1):
        iff.insert_int16(0) # Frame
        iff.insert_int32(0) # Compressed Quaternion Rotation
    iff.exitChunk("QCHN")

    iff.exitForm("0001")
    iff.exitForm("CKAT")

    return iff

def export_ans(context, filepath, action: bpy.types.Action):
    starttime = time.time()

    iff = nsg_iff.IFF(initial_size=512000)
    
    ans_type = action.name.split(".")[-1].upper()
    match ans_type:
        case "KFAT": iff = create_kfat(iff, action)
        case "CKAT": iff = create_ckat(iff, action)
        case _: iff = create_kfat(iff, action) # default KFAT

    iff.write(filepath)

    now = time.time()
    print(f"Successfully wrote: {filepath} Duration: " + str(datetime.timedelta(seconds=(now-starttime))))
    return {'FINISHED'}