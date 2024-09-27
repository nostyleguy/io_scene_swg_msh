import os, bpy, math, mathutils
import numpy as np
from bpy_extras.image_utils import load_image
from bpy_extras import node_shader_utils
from bpy_extras.io_utils import axis_conversion
from mathutils import Vector, Matrix
import bmesh

from . import extents
from . import swg_types

def getChildren(myObject): 
    children = [] 
    for ob in bpy.data.objects: 
        if ob.parent == myObject: 
            children.append(ob) 
    return children
    
def clean_path(path):
    return path.replace('\\', '/') if (os.sep == '/') else path.replace('/', '\\')

def find_file(relative_path, root):
    root=clean_path(root)
    relative_path=clean_path(relative_path)
    if os.path.exists(os.path.join(root, relative_path)):
        #print(f"Found {relative_path}! Returning: {os.path.join(root,relative_path)}")
        return os.path.join(root,relative_path)
    else:
        #print(f"{os.path.join(root,relative_path)} doesn't exist!")
        return None

def load_shared_image(path, root):   
    abs_path = find_file(path, root)
    if not abs_path:
        print (f"Error! Couldn't find image: {path}")
        return None

    png_path = abs_path.replace(".dds",".png")
    image = None
    if abs_path:
        shortname = os.path.basename(png_path)
        for img in bpy.data.images: 
            if shortname == img.name:
                image = img
                print(f"Found image: shortname at {abs_path}. Already is: {img.name}. Has data? {img.has_data}")
                break
    if image == None:
        temp = load_image(abs_path, ".") 
        temp.file_format = "PNG"  
        temp.save_render(png_path)
        image = load_image(png_path, ".")
        # dds_path = png_path.replace(".png", "-converted.dds")
        # image.file_format= "DDS"
        # image.save_render(dds_path)
        bpy.data.images.remove(temp)
    return image

def configure_material_from_swg_shader(material, shader, root_dir):
    ma_wrap = node_shader_utils.PrincipledBSDFWrapper(material, is_readonly=False)
    ma_wrap.use_nodes = True
    main_image = None

    node_tree = material.node_tree

    for node in node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED': 
            if node.inputs['Alpha'].is_linked:
                image_node =  node.inputs['Alpha'].links[0].from_node
                #print(f"Removing Alpha: {image_node.name}")
                node_tree.nodes.remove(image_node)                
            if node.inputs['Base Color'].is_linked:
                image_node =  node.inputs['Base Color'].links[0].from_node
                #print(f"Removing Base: {image_node.name}")
                node_tree.nodes.remove(image_node)              
            if node.inputs['Roughness'].is_linked:
                image_node =  node.inputs['Roughness'].links[0].from_node
                #print(f"Removing Roughness: {image_node.name}")
                node_tree.nodes.remove(image_node)            
            if node.inputs['Specular'].is_linked:
                image_node =  node.inputs['Specular'].links[0].from_node
                #print(f"Removing Specular: {image_node.name}")
                node_tree.nodes.remove(image_node)

    if shader.effect:
        material["Effect"] = shader.effect
        
    if shader.main:
        main_image = load_shared_image(shader.main, root_dir)
        if main_image:
            ma_wrap.base_color_texture.image = main_image
            ma_wrap.base_color_texture.texcoords = 'UV'  
            #ma_wrap.roughness_texture.image = main_image
            #ma_wrap.specular_texture.image = main_image

    if shader.transparent:
        material.blend_method = "BLEND"  
        if main_image:
            ma_wrap.alpha_texture.image = main_image
            ma_wrap.alpha_texture.texcoords = 'UV' 
        else:
            ma_wrap.alpha = 0.1
    else:
        material.blend_method = "OPAQUE"
        ma_wrap.alpha = 1

    if shader.normal:
        normal_image = load_shared_image(shader.normal, root_dir)
        if normal_image:
            ma_wrap.roughness_texture.image = normal_image

    if shader.spec:
        spec_image = load_shared_image(shader.spec, root_dir)
        if spec_image:
            ma_wrap.specular_texture.image = spec_image

def add_sphere(collection, collision, broadphase):
    sph = bpy.data.objects.new(name="Sphere", object_data=None)        
    sph.empty_display_type = "SPHERE"
    sph.location = Vector(convert_vector3([collision.center[0], collision.center[1], collision.center[2]]))
    sph.empty_display_size = 1
    sph.scale = Vector(convert_scale([collision.radius, collision.radius, collision.radius]))
    collection.objects.link(sph)    

    if broadphase:
        sph['broadphase'] = 1

