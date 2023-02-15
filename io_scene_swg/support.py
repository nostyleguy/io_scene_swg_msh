
import os, bpy
from bpy_extras.image_utils import load_image
from bpy_extras import node_shader_utils

def clean_path(path):
    return path.replace('\\', '/') if (os.sep == '/') else path.replace('/', '\\')

def find_file(relative_path, root):
    root=clean_path(root)
    relative_path=clean_path(relative_path)
    if os.path.exists(os.path.join(root, relative_path)):
        return os.path.join(root,relative_path)
    else:
        return None

def load_shared_image(path, root):   
    path = find_file(path, root)
    png_path = path.replace(".dds",".png")
    image = None
    if path:
        shortname = os.path.basename(png_path)
        for img in bpy.data.images: 
            if shortname == img.name:
                image = img
                break
    if image == None:
        temp = load_image(path, ".") 
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