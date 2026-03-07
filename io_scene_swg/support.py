import os, bpy, math, mathutils
import numpy as np
from bpy_extras.image_utils import load_image
from bpy_extras import node_shader_utils
from bpy_extras.io_utils import axis_conversion
from mathutils import Vector, Matrix
import bmesh

from . import extents
from . import swg_types

SWG_EFT_ALPHA = 1
SWG_EFT_SPEC = 2
SWG_EFT_EMISMAP = 4
SWG_EFT_EMISFULL = 8
SWG_EFT_HUEMAP = 16
SWG_EFT_HUEFULL = 32
SWG_EFT_HUEMAP_RB = 64

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

def load_shared_image(path, root, convert_to_png = False):   
	abs_path = find_file(path, root)
	if not abs_path:
		print (f"Error! Couldn't find image: {path}")
		return None

	out_path = abs_path
	if convert_to_png:
		out_path = abs_path.replace(".dds",".png")
	
	image = None

	shortname = os.path.basename(out_path)
	for img in bpy.data.images: 
		if shortname == img.name:
			image = img
			print(f"Found image: shortname at {abs_path}. Already is: {img.name}. Has data? {img.has_data}")
			break
	
	if image == None:
		if convert_to_png:
			temp = load_image(abs_path, ".")
			temp.file_format = "PNG"
			temp.save_render(out_path)
			bpy.data.images.remove(temp)
		
		image = load_image(out_path, ".")
		image.alpha_mode = "CHANNEL_PACKED"
	
	return image