def add_box(collection, collision, broadphase):
    box = bpy.data.objects.new(name="Box", object_data=None)        
    box.empty_display_type = "CUBE"
    location = collision.getCenter()
    box.location = Vector(convert_vector3([location[0], location[1], location[2]]))
    scale = Vector(convert_scale(collision.getSize()))
    #scale = Vector([abs(scale.x), abs(scale.y), abs(scale.z)])
    print(f"adding box: loc: {box.location} scale: {collision.getSize()} (converted: {scale}")
    box.scale = scale
    box.color = [0,0,1,1]
    collection.objects.link(box)

    if broadphase:
        box['broadphase'] = 1

def add_cylinder(collection, collision, broadphase):
    location = collision.base
    bpy.ops.mesh.primitive_cylinder_add(
        radius = 1, 
        depth = 1,
        location = Vector(convert_vector3([location[0], location[1] + (collision.height / 2.0), location[2]])))
    cyln = bpy.context.active_object
    cyln.name = "Cyln"
    cyln.scale = Vector(convert_scale([collision.radius, collision.height, collision.radius]))
    collection.objects.link(cyln)

    try:
       bpy.context.scene.collection.objects.unlink(cyln)
    except:
        pass

    if broadphase:
       cyln['broadphase'] = 1

def add_mesh(collection, collision, broadphase):
    mesh = bpy.data.meshes.new(name='Cmesh-mesh')
    obj = bpy.data.objects.new("CMesh", mesh)
    collection.objects.link(obj)        
    mesh.from_pydata([ convert_vector3([v[0], v[1], v[2]]) for v in collision.verts], [], [[v[2],v[1],v[0]] for v in collision.triangles])
    mesh.update()
    mesh.validate()   

    if broadphase:
        obj['broadphase'] = 1

def add_rtw_mesh(collection, idtl, name):
    mesh = bpy.data.meshes.new(name=f'{name}-mesh')
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)        
    mesh.from_pydata([ convert_vector3([v[0], v[1], v[2]]) for v in idtl.verts], [], [[v[2],v[1],v[0]] for v in idtl.indexes])
    mesh.update()
    mesh.validate()

def obj_to_idtl(obj):
    # Transform per export matrix..
    mesh = obj.to_mesh()    
    # Triangulate
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    
    idtl = swg_types.IndexedTriangleList()
    idtl.verts = [ convert_vector3([v.co[0], v.co[1], v.co[2]]) for v in mesh.vertices]
    idtl.indexes = [ [t.vertices[2],t.vertices[1],t.vertices[0]] for t in mesh.polygons]
    return idtl

def add_component(collection, collision, broadphase):
    return add_collision_to_collection(collection, collision.extent, broadphase)


def add_composite(collection, collision, broadphase):
    for e in collision.extents:
        add_collision_to_collection(collection, e, broadphase)


def add_detail(collection, collision, broadphase):
    add_collision_to_collection(collection, collision.broad_extent, True)
    add_collision_to_collection(collection, collision.extents, False)

def add_collision_to_collection(collection, collision, broadphase = False):

    if isinstance(collision, extents.SphereExtents):
        add_sphere(collection, collision, broadphase)
    elif isinstance(collision, extents.BoxExtents):
        add_box(collection, collision, broadphase)
    elif isinstance(collision, extents.CylinderExtent):
        add_cylinder(collection, collision, broadphase)
    elif isinstance(collision, extents.MeshExtent):
        add_mesh(collection, collision, broadphase)
    elif isinstance(collision, extents.CompositeExtent):
        add_composite(collection, collision, broadphase)
    elif isinstance(collision, extents.ComponentExtent):
        add_component(collection, collision, broadphase)
    elif isinstance(collision, extents.DetailExtent):
        add_detail(collection, collision, broadphase)

def create_extent_for_obj(obj):
    if obj.type == 'MESH' and obj.name.lower().startswith("cyln"):
        converted_location = Vector(convert_vector3(obj.location))
        converted_scale = Vector(convert_scale(obj.scale))   
        radius = converted_scale[0]
        height = converted_scale[1]
        base = converted_location - Vector([0, height/2, 0])     
        be = extents.CylinderExtent(base, radius, height)
        return be

    elif obj.type == 'MESH':
        idtl = obj_to_idtl(obj)
        me = extents.MeshExtent()
        me.verts = idtl.verts
        me.triangles = idtl.indexes
        return me

    elif obj.type == 'EMPTY' and obj.empty_display_type == 'CUBE':
        be = extents.BoxExtents(None, None)
        converted_location = Vector(convert_vector3(obj.location))
        converted_scale = Vector(convert_scale(obj.scale))
        be.fromCenterAndScale(converted_location,converted_scale)
        return be

    elif obj.type == 'EMPTY' and obj.empty_display_type == 'SPHERE':
        converted_location = Vector(convert_vector3(obj.location))
        converted_scale = Vector(convert_scale(obj.scale))       
        be = extents.SphereExtents(converted_location, converted_scale[1])
        return be

    else:
        print(f"Error! Unhandled object in Collision collection: {obj.name}")
        return extents.NullExtents()

