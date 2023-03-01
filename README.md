# io_scene_swg
A Blender add-on for importing and exporting Star Wars Galaxies static (.msh) and animated (.mgn) mesh files
## Blender Version Support
Should work with Blender 2.9+ and 3+
## Features

### General SWG helper functions
* In the 3D View toolbar (contains menus like "View", "Select", "Object", etc), the very furthest right menu will be "SWG". This is where you can find some helper functions. NOTE: For many of these to work, you need to set the "SWG Client Extract Dir" path in the add-on preferences. This is a directory containing the full directory structure from a "Full Client Extract" via SIE. It should be the directory which contains child directories like "appearance", "shader" and "texture"
  * "Find and load materials": If you named your materials identically to a shader filename (no preceding dir or exteion, just "concertina_a_aa7" for example), and the path is set correctly, the images and some settings should automatically be applied to the materials in Blender
    * You can repeat selecting "Find and load materials" as often as you want (if you change a SWG Shader on disk, or want to change the shader completely), and it should keep any existing material assignments in the scene. 
  * "Add SWG Shader as Material": Similar to the above, but opens a file browser to select a SWG shader. The Shader is converted to a Material and added in a new Material Slot on the mesh. 
  * "Create a SWG .apt for this .msh": Creates a very simple .apt file at the browsed path representing the APT->MSH file chain. The reference inside the APT will always be "mesh/<currently selected object name>.msh" so change your object name accordingly. No support for APT->LOD->MSH or any other file chain yet. 

### MSH Import/Export:
* Import and Export SWG .msh file (versions 0004 and 0005)
* Since version 2.0.0, multi-shader MSHs are imported as one Blender mesh with per-face material assignemnt. Materials are created and properly assigned per shader used in the .msh
* UVs: Multiple UV sets are fully supported for import/export per material. When 1 shader uses multiple UV channels, you need to be sure to use the "UVSets" custom property properly:
  * When an SPS is imported, the number of UV channels it used are added as a custom property, "UVSets", on the specific material (not the main object or mesh). 
  * If you are creating a new object, or want to add more UV sets, create a new UV Map in blender, uv map your faces like normal, and make sure the given material for the shader you are working with has a "UVSets" custom property with the correct number of UV sets assigned
* DOT3: Imports the existance (or not) of DOT3 normalmap coordinates (tangents?), but not the tangents themselves since Blender will reclaculate these. Stored in the "DOT3" custom property per material. If you are creating a new object and want DOT3 for any/all shaders, you need to add a "DOT3" custom property to the material(s) with a value of "1"
* Normals: Imported normals are stored in Blenders' split normals. Split normals are exported. 
* Vertex Colors: Not supported (can read a mesh with them, but will be unused and lost). No export support.
* Extents: Automatically compute Extents (box and sphere)
* Collision Extents: Reads CollisionExtents and stores their binary data in a Custom Property so they can be exported. No edit support, but non-destructive 
* Floor: Saves floor file path in custom property, "Floor". You can add/edit this for export.
* Hardpoints: Supports hardpoints as empty "Arrows" objects. The name of the Arrows empty will become the name of the hardpoint at export. To add a hardpoint:
  * Create an empty Arrows object in Object mode:
    * Shift+A -> Empty -> Arrows 
  * Make the new Empty a child of a mesh object:
    * In Object Mode, multi-select the Arrow then the Mesh
    * Ctrl+P -> Object 
* Import option to "Remove Duplicate Verts". Shouldn't be needed in most cases, but will remove verts that are in the same 3D space and merge them. 

### MGN Import/Export:

* Imports base mesh, UV, Shader Name, Bone names, Vertex weights, Blends, occlusion zones, and skeleton name as follows:
  * The mesh is obviously the active imported object.
  * Bone names are Imported as vertex groups.
  * Vertex weights are imported and assigned relative to the vertex groups they belong to.
  * Blends are imported as shape keys.
  * Occlusion layer (2 for most wearables) is stored in the custom property, "OCC_LAYER"
  * Skeleton name(s) are imported as a custom properties. The name of the property will be of the form SKTM_n where n is an integer. This allows multiple skeletons to be affected. The value of the property is the path to the skeleton, including the directory, e.g. "appearance/skeleton/all_b.skt".
  * Occlusion zones are imported as Integer type custom properties. The name of the occlusion zone is "OZN_" plus the name of the occlusion zone; i.e "OZN_chest". The custom property value is 0 or 1, where 1 means occluded by this model and 0 means not occluded.
  * OCZ Support: You can specify the Occlusion Zones on this model by using Blender's "Face Map" feature. This is similar to a Vertex Group, but with faces. The name of the group must be either an occlusion zone ("chest", "torso_f") OR a colon-separated list of occlusion zones ("chest:torso_f"). Import a model like armor_padded_s01_chest_plate_m_l0.mgn to see an example. 
  * Shader name is imported as a material, in cases where there are multiple shaders, each shader is added as a new material.  Also,  each polygon in the mesh is properly assigned to each material.
  * UVs are imported for each shader, and stored in a single UV file within blender.  Again, the UVs are assigned properly to each Poly and material that gets created.  This allows you to import any and all textures from the SWG shader files into blender, and they will map properly.   Please be aware that SWG UVs are written to the MGN files Upside-Down.  Meaning they have to be flipped upright on import for them to work properly in blender.   