def configure_material_from_swg_shader(material, shader, root_dir, tex_to_png):
	material.use_backface_culling = True
	material.use_nodes = True
	node_tree = material.node_tree
	for node in node_tree.nodes:
		node_tree.nodes.remove(node)

	bsdf = node_tree.nodes.new('ShaderNodeBsdfPrincipled')
	bsdf.location = (0, 0)
	material_output = node_tree.nodes.new('ShaderNodeOutputMaterial')
	material_output.location = (250, 0)
	node_tree.links.new(material_output.inputs[0], bsdf.outputs[0])

	nodes = node_tree.nodes

	# Infer shader effect features
	shader_effects = 0
	emis_node = None
	if shader.effect:
		material["Effect"] = shader.effect
		if any([x in shader.effect for x in ["alpha", "invis", "water", "punchout"]]):
			shader_effects += SWG_EFT_ALPHA
		if shader.specular != None or "specmap" in shader.effect:
			shader_effects += SWG_EFT_SPEC
		if shader.emission != None or "emismap" in shader.effect:
			shader_effects += SWG_EFT_EMISMAP
		elif "emis_full" in shader.effect:
			shader_effects += SWG_EFT_EMISFULL
		if "color" in shader.effect:
			if "_rb" in shader.effect:
				shader_effects += SWG_EFT_HUEMAP_RB
			else:
				shader_effects += SWG_EFT_HUEMAP
		elif shader.effect.startswith("effect\h_"):
			shader_effects += SWG_EFT_HUEFULL
	
	x_ofs = 0
	attribute_multiply_node = None
	if "Color0" in material:
		if material["Color0"] == True:
			x_ofs = -300
			attribute_node = nodes.new('ShaderNodeAttribute')
			attribute_node.label = "Vertex Color"
			if (shader_effects & SWG_EFT_HUEMAP):
				attribute_node.location = (-500, 500)
			else:
				attribute_node.location = (-500, 300)
			attribute_node.attribute_type = 'GEOMETRY'
			attribute_node.attribute_name = "color0"

			attribute_multiply_node = nodes.new('ShaderNodeMix')
			attribute_multiply_node.label = "Vector Color Multiply"
			if (shader_effects & SWG_EFT_HUEMAP):
				attribute_node.location = (-250, 500)
			else:
				attribute_multiply_node.location = (-250, 300)
			attribute_multiply_node.data_type = 'RGBA'
			attribute_multiply_node.blend_type = 'MULTIPLY'
			# Factor is always 1
			attribute_multiply_node.inputs[0].default_value = 1

			# Connect Vector Color to Vector Multiply Multiply Color 1
			node_tree.links.new(attribute_multiply_node.inputs[6], attribute_node.outputs[0])
			# Connect MAIN texture Color to Vector Color Multiply Color 2
			#node_tree.links.new(attribute_multiply_node.inputs[7], main_node.outputs[0])
			# Connect Vector Color Multiply to BSDF Base Color
			node_tree.links.new(bsdf.inputs[0], attribute_multiply_node.outputs[2])

	main_node = None
	if shader.main:
		main_image = load_shared_image(shader.main, root_dir, tex_to_png)
		if main_image:
			main_node = nodes.new('ShaderNodeTexImage')
			main_node.label = "MAIN"
			main_node.location = (-300 + x_ofs, 0)
			main_node.image = main_image
			main_node.image.colorspace_settings.name = 'sRGB'
			main_node.image.alpha_mode = 'CHANNEL_PACKED'
			if attribute_multiply_node == None:
				# Connect MAIN texture Color to BSDF Base Color
				node_tree.links.new(bsdf.inputs[0], main_node.outputs[0])
			else:
				# Connect MAIN texture Color to Vector Color Multiply Color 2
				node_tree.links.new(attribute_multiply_node.inputs[7], main_node.outputs[0])

			# Hue Mapping
			if (shader_effects & SWG_EFT_HUEMAP) and (shader.hueb or not (shader_effects & SWG_EFT_ALPHA)):
				main_node.location = (-800 + x_ofs, 0)

				hueb_node = None
				if shader.hueb:
					hueb_image = load_shared_image(shader.hueb, root_dir, tex_to_png)
					if hueb_image:
						hueb_node = nodes.new('ShaderNodeTexImage')
						hueb_node.label = "HUEB"
						hueb_node.location = (-800 + x_ofs, 300)
						hueb_node.image = hueb_image
						hueb_node.image.alpha_mode = 'CHANNEL_PACKED'
				
				hue_mix_node = nodes.new('ShaderNodeMix')
				hue_mix_node.label = "MAIN Hue Mix"
				hue_mix_node.location = (-525 + x_ofs, 0)
				hue_mix_node.data_type = 'RGBA'
				hue_mix_node.inputs[6].default_value = (1, 1, 1, 1)
				if "MAIN" in shader.palette_colors:
					c = shader.palette_colors["MAIN"]
					hue_mix_node.inputs[7].default_value = (c[0], c[1], c[2], 1)
				else:
					hue_mix_node.inputs[7].default_value = (1, 0.1, 0.1, 1)

				hue_multiply_node = nodes.new('ShaderNodeMix')
				hue_multiply_node.label = "MAIN Hue Multiply"
				hue_multiply_node.location = (-350 + x_ofs, 0)
				hue_multiply_node.data_type = 'RGBA'
				hue_multiply_node.blend_type = 'MULTIPLY'
				# Factor is always 1
				hue_multiply_node.inputs[0].default_value = 1
				# Connect MAIN texture Color to Hue Multiply Color 1
				node_tree.links.new(hue_multiply_node.inputs[6], main_node.outputs[0])
				# Connect Hue Mix Color to Hue Multiply Color 2
				node_tree.links.new(hue_multiply_node.inputs[7], hue_mix_node.outputs[2])

				if not (shader_effects & SWG_EFT_ALPHA):
					# Connect MAIN texture Alpha to Hue Mix Node Factor
					node_tree.links.new(hue_mix_node.inputs[0], main_node.outputs[1])
					
					# If a Hue B texture exists...
					if hueb_node:
						hueb_mix_node = nodes.new('ShaderNodeMix')
						hueb_mix_node.label = "HUEB Mix"
						hueb_mix_node.location = (-525 + x_ofs, 300)
						hueb_mix_node.data_type = 'RGBA'
						hueb_mix_node.inputs[6].default_value = (1, 1, 1, 1)
						if "HUEB" in shader.palette_colors:
							c = shader.palette_colors["HUEB"]
							hueb_mix_node.inputs[7].default_value = (c[0], c[1], c[2], 1)
						else:
							hueb_mix_node.inputs[7].default_value = (0.1, 0.1, 1, 1)
						# Connect HUEB texture Alpha to Hue Mix Factor
						node_tree.links.new(hueb_mix_node.inputs[0], hueb_node.outputs[1])

						hueb_multiply_node = nodes.new('ShaderNodeMix')
						hueb_multiply_node.label = "HUEB Multiply"
						hueb_multiply_node.location = (-175 + x_ofs, 0)
						hueb_multiply_node.data_type = 'RGBA'
						hueb_multiply_node.blend_type = 'MULTIPLY'
						# Factor is always 1
						hueb_multiply_node.inputs[0].default_value = 1
						# Connect Hue Multiply Color to Hue B Multiply Color 1
						node_tree.links.new(hueb_multiply_node.inputs[6], hue_multiply_node.outputs[2])
						# Connect Hue B Mix Color to Hue B Multiply Color 2
						node_tree.links.new(hueb_multiply_node.inputs[7], hueb_mix_node.outputs[2])
						if attribute_multiply_node == None:
							# Connect Hue B Multiply Color to BSDF Base Color
							node_tree.links.new(bsdf.inputs[0], hueb_multiply_node.outputs[2])
						else:
							# Connect Hue B Multiply Color to Vector Color Multiply Color 2
							node_tree.links.new(attribute_multiply_node.inputs[7], hueb_multiply_node.outputs[2])
					
					# No Hue B texture
					else:
						# Move MAIN hue to Color A
						if "MAIN" in shader.palette_colors:
							c = shader.palette_colors["MAIN"]
							hue_mix_node.inputs[6].default_value = (c[0], c[1], c[2], 1)
						else:
							hue_mix_node.inputs[6].default_value = (1, 0.1, 0.1, 1)
						# Color B could be HUEB or MAIN again
						if "HUEB" in shader.palette_colors:
							c = shader.palette_colors["HUEB"]
						elif "MAIN2" in shader.palette_colors:
							c = shader.palette_colors["MAIN2"]
						else:
							c = [1, 1, 1]
						hue_mix_node.inputs[7].default_value = (c[0], c[1], c[2], 1)
						# Connect MAIN Hue Multiply Color to BSDF Base Color
						if attribute_multiply_node == None:
							# Connect Hue Multiply Color to BSDF Base Color
							node_tree.links.new(bsdf.inputs[0], hue_multiply_node.outputs[2])
						else:
							# Connect Hue Multiply Color to Vector Color Multiply Color 2
							node_tree.links.new(attribute_multiply_node.inputs[7], hue_multiply_node.outputs[2])
				
				# Transparency shader; use Hue B for hue mapping
				elif hueb_node:
					hueb_mix_node = nodes.new('ShaderNodeMix')
					hueb_mix_node.label = "HUEB Mix"
					hueb_mix_node.location = (-525 + x_ofs, 300)
					hueb_mix_node.data_type = 'RGBA'
					hueb_mix_node.inputs[6].default_value = (1, 0.1, 0.1, 1)
					if "HUEB" in shader.palette_colors:
						c = shader.palette_colors["HUEB"]
						hueb_mix_node.inputs[7].default_value = (c[0], c[1], c[2], 1)
					else:
						hueb_mix_node.inputs[7].default_value = (0.1, 0.1, 1, 1)
					# Connect HUEB texture Alpha to Hue Mix Factor
					node_tree.links.new(hueb_mix_node.inputs[0], hueb_node.outputs[1])

					hueb_multiply_node = nodes.new('ShaderNodeMix')
					hueb_multiply_node.label = "HUEB Multiply"
					hueb_multiply_node.location = (-150 + x_ofs, 0)
					hueb_multiply_node.data_type = 'RGBA'
					hueb_multiply_node.blend_type = 'MULTIPLY'
					# Factor is always 1
					hueb_multiply_node.inputs[0].default_value = 1
					# Connect MAIN texture Color to Hue B Multiply Color 1
					node_tree.links.new(hueb_multiply_node.inputs[6], main_node.outputs[0])
					# Connect Hue B Mix Color to Hue B Multiply Color 2
					node_tree.links.new(hueb_multiply_node.inputs[7], hue_multiply_node.outputs[0])
					# Connect Hue B Multiply Color to BSDF Base Color
					node_tree.links.new(bsdf.inputs[0], hueb_multiply_node.outputs[0])
					if attribute_multiply_node == None:
						# Connect Hue B Multiply Color to BSDF Base Color
						node_tree.links.new(bsdf.inputs[0], hueb_multiply_node.outputs[2])
					else:
						# Connect Hue B Multiply Color to Vector Color Multiply Color 2
						node_tree.links.new(attribute_multiply_node.inputs[7], hueb_multiply_node.outputs[2])
			
			# Hue Shading
			elif (shader_effects & SWG_EFT_HUEFULL):
				main_node.location = (-450, x_ofs)
				hue_multiply_node = nodes.new('ShaderNodeMix')
				hue_multiply_node.label = "Hue Multiply"
				hue_multiply_node.location = (-175 + x_ofs, 0)
				hue_multiply_node.data_type = 'RGBA'
				hue_multiply_node.blend_type = 'MULTIPLY'
				hue_multiply_node.inputs[0].default_value = 1 # Factor is always 1
				if "MAIN" in shader.palette_colors:
					c = shader.palette_colors["MAIN"]
					hue_multiply_node.inputs[7].default_value = (c[0], c[1], c[2], 1)
				else:
					hue_multiply_node.inputs[7].default_value = (1, 1, 1, 1)
				# Connect MAIN texture Color to Hue Multiply Color 1
				node_tree.links.new(hue_multiply_node.inputs[6], main_node.outputs[0])
				node_tree.links.new(bsdf.inputs[0], hue_multiply_node.outputs[2])
			
			# Hue Mapping Red Blue
			elif (shader_effects & SWG_EFT_HUEMAP_RB) and (shader.hueb):
				hueb_image = load_shared_image(shader.hueb, root_dir, tex_to_png)
				if hueb_image:
					main_node.location = (-525 + x_ofs, 0)

					hueb_node = nodes.new('ShaderNodeTexImage')
					hueb_node.label = "HUEB"
					hueb_node.location = (-1100 + x_ofs, 300)
					hueb_node.image = hueb_image
					hueb_node.image.colorspace_settings.name = 'Raw'
					#hueb_node.image.alpha_mode = 'CHANNEL_PACKED'

					# Separate the hue map's color channels
					split_color_node = nodes.new('ShaderNodeSeparateColor')
					split_color_node.label = "HUEB Split Color"
					split_color_node.location = (-800 + x_ofs, 300)
					# Connect HUEB texture Color to Split Color Color
					node_tree.links.new(split_color_node.inputs[0], hueb_node.outputs[0])

					# Palette Colors
					hue_palette_node = nodes.new('ShaderNodeMix')
					hue_palette_node.label = "Hue Palette Mix"
					hue_palette_node.location = (-600 + x_ofs, 300)
					hue_palette_node.data_type = 'RGBA'
					
					if "HUEB" in shader.palette_colors:
						c = shader.palette_colors["HUEB"]
						hue_palette_node.inputs[6].default_value = (c[0], c[1], c[2], 1)
					else:
						hue_palette_node.inputs[6].default_value = (1, 1, 1, 1)
					if "HUEB2" in shader.palette_colors:
						c = shader.palette_colors["HUEB2"]
						hue_palette_node.inputs[7].default_value = (c[0], c[1], c[2], 1)
					else:
						hue_palette_node.inputs[7].default_value = (0.1, 0.1, 1, 1)
					# Connect Split Color Red Channel to Hue Mix Factor
					node_tree.links.new(hue_palette_node.inputs[0], split_color_node.outputs[0])

					# Influence
					hue_influence_node = nodes.new('ShaderNodeMix')
					hue_influence_node.label = "Hue Influence Mix"
					hue_influence_node.location = (-400 + x_ofs, 300)
					hue_influence_node.data_type = 'RGBA'
					hue_influence_node.inputs[7].default_value = (1, 1, 1, 1)
					# Connect Split Color Blue Channel to Hue Influence Factor
					node_tree.links.new(hue_influence_node.inputs[0], split_color_node.outputs[2])
					# Connect Hue Palette Result to Hue Influence Color A
					node_tree.links.new(hue_influence_node.inputs[6], hue_palette_node.outputs[2])

					hue_multiply_node = nodes.new('ShaderNodeMix')
					hue_multiply_node.label = "Hue Multiply"
					hue_multiply_node.location = (-200 + x_ofs, 150)
					hue_multiply_node.data_type = 'RGBA'
					hue_multiply_node.blend_type = 'MULTIPLY'
					# Factor is always 1
					hue_multiply_node.inputs[0].default_value = 1
					# Connect MAIN texture Color to Hue B Multiply Color 1
					node_tree.links.new(hue_multiply_node.inputs[6], main_node.outputs[0])
					# Connect Hue Influence Mix Color to Hue Multiply Color 2
					node_tree.links.new(hue_multiply_node.inputs[7], hue_influence_node.outputs[2])
					# Connect Hue B Multiply Color to BSDF Base Color
					node_tree.links.new(bsdf.inputs[0], hue_multiply_node.outputs[2])
			
			if not main_node.outputs[1].is_linked:
				# Transparency
				if (shader_effects & SWG_EFT_ALPHA):
					# Connect MAIN texture Alpha to BSDF Alpha
					node_tree.links.new(bsdf.inputs[21], main_node.outputs[1])
					material.blend_method = 'HASHED'
					material.shadow_method = 'HASHED'
				# Specular
				elif (shader_effects & SWG_EFT_SPEC):
					if shader.specular == None or shader.specular == shader.main:
						# Connect MAIN texture Alpha to BSDF Specular
						node_tree.links.new(bsdf.inputs[7], main_node.outputs[1])
				# Emission Map
				elif (shader_effects & SWG_EFT_EMISMAP):
					if shader.emission == None or shader.emission == shader.main:
						emis_node = nodes.new('ShaderNodeVectorMath')
						emis_node.label = "Emission Factor"
						emis_node.operation = 'MULTIPLY'
						emis_node.location = (-175 + x_ofs, -380)
						# Connect MAIN texture to Vector Multiply Node
						node_tree.links.new(emis_node.inputs[0], main_node.outputs[0])
						node_tree.links.new(emis_node.inputs[1], main_node.outputs[1])
						# Connect Vector Multiply Node to BSDF Emission
						node_tree.links.new(bsdf.inputs[19], emis_node.outputs[0])
				# Emission Full
				if (shader_effects & SWG_EFT_EMISFULL):
					# Connect MAIN texture Color to BSDF Emission
					node_tree.links.new(bsdf.inputs[19], main_node.outputs[0])
		
		# Transparency fallback
		elif (shader_effects & SWG_EFT_ALPHA):
			material.blend_method = 'BLEND'
			bsdf.inputs[21].default_value = 0.1
	# Transparency fallback
	elif (shader_effects & SWG_EFT_ALPHA):
		material.blend_method = 'BLEND'
		bsdf.inputs[21].default_value = 0.1
	
	bsdf.inputs[7].default_value = 0.0

	if shader.specular:
		if shader.specular != shader.main and shader.specular != shader.normal:
			spec_image = load_shared_image(shader.specular, root_dir, tex_to_png)
			if spec_image:
				spec_node = nodes.new('ShaderNodeTexImage')
				spec_node.label = "SPEC"
				spec_node.location = (-525, -260)
				spec_node.image = spec_image
				if spec_image != main_image:
					spec_node.image.colorspace_settings.name = 'Raw'
				# Connect SPEC texture Alpha to BSDF Specular
				node_tree.links.new(bsdf.inputs[7], spec_node.outputs[1])

	if shader.compressed_normal:
		normal_image = load_shared_image(shader.compressed_normal, root_dir, tex_to_png)
		if normal_image:
			normal_node = nodes.new('ShaderNodeTexImage')
			normal_node.label = "CNRM"
			normal_node.location = (-1850, -560)
			normal_node.image = normal_image
			#normal_node.image.alpha_mode = 'CHANNEL_PACKED'
			normal_node.image.colorspace_settings.name = 'Raw'

			# Separate the Compressed Normal's color channels
			split_color_node = nodes.new('ShaderNodeSeparateColor')
			split_color_node.label = "CNRM Split Color"
			split_color_node.location = (-1575, -560)
			node_tree.links.new(split_color_node.inputs[0], normal_node.outputs[0])

			# Create and connect Vector Normal Map Node to BSDF Normal
			map_node = nodes.new('ShaderNodeNormalMap')
			map_node.location = (-175, -560)
			node_tree.links.new(bsdf.inputs['Normal'], map_node.outputs[0])

			# Create and connect Combine Color Node to Vector Normal Map Node
			combine_color_node = nodes.new('ShaderNodeCombineColor')
			combine_color_node.location = (-350, -560)
			node_tree.links.new(map_node.inputs[1], combine_color_node.outputs[0])

			# Compressed normals are decompressed in SWG using what appears to be a slightly modified DXT5 normal decompression.
			# The Compressed Normal's Alpha and Green channels each have 0.5 subtracted from them, multiplied by 2, and then sent to the Red and Green channels respectively.
			# The Blue Channel is derived using the calculation sqrt(1 - (red * red + green * green)).
			# We create the necessary nodes for these operations in reverse order, preparing the Red and Green channels first.

			# RED CHANNEL
			math_node_multiply_r = nodes.new('ShaderNodeMath')
			math_node_multiply_r.label = "R Mult"
			math_node_multiply_r.location = (-1225, -470)
			math_node_multiply_r.operation = 'MULTIPLY'
			math_node_multiply_r.inputs[1].default_value = 2.0
			# Connect Math Node to Combine Color's Red Channel
			node_tree.links.new(combine_color_node.inputs[0], math_node_multiply_r.outputs[0])

			math_node_subtract = nodes.new('ShaderNodeMath')
			math_node_subtract.label = "R Sub"
			math_node_subtract.location = (-1400, -470)
			math_node_subtract.operation = 'SUBTRACT'
			math_node_subtract.inputs[1].default_value = 0.5
			node_tree.links.new(math_node_multiply_r.inputs[0], math_node_subtract.outputs[0])
			# Connect Compressed Normal texture's Alpha Channel to Math Node
			node_tree.links.new(math_node_subtract.inputs[0], normal_node.outputs[1])

			# GREEN CHANNEL
			math_node_multiply_g = nodes.new('ShaderNodeMath')
			math_node_multiply_g.label = "G Mult"
			math_node_multiply_g.location = (-1225, -650)
			math_node_multiply_g.operation = 'MULTIPLY'
			math_node_multiply_g.inputs[1].default_value = 2.0
			# Connect Math Node to Combine Color's Green Channel
			node_tree.links.new(combine_color_node.inputs[1], math_node_multiply_g.outputs[0])

			math_node_subtract = nodes.new('ShaderNodeMath')
			math_node_subtract.label = "G Sub"
			math_node_subtract.location = (-1400, -650)
			math_node_subtract.operation = 'SUBTRACT'
			math_node_subtract.inputs[1].default_value = 0.5
			node_tree.links.new(math_node_multiply_g.inputs[0], math_node_subtract.outputs[0])
			# Connect Compressed Normal texture's Green Channel to Math Node
			node_tree.links.new(math_node_subtract.inputs[0], split_color_node.outputs[1])

			# BLUE CHANNEL
			math_node_sqrt = nodes.new('ShaderNodeMath')
			math_node_sqrt.label = "B Sqrt"
			math_node_sqrt.location = (-525, -760)
			math_node_sqrt.operation = 'SQRT'
			node_tree.links.new(combine_color_node.inputs[2], math_node_sqrt.outputs[0])
			
			math_node_subtract = nodes.new('ShaderNodeMath')
			math_node_subtract.label = "B Sub"
			math_node_subtract.location = (-700, -760)
			math_node_subtract.operation = 'SUBTRACT'
			math_node_subtract.inputs[0].default_value = 1.0
			node_tree.links.new(math_node_sqrt.inputs[0], math_node_subtract.outputs[0])

			math_node_add = nodes.new('ShaderNodeMath')
			math_node_add.label = "B Add"
			math_node_add.location = (-875, -760)
			math_node_add.operation = 'ADD'
			node_tree.links.new(math_node_subtract.inputs[1], math_node_add.outputs[0])

			# Red Channel
			math_node_power = nodes.new('ShaderNodeMath')
			math_node_power.label = "R Pwr"
			math_node_power.location = (-1050, -760)
			math_node_power.operation = 'POWER'
			math_node_power.inputs[1].default_value = 2.0
			node_tree.links.new(math_node_add.inputs[0], math_node_power.outputs[0])
			node_tree.links.new(math_node_power.inputs[0], math_node_multiply_r.outputs[0])

			# Green Channel
			math_node_power = nodes.new('ShaderNodeMath')
			math_node_power.label = "G Pwr"
			math_node_power.location = (-1050, -960)
			math_node_power.operation = 'POWER'
			math_node_power.inputs[1].default_value = 2.0
			node_tree.links.new(math_node_add.inputs[1], math_node_power.outputs[0])
			node_tree.links.new(math_node_power.inputs[0], math_node_multiply_g.outputs[0])

	elif shader.normal:
		normal_image = load_shared_image(shader.normal, root_dir, tex_to_png)
		if normal_image:
			normal_node = nodes.new('ShaderNodeTexImage')
			normal_node.label = "NRML"
			normal_node.location = (-450, -575)
			normal_node.image = normal_image
			normal_node.image.colorspace_settings.name = 'Raw'
			#normal_node.image.alpha_mode = 'CHANNEL_PACKED'
			map_node = nodes.new('ShaderNodeNormalMap')
			map_node.location = (-175, -575)
			# Connect NRML texture Color to Vector Normal Map Node Color
			node_tree.links.new(map_node.inputs[1], normal_node.outputs[0])
			# Connect Vector Normal Map Node to BSDF Normal
			node_tree.links.new(bsdf.inputs[22], map_node.outputs[0])
			
			if (shader_effects & SWG_EFT_SPEC) and not bsdf.inputs[7].is_linked:
				node_tree.links.new(bsdf.inputs[7], normal_node.outputs[1])
			# Emission Map
			elif (shader_effects & SWG_EFT_EMISMAP) and main_node != None:
				if shader.emission == None or shader.emission == shader.normal:
					emis_node = nodes.new('ShaderNodeVectorMath')
					emis_node.label = "Emission Factor"
					emis_node.operation = 'MULTIPLY'
					emis_node.location = (-175, -380)
					# Connect MAIN texture Color to Vector Multiply Node
					node_tree.links.new(emis_node.inputs[0], main_node.outputs[0])
					# Connect NRML texture Alpha to Vector Multiply Node
					node_tree.links.new(emis_node.inputs[1], normal_node.outputs[1])
					# Connect Vector Multiply Node to BSDF Emission
					node_tree.links.new(bsdf.inputs[19], emis_node.outputs[0])
	
	if shader.emission and shader.emission != shader.main and shader.emission != shader.normal:
		emis_image = load_shared_image(shader.emission, root_dir, tex_to_png)
		if emis_image:
			emismap_node = nodes.new('ShaderNodeTexImage')
			emismap_node.label = "EMIS"
			emismap_node.location = (-225, 260)
			emismap_node.image = emis_image
			if emis_image != main_image:
				emismap_node.image.colorspace_settings.name = 'Raw'

			emis_node = nodes.new('ShaderNodeVectorMath')
			emis_node.operation = 'MULTIPLY'
			emis_node.location = (-175, -380)
			# Connect MAIN texture Color to Vector Multiply Node
			node_tree.links.new(emis_node.inputs[0], main_node.outputs[0])
			# Connect EMIS texture Alpha to Vector Multiply Node
			node_tree.links.new(emis_node.inputs[1], emismap_node.outputs[1])
			# Connect Vector Multiply Node to BSDF Emission
			node_tree.links.new(bsdf.inputs[19], emis_node.outputs[0])

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
		blenderName="ParallelLight"
		blenderLightType = 'SUN'
	elif swgLight.lightType == 2:
		blenderName='PointLight'
		blenderLightType = 'POINT'
	elif swgLight.lightType == 3:
		blenderName='AreaLight'
		blenderLightType = 'POINT'
	elif swgLight.lightType == 4:
		blenderName='SpotLight'
		blenderLightType = 'SPOT'
	else:
		print(f'Warning! Unhandled SOE Light Type: {swgLight.lightType}!')

	# Create light datablock
	light_data = bpy.data.lights.new(name="light-data", type=blenderLightType)
	light_data.energy = swgLight.intensity
	if light_data.energy == 0:
		light_data.energy = 0.0001

	for c in range(3):
		swgLight.diffuse_color[c] /= light_data.energy
		swgLight.specular_color[c] /= light_data.energy

	light_data.color = mathutils.Color(swgLight.diffuse_color[0:3])
	
	light_data['specular_color'] = mathutils.Color(swgLight.specular_color[0:3])
	light_data.id_properties_ui('specular_color').update(
			default=(0, 0, 0), 
			min=0.0, 
			max=1.0, 
			soft_min=0.0, 
			soft_max=1.0, 
			subtype="COLOR"
		)
	
	light_data['constant_attenuation'] = swgLight.constant_att
	light_data['linear_attenuation'] = swgLight.linear_att
	light_data['quadratic_attenuation'] = swgLight.quad_att

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

	lightType = 0
	if ob.data.type == 'POINT':
		lightType = 2 # Point
	elif ob.data.type == 'SUN':		
		lightType = 1 # Parallel
	elif ob.data.type == 'AREA':		
		lightType = 0 # Ambient
	elif ob.data.type == 'SPOT':
		lightType = 4 # Spot; discarded currently; support with CELL version 0006?
	
	intensity = ob.data.energy
	
	diffuse_color = ob.data.color
	
	specular_color = diffuse_color
	if 'specular_color' in ob.data:
		specular_color = ob.data['specular_color']
	else:
		ob.data['specular_color'] = specular_color
		ob.data.id_properties_ui('specular_color').update(
			default=(0, 0, 0), 
			min=0.0, 
			max=1.0, 
			soft_min=0.0, 
			soft_max=1.0, 
			subtype="COLOR"
		)
	
	m = ob.matrix_world
	transform = [
		m[0][0], m[0][2], m[0][1], m[0][3],
		m[2][0], m[2][2], m[2][1], m[2][3],
		m[1][0], m[1][2], m[1][1], m[1][3]
	]

	constant_attenuation = 1.0
	if 'constant_attenuation' in ob.data:
		constant_attenuation = ob.data['constant_attenuation']
	else:
		ob.data['constant_attenuation'] = constant_attenuation

	linear_attenuation = 0.0
	if 'linear_attenuation' in ob.data:
		linear_attenuation = ob.data['linear_attenuation']
	else:
		ob.data['linear_attenuation'] = linear_attenuation

	quadratic_attenuation = 0.0
	if 'quadratic_attenuation' in ob.data:
		quadratic_attenuation = ob.data['quadratic_attenuation']
	else:
		ob.data['quadratic_attenuation'] = quadratic_attenuation

	return swg_types.Light(lightType, intensity, diffuse_color, specular_color, transform, constant_attenuation, linear_attenuation, quadratic_attenuation)