def create_detail_extents(broadPhaseObjs, otherObjs):    
    dtal = extents.DetailExtent()

    if len(broadPhaseObjs) > 1:
        dtal.broad_extent = create_component_extents(broadPhaseObjs)
    else:
        dtal.broad_extent = create_extent_for_obj(broadPhaseObjs[0])

    
    if len(otherObjs) > 1:
        dtal.extents = create_component_extents(otherObjs)
    else:
        dtal.extents = create_extent_for_obj(otherObjs[0])

    return dtal


def create_component_extents(objs):
    cmpt = extents.ComponentExtent()
    cpst = extents.CompositeExtent()
    for o in objs:
        e = create_extent_for_obj(o)
        cpst.extents.append(e)    
    cmpt.extent = cpst
    return cmpt

def create_extents_from_collection(collection):
    if len(collection.all_objects) == 0:
        return extents.NullExtents()    
    
    if len(collection.all_objects) == 1:
        return create_extent_for_obj(collection.all_objects[0])

    if len(collection.all_objects) > 1:
        broadphaseObjs = []
        otherObjs = []
        for o in collection.all_objects:
            if 'broadphase' in o and o['broadphase']:
                broadphaseObjs.append(o)
            else:
                otherObjs.append(o)
        
        if len(broadphaseObjs) > 0:
            return create_detail_extents(broadphaseObjs, otherObjs)

        else:
            return create_component_extents(collection.all_objects)

def create_light(collection, swgLight):
    blenderName=f'UnknownLightType-{swgLight.lightType}'
    blenderLightType = 'POINT'
    m=swgLight.transform
    if swgLight.lightType == 0:        
        blenderName='AmbientLight'
        blenderLightType = 'AREA'
    elif swgLight.lightType == 1:
        blenderName="DirectionalLight"
        blenderLightType = 'SUN'
    elif swgLight.lightType == 2:
        blenderName='PointLight'
        blenderLightType = 'POINT'
    else:
        print(f'Warning! Unhandled SOE Light Type: {swgLight.lightType}!')

    # Create light datablock
    light_data = bpy.data.lights.new(name="light-data", type=blenderLightType)
    light_data.energy = 100

    light_data.color = mathutils.Color(swgLight.diffuse_color[0:3])

    # Create new object, pass the light data 
    light_object = bpy.data.objects.new(name=blenderName, object_data=light_data)

    # Link object to collection in context
    collection.objects.link(light_object)

    # Change light position    
    light_object.matrix_world = [
        [m[0], m[8], m[4], 0.0],
        [m[2], m[10], m[6], 0.0],
        [m[1], m[9], m[5], 0.0],
        [-m[3], m[11], m[7], 0.0],
    ]

    return light_object

def swg_light_from_blender(ob): 

    if not ob.type == 'LIGHT':
        print(f"Error. Tried to convert non-light object to light: {ob.name}")
        return None

    #print(f"Object: {ob.name} is a light and its type is {ob.data.type}")
    # if not ob.data

    diffuseColor = ob.data.color
    lightType = 0
    if ob.data.type == 'AREA':        
        lightType = 0
    elif ob.data.type == 'SUN':        
        lightType = 1
    elif ob.data.type == 'POINT':        
        lightType = 2
    
    m = ob.matrix_world

    transform = [
        m[0][0], m[0][2], m[0][1], m[0][3],
        m[2][0], m[2][2], m[2][1], m[2][3],
        m[1][0], m[1][2], m[1][1], m[1][3]
    ]

    return swg_types.Light(lightType, diffuseColor, diffuseColor, transform, 1, 0, 0)