* This plugin will export a single object from blender into the MGN file format for SWG.  Items exported are the mesh, UV, Shader names, Bone names, bone weights, Blends, Occlusions and skeleton name.
  * Each item works the same as has already been described above for the importer.   This exporter will fail if multiple objects are selected for export.
  * The exporter will also flip the UV Upside down (mirror on the Y axis), on export,  so you don't need to manually flip the UV.
  * Materials get written to the PDST chunks in the order in which they appear in blender.  I would not change this order for imported MGNs, and for custom items, if you find the materials and shaders getting mixed up in the client,  I'd adjust the listing order to compensate.  This shouldn't be a problem,  but it has on occasion been a bit fickle.
* Hardpoints: Not properly supported (need a skeleton to know the relative positioning), but the binary data is preserved (and uneditable) in a custom property, "HPTS"
* Texture Renderers: Not properly supported but the binary data is preserved (and uneditable) in a custom property, "TRTS"

Notes: 
* If you create a new original mesh/object, you'll first need to choose a skeleton file that your mesh should use.  From that skeleton file, you'll want to use the bone names in the file for your vertex group names in Blender.  Then you can assign vertex weights as necessary.  When finished, make sure that the skeleton file name is set as a SKTM_n custom property where n is an integer. If there are no SKTM_ custom properties, one will be automatically added for the most common skeleton ("appearance/skeleton/all_b.skt"), which might not be what you want.
* If you import an existing MGN,  the vertex groups will be named properly from the start.  The skeleton file to be used will also be added as a custom property to the mesh. 
* Occlusion (OZN and ZTO chunks, not FOZC or OZC yet) are exported automatically based on the existence of Custom Properties. To understand what this is doing you probably need some additional information on how it works.
  * The SWG client has a list of zones that can be made invisible for humanoid type objects.  Most creatures do not use occlusions, and any extra layers of clothing or items are made to fit exactly without clipping.  For humanoids that can use extra layers of clothing and items,  SWG uses occlusions to avoid clipping with lower level layers.  So using a human as an example,  it loads with a default skin as layer 1.  If you make a shirt for the human to wear,  the shirt will occupy layer 2,  and without any occlusions the layer 1 body can clip through the shirt during movement in some circumstances.  To avoid this clipping, you can use occlusions, which will make segments of the layer 1 skin invisible.  a long sleeved shirt will occlude the chest, torso_f, torso_b, L_arm, R_arm, and maybe the formarms, and maybe even the waist zones… 
  * It's important to understand that you are not occluding zones on the object you're working with, but rather that you are occluding zones on the base skin mesh you want to make invisible.
  * So, to include occlusions as part of the export, I did so by making each exclusion zone a custom property (prepended with "OZN_") for the blender mesh/object.   The easiest way to see this in action is to import an existing clothing item,  dresses or robes are probably the best examples to get to know the system.  Then in blender,  look at the custom properties, and you'll see a listing for every occlusion zone that clothing item has been set to use.   For the properties:  1 = occluded (invisible),  0 = not occluded.  All zones import as occluded by default, so you'll want to make sure that you've switched the zones you want to see to.
  * If you export your clothing item, and load up the SWG client, and don't see a body part you were expecting to see,  example:  hands, or feet, or face, etc.,   then come back to blender and set those zones to zero.
Some additional function information.
* Blends / Shape keys:
  * Blends are the basic deformations of the base mesh that define how the object deforms along with the “body shape” sliders within the SWG client.  There are 4 main Blends for most clothing:  flat_chest, Skinny, Fat, and Muscle.  Heads for the various species have many more blends that correspond to the sliders you see at character creation. The base mesh, is also the Basis shape key.  Search google,  research, and learn for yourself how to properly use and save shape keys within blender.
* DOT3:
  * DOT3 (aka tangents, aka normalmap coords, aka per-pixel lighting coords) are optionally exportable since some shaders don't want them. Controlled by the export option, "DOT3" 

Limitations:
* Hardpoints and Texture Renderers are stored as binary data in a Custom Property on import, but there is no edit support for these. The existing data will be rewritten at export.  