def create_interior_buildout(collection):
	buildout_text = "strTemplate\tfltJX\tfltJY\tfltJZ\tfltKX\tfltKY\tfltKZ\tfltPX\tfltPY\tfltPZ\tstrObjVars\tstrScripts\tstrCellName\tintNoCreate\tstrLocationList\ns\tf\tf\tf\tf\tf\tf\tf\tf\tf\tp\ts\ts\ti\ts\n"

	print(f"Generating interior buildout for {collection.name}...")
	for cell in collection.children:
		print(f"\t{cell.name} Objects:")
		for cell_col in cell.children:
			if cell_col.name.startswith("Objects_"):
				for obj in cell_col.objects:
					obj_text = ""

					if 'template' in obj:
						obj_text += obj['template'] + "\t"
					else:
						obj['template'] = ""
						print(f"\t\tERROR! Missing \"template\" property in {obj.name}!")
						continue

					m = obj.matrix_world
					t = [
						m[0][0], m[0][2], m[0][1], m[0][3],
						m[2][0], m[2][2], m[2][1], m[2][3],
						m[1][0], m[1][2], m[1][1], m[1][3]
					]
					for i in range(len(t)):
						t[i] = round(t[i], 9)
					
					obj_text += f"{t[1]}\t{t[5]}\t{t[9]}\t"
					obj_text += f"{t[2]}\t{t[6]}\t{t[10]}\t"
					obj_text += f"{t[3]}\t{t[7]}\t{t[11]}\t"

					if 'objvars' in obj:
						if obj['objvars'].endswith("$|"):
							obj_text += obj['objvars'] + "\t"
						else:
							obj_text += "$|" + obj['objvars'] + "\t"
					else:
						obj['objvars'] = "$|"
						obj_text += "$|\t"
					
					if 'scripts' in obj:
						obj_text += obj['scripts'] + "\t"
					else:
						obj['scripts'] = ""
						obj_text += "\t"
					
					obj_text += cell.name + "\t"

					if 'no_create' in obj:
						obj_text += str(obj['no_create']) + "\t"
					else:
						obj['no_create'] = 0
						obj_text += "0\t"
					
					if 'location_list' in obj:
						obj_text += obj['location_list'] + "\n"
					else:
						obj['location_list'] = ""
						obj_text += "\n"
					
					buildout_text += obj_text
					print(f"\t\t{obj.name}")
	
	return buildout_text

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
