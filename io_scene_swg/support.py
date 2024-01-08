
import os, bpy
from bpy_extras.image_utils import load_image
from bpy_extras import node_shader_utils
from mathutils import Vector

from . import extents
from . import swg_types

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
                print(f"Removing Alpha: {image_node.name}")
                node_tree.nodes.remove(image_node)                
            if node.inputs['Base Color'].is_linked:
                image_node =  node.inputs['Base Color'].links[0].from_node
                print(f"Removing Base: {image_node.name}")
                node_tree.nodes.remove(image_node)              
            if node.inputs['Roughness'].is_linked:
                image_node =  node.inputs['Roughness'].links[0].from_node
                print(f"Removing Roughness: {image_node.name}")
                node_tree.nodes.remove(image_node)            
            if node.inputs['Specular'].is_linked:
                image_node =  node.inputs['Specular'].links[0].from_node
                print(f"Removing Specular: {image_node.name}")
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

def add_sphere(collection, collision, global_matrix, broadphase):
    print(f"Add sphere...")
    sph = bpy.data.objects.new(name="Sphere", object_data=None)        
    sph.empty_display_type = "SPHERE"
    sph.location = global_matrix @ Vector([-collision.center[0], collision.center[1], collision.center[2]])
    sph.empty_display_size = collision.radius
    collection.objects.link(sph)    

    if broadphase:
        sph['broadphase'] = 1

def add_box(collection, collision, global_matrix, broadphase):
    print(f"Add box...")
    box = bpy.data.objects.new(name="Box", object_data=None)        
    box.empty_display_type = "CUBE"
    location = collision.getCenter()
    box.location = global_matrix @ Vector([-location[0], location[1], location[2]])
    scale = collision.getSize()
    box.scale = global_matrix @ Vector(scale)
    box.color = [0,0,1,1]
    collection.objects.link(box)

    if broadphase:
        box['broadphase'] = 1

def add_mesh(collection, collision, global_matrix, broadphase):
    print(f"Add msh...")
    mesh = bpy.data.meshes.new(name='Cmesh-mesh')
    obj = bpy.data.objects.new("CMesh", mesh)
    collection.objects.link(obj)        
    mesh.from_pydata([[-v[0], v[1], v[2]] for v in collision.verts], [], [[v[2],v[1],v[0]] for v in collision.triangles])
    mesh.transform(global_matrix)
    mesh.update()
    mesh.validate()   

    if broadphase:
        obj['broadphase'] = 1

def add_rtw_mesh(collection, idtl, global_matrix, name):
    mesh = bpy.data.meshes.new(name=f'{name}-mesh')
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)        
    mesh.from_pydata([[-v[0], v[1], v[2]] for v in idtl.verts], [], [[v[2],v[1],v[0]] for v in idtl.indexes])
    mesh.transform(global_matrix)
    mesh.update()
    mesh.validate()

def add_component(collection, collision, global_matrix, broadphase):
    print(f"Add component...")
    return add_collision_to_collection(collection, collision.extent, global_matrix, broadphase)


def add_composite(collection, collision, global_matrix, broadphase):
    print(f"Add composite with extents {len(collision.extents)} ...")
    for e in collision.extents:
        add_collision_to_collection(collection, e, global_matrix, broadphase)


def add_detail(collection, collision, global_matrix, broadphase):
    print(f"Add Detail with {type(collision.broad_extent)} and {type(collision.extents)}")
    add_collision_to_collection(collection, collision.broad_extent, global_matrix, True)
    add_collision_to_collection(collection, collision.extents, global_matrix, False)

def add_collision_to_collection(collection, collision, global_matrix, broadphase = False):

    if isinstance(collision, extents.SphereExtents):
        add_sphere(collection, collision, global_matrix, broadphase)
    elif isinstance(collision, extents.BoxExtents):
        add_box(collection, collision, global_matrix, broadphase)
    elif isinstance(collision, extents.MeshExtent):
        add_mesh(collection, collision, global_matrix, broadphase)
    elif isinstance(collision, extents.CompositeExtent):
        add_composite(collection, collision, global_matrix, broadphase)
    elif isinstance(collision, extents.ComponentExtent):
        add_component(collection, collision, global_matrix, broadphase)
    elif isinstance(collision, extents.DetailExtent):
        add_detail(collection, collision, global_matrix, broadphase)