def create_pathgraph(pgrf_collection, pgrf, parent = None, onlyCellWaypoints = False):
    for node in pgrf.nodes:

        if onlyCellWaypoints and (node.type != 1):
            continue

        mesh = bpy.data.meshes.new(f"{swg_types.PathGraphNode.typeStr(node.type)}-{node.index}-mesh")
        sph = bpy.data.objects.new(f"{swg_types.PathGraphNode.typeStr(node.type)}-{node.index}", mesh)
        sph.location = Vector(convert_vector3(node.position))

        pgrf_collection.objects.link(sph)  
        
        # if a parent was provided, use it
        if parent != None:
            sph.parent = parent 

        # Select the newly created object
        bpy.context.view_layer.objects.active = sph
        sph.select_set(True)

        # Construct the bmesh sphere and assign it to the blender mesh.
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.5)
        bm.to_mesh(mesh)
        bm.free()
        bpy.ops.object.modifier_add(type='SUBSURF')
        bpy.ops.object.shade_smooth()

        sph['radius'] = node.radius

    if not onlyCellWaypoints:
        for edge in pgrf.edges:

            posA = pgrf.nodes[edge.indexA].position
            posB = pgrf.nodes[edge.indexB].position
            coords_list = []
            
            coords_list.append(Vector(convert_vector3([posA[0], posA[1], posA[2]])))
            coords_list.append(Vector(convert_vector3([posB[0], posB[1], posB[2]])))

            curveData = bpy.data.curves.new(f'edge-{edge.indexA}-{edge.indexB}', type='CURVE')
            curveData.dimensions = '3D'
            curveData.fill_mode = 'FULL'
            polyline = curveData.splines.new('POLY')
            polyline.points.add(len(coords_list)-1)

            for i, coord in enumerate(coords_list):
                polyline.points[i].co = (coord.x, coord.y, coord.z, 1)
                #print(f"Point {i}: {polyline.points[i]}")

            # make a new object with the curve
            obj = bpy.data.objects.new(f'edge-{edge.indexA}-{edge.indexB}', curveData)
            pgrf_collection.objects.link(obj)
                
            # if a parent was provided, use it
            if parent != None:
                obj.parent = parent
            
def unit_vector(vector):
    return vector / np.linalg.norm(vector)

def angle_between(v1, v2):
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))

def angle_between_unnormalized(v1, v2):
    return np.arccos(np.clip(np.dot(v1, v2), -1.0, 1.0))

def mat2rpy(R):
    from math import asin, pi, atan2, cos
    R11=R[0]
    R12=R[1]
    R13=R[2]
    R21=R[3]
    R22=R[4]
    R23=R[5]
    R31=R[6]
    R32=R[7]
    R33=R[8]
    roll = yaw = pitch = 0
    if R31 != 1 and R31 != -1:
        pitch_1 = -1*asin(R31)
        pitch_2 = pi - pitch_1
        roll_1 = atan2( R32 / cos(pitch_1) , R33 /cos(pitch_1) )
        roll_2 = atan2( R32 / cos(pitch_2) , R33 /cos(pitch_2) )
        yaw_1 = atan2( R21 / cos(pitch_1) , R11 / cos(pitch_1) )
        yaw_2 = atan2( R21 / cos(pitch_2) , R11 / cos(pitch_2) )
        pitch = pitch_1
        roll=roll_1
        yaw=yaw_1
    else:
        if R31 == -1:
            pitch = pi/2
            roll = yaw + atan2(R12,R13)
        else:
            pitch = -pi/2
            roll = -1*yaw + atan2(-1*R12,-1*R13)
    return (roll, pitch, yaw)

def convert_vector3(v):
    return Vector([v[0], v[2], v[1]])

def convert_scale(v):
    return Vector([abs(v[0]), abs(v[2]), abs(v[1])])

def create_hardpoint_obj(name, m, *, parent = None, collection = None):
    matrix = [
        [m[0], m[8], m[4], 0.0],
        [m[2], m[10], m[6], 0.0],
        [m[1], m[9], m[5], 0.0],
        [-m[3], m[11], m[7], 0.0],
    ]       
    hpntadded = bpy.data.objects.new(name=name, object_data=None)
    hpntadded.matrix_world = matrix
    hpntadded.empty_display_type = "ARROWS"

    if parent != None:
        hpntadded.parent = parent
    
    if collection != None:
        collection.objects.link(hpntadded)
    else:
        bpy.context.scene.collection.objects.link(hpntadded)

    return hpntadded

def hardpoint_from_obj(ob):   
    clean_name = ob.name.split('.')[0]
    m = ob.matrix_world
    return [
        m[0][0], m[0][2], m[0][1], m[0][3],
        m[2][0], m[2][2], m[2][1], m[2][3],
        m[1][0], m[1][2], m[1][1], m[1][3],
        clean_name
    ]

