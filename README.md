# io_scene_swg
A Blender add-on for importing and exporting various Star Wars Galaxies asset formats.

### Blender Version Support
Should work with Blender 2.9+ and 3+

### Features
- Import / export formats:
  - mgn (Animated Mesh)
  - msh (Static Mesh)
  - lod (Level of Detail Static Mesh Group)
  - pob (Portalized Object)
  - skt (Skeleton)
- Generate .apt, .sat and .lmg files
- Generate materials from .sht (shader) files
- Generate .pob hierarchies and interior buildouts

### Recommended External Tools
- [Sytner's Iff Editor (SIE)](https://modthegalaxy.com/index.php?resources/sie.1/)
  - Tool used to edit almost all of SWG's file types.
  - Requires forum account to download.
- [Krita](https://krita.org/en/)
  - Free and open source image editing software. Very handy replacement for Photoshop.
- [NVIDIA Texture Tools Exporter](https://developer.nvidia.com/texture-tools-exporter)
  - Standalone app recommended. Useful for converting image types like PNG into DDS textures useable by SWG.
  - Included in this repository is `swg_dds_nvidia_tex_tools_preset.dpf`, a preset for the Texture Tools that works with SWG's DDS support.
  - Can accurately display DDS files and will show where errors in your textures will occur (typically caused by alpha transparency in PNGs).
  - Requires signing in with a NVIDIA Account. The tools are free, but can be a bit of a hassle to download.
- Krita DDS Python Plugin [Import](https://github.com/esuriddick/Programming/tree/main/Python/Krita/DDS_File_Importer) / [Export](https://github.com/esuriddick/Programming/tree/main/Python/Krita/DDS_File_Exporter)
  - An alternative to the NVIDIA Texture Tools. It's a bit clunky and doesn't have a way to show you if you screwed something up before you get into the game, but it works.

## How To Use

### General SWG helper functions
* In the 3D View toolbar (contains menus like "View", "Select", "Object", etc), the very furthest right menu will be "SWG". This is where you can find some helper functions. NOTE: For many of these to work, you need to set the "SWG Client Extract Dir" path in the add-on preferences. This is a directory containing the full directory structure from a "Full Client Extract" via SIE. It should be the directory which contains child directories like "appearance", "shader" and "texture"
  * "Initialize MGN data (occlusions, bones, blends) from an existing MGN": Browse to an existing MGN file, and sets up the current objects's Occlusion, Bone and Blend Shape data to match. A very quick way to get started making a similar item like a new wearable. Does not actually assign any mesh verts to the Vertex Groups, faces to the Face Maps, or do anything with materials. 
  * "Find and load materials": If you named your materials identically to a shader filename (no preceding dir or extention, just "concertina_a_aa7" for example), and the path is set correctly, the images and some settings should automatically be applied to the materials in Blender
    * You can repeat selecting "Find and load materials" as often as you want (if you change a SWG Shader on disk, or want to change the shader completely), and it should keep any existing material assignments in the scene. 
  * "Add SWG Shader as Material": Similar to the above, but opens a file browser to select a SWG shader. The Shader is converted to a Material and added in a new Material Slot on the mesh. 
  * "Create a SWG .apt for this .msh": Creates a very simple .apt file at the browsed path representing the APT->MSH file chain. The reference inside the APT will always be "mesh/\<currently selected object name\>.msh" so change your object name accordingly. No support for APT->LOD->MSH or any other file chain yet.
  * "Create a SWG .sat and .lmg for this .mgn": Creates .sat and .lmg files at the browsed path representing the SAT->LMG->MGN file chain. The reference inside the LMG will always be "mesh/\<currently selected object name\>.mgn" so change your object name accordingly.
  * "Generate Blend Shapes From Other": Attempts to use the shape key deltas in one mesh to create shape keys in another. Use Ctrl+click to select 2 meshes. The first is the source and the second is the destination. For every shape key in source, this will create a same-named shape key in destination. In addition, it will actually try to update the vertex deltas in destination's shap keys. It does this by finding the closest vertex in source, and applying the same delta it had in this shape key. This works okay, but not amazing.

### MSH (Static Mesh) Import / Export:
* Import and Export SWG .msh file (versions 0004 and 0005)
* Since version 2.0.0, multi-shader MSHs are imported as one Blender mesh with per-face material assignemnt. Materials are created and properly assigned per shader used in the .msh
* UVs: Multiple UV sets are fully supported for import/export per material. When 1 shader uses multiple UV channels, you need to be sure to use the "UVSets" custom property properly:
  * When an SPS is imported, the number of UV channels it used are added as a custom property, "UVSets", on the specific material (not the main object or mesh). 
  * If you are creating a new object, or want to add more UV sets, create a new UV Map in blender, uv map your faces like normal, and make sure the given material for the shader you are working with has a "UVSets" custom property with the correct number of UV sets assigned
* DOT3: Imports the existance (or not) of DOT3 normalmap coordinates (tangents?), but not the tangents themselves since Blender will reclaculate these. Stored in the "DOT3" custom property per material. If you are creating a new object and want DOT3 for any/all shaders, you need to add a "DOT3" custom property to the material(s) with a value of "1"
* Normals: Imported normals are stored in Blenders' split normals. Split normals are exported. 
* Vertex Colors: Imports color0 and color1 into mesh Color Attributes if present. Adds a Custom Property "Color0" and/or "Color1" onto Materials representing SPSs that use vertex colors. The exporter looks for this Custom Property to determine whether to export them since each SPS can have them or not.
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

### MGN (Animated Mesh) Import / Export:
* Imports base mesh, UV, Shader Name, Bone names, Vertex weights, Blends, occlusion zones, and skeleton name as follows:
  * The mesh is the active imported object.
  * Joint names are imported as vertex groups.
  * Vertex weights are imported and assigned relative to the vertex groups they belong to.
  * Blends are imported as shape keys.
  * Occlusion layer (2 for most wearables) is stored in the custom property, "OCC_LAYER"
  * Skeleton name(s) are imported as a custom properties. The name of the property will be of the form SKTM_n where n is an integer. This allows multiple skeletons to be affected. The value of the property is the path to the skeleton, including the directory, e.g. "appearance/skeleton/all_b.skt".
  * Occlusion Zones (either zones occluded BY this model on lower layers, or zones occluded ON this model) are imported as Integer type Custom Properties on the main Blender object. The name of the Custom Property will be OZN_<zone name> and value will be either 0 or 1:
    * Zones occluded by this model: The value of the Custom Property will be 1, signifying that this model occludes those zones on lower-layered meshes. 0 if not. 
    * Zones occluded ON this model: The OZN_ Custom Property will still be added, and Blender Face Maps will be created to signify which triangles belong to which occlusion zone.  
  * Shader name is imported as a material, in cases where there are multiple shaders, each shader is added as a new material.  Also,  each polygon in the mesh is properly assigned to each material.
  * UVs are imported for each shader, and stored in a single UV file within blender.  Again, the UVs are assigned properly to each Poly and material that gets created.  This allows you to import any and all textures from the SWG shader files into blender, and they will map properly.   Please be aware that SWG UVs are written to the MGN files Upside-Down.  Meaning they have to be flipped upright on import for them to work properly in blender.   
* This plugin will export a single object from blender into the MGN file format for SWG.  Items exported are the mesh, UV, Shader names, Bone names, bone weights, Blends, Occlusions and skeleton name.
  * Each item works the same as has already been described above for the importer.   This exporter will fail if multiple objects are selected for export.
  * The exporter will also flip the UV Upside down (mirror on the Y axis), on export,  so you don't need to manually flip the UV.
* Hardpoints: Not properly supported (need a skeleton to know the relative positioning), but the binary data is preserved (and uneditable) in a custom property, "HPTS"
* Texture Renderers: Not properly supported but the binary data is preserved (and uneditable) in a custom property, "TRTS"

MGN Workflow Notes: 
  * If you create a new original mesh/object, you'll first need to choose a skeleton file that your mesh should use.  From that skeleton file, you'll want to use the bone names in the file for your vertex group names in Blender.  Then you can assign vertex weights as necessary.  When finished, make sure that the skeleton file name is set as a SKTM_n custom property where n is an integer. If there are no SKTM_ custom properties, one will be automatically added for the most common skeleton ("appearance/skeleton/all_b.skt"), which might not be what you want.
  * If you import an existing MGN,  the vertex groups will be named properly from the start.  The skeleton file to be used will also be added as a custom property to the mesh.
  * Occlusion zones, either BY this model or ON this model
    * To denote an occlusion zone used (for either case), add an Integer type Custom Property named "OZN_<zone name>" on the Blender object. For the value, set it to either 1 (occluded/invisible) or 0 (not occluded/visible). The reason for including a non-occluded (visible) zone is because another part of the occlusion system (marking the triangles on THIS object that belong to occlusion zones) use the same zone names.
    * Occlusions zones this model occludes (OZN and ZTO chunks) are exported based on the existence of Custom Properties. 
      * The SWG client has a list of zones that can be made invisible for humanoid type objects.  Most creatures do not use occlusions, and any extra layers of clothing or items are made to fit exactly without clipping.  For humanoids that can use extra layers of clothing and items,  SWG uses occlusions to avoid clipping with lower level layers.  So using a human as an example,  it loads with a default skin as layer 1.  If you make a shirt for the human to wear,  the shirt may occupy layer 2,  and without any occlusions the layer 1 body can clip through the shirt during movement in some circumstances.  To avoid this clipping, you can use occlusions, which will make faces of the layer 1 meshes invisible. A long sleeved shirt will occlude the chest, torso_f, torso_b, L_arm, R_arm, and maybe the formarms, and maybe even the waist zones… 
      * It's important to understand that you are not occluding zones on the object you're working with, but rather that you are occluding zones on lower layers of any other mgns on this humanoid.    
    * Occlusion zones ON this model (OZN, OZC, FOZC, and OITL chunks): You can specify the Occlusion Zones on this model by using Blender's "Face Map" feature. This is similar to a Vertex Group, but with faces. The name of the group must be either an occlusion zone ("chest", "torso_f") OR a colon-separated list of occlusion zones ("chest:torso_f"). Import a model like armor_padded_s01_chest_plate_m_l0.mgn to see an example. 
      * IMPORTANT: It's required that any zone name used in a Face Map has a corresponding OZN_<zone name> Custom Property. SWG uses the same data chunk to store both the zones occluded BY this model and the zones occluded ON this model. If you create a Face Map with a zone that isn't also OZN_ custom property, there will be a nasty error on export. .
  * Blends / Shape keys:
    * Blends are the basic deformations of the base mesh that define how the object deforms along with the “body shape” sliders within the SWG client.  There are 4 main Blends for most clothing:  flat_chest, Skinny, Fat, and Muscle.  Heads for the various species have many more blends that correspond to the sliders you see at character creation. The base mesh, is also the Basis shape key.  Search google,  research, and learn for yourself how to properly use and save shape keys within blender.
  * DOT3:
    * DOT3 (aka tangents, aka normalmap coords, aka per-pixel lighting coords) are optionally exportable since some shaders don't want them. Controlled by the export option, "DOT3" 

Limitations:
* MGN Hardpoints and Texture Renderers are stored as binary data in a Custom Property on import, but there is no edit support for these. The existing data will be rewritten at export.  
* If you export an MGN with Face Maps while in Blender's Edit Mode, the Face Map data is not properly retrieved so Occlusion Triangles are not properly set. This will usually result in ALL of your mesh's triangles belonging to the first defined Occlusion zone which can do funky things like a helmet hiding all the geometry on a species' body. Exporting in Object Mode seems to work more reliably.

### SKT (Skeleton) Import / Export:
- Imports skeleton LOD, joint name, parenting, rotation, and position data and converts it into multiple armature objects.
  - SWG skeletons can have 1 to 4 levels of detail (LOD). Skeletal animation can get pretty expensive, so each LOD is used to reduce joint counts. Each LOD is imported as a separate armature object.
  - When creating a new skeleton from scratch, create a separate collection for them and place all of your skeleton's LOD armatures within it. You can see the expected structure by importing an existing skeleton.
  - LOD order in the skeleton is determined by the armature order in the skeleton collection, highest detail to lowest in descending order.
  - Using LODs is good! Don't eliminate them if it can be helped. They can be essential for performance on some users' machines!
  - Most skeletons will have 3 or 4 LODs, depending upon their complexity.
- SWG uses joints instead of bones. The difference is that joints have no length, only position and rotation, whereas bones have all three.
  - The importer will calculate tail positions based on 3 conditions:
   - If the bone has children, the tail position will be the averaged position of all child head positions. If there is only one child, the bone will be connected.
   - If the bone has no children but it has a parent, the tail will continue along the trajectory of the parent for half of its length.
   - If the bone has no children and no parent, then it will move positively on the Y-axis at a distance of 0.05.
- Rotation data in the skeleton is saved per joint and comprised of Pre-Multiply Rotations (RPRE), Bind Pose Rotations (BPRO), and Post-Multiply Rotations (RPST). These are a carryover from Maya, the modeling program uses to animate the characters in SWG.
  - The exporter is still unable to create recreate these rotations accurately. Consider exporting modified pre-existing skeletons or skeletons intended to reuse existing animations to be broken for now.
- When exporting the skeleton, the the portion of the collection name prior to any `.` will be used, eg: a collection named `weegee.bunchofnumbers` will be exported as `weegee.skt`.
  - Armature names are ignored. A naming convention of `<skeleton name>_skt_l<detail level>` is recommended but not necessary.
  - Only deform bones are exported. This allows for the use of control bones like IK while animating (animations are not yet supported!).

### POB (Portalized Object) Import / Export:
- Portalized Objects are objects that contain interiors that can be traversed by other objects, like buildings or caves or bigger spaceships like the YT-2400. They are composite objects comprised of many different parts and are some of the most complex and interesting objects in the game.
  - POBs are divided into rooms. They always contain one exterior "room", known as "r0", and at least (but not limited to) one interior room.
  - Room 0, the exterior, will also have an LOD associated with it, usually with 4 detail level static meshes.
  - All other rooms only ever have 1 static mesh.
  - Each room is connected to each other by objects known as a "portals". Portals act as windows between rooms, allowing players to view into the next room through them.
  - Each room also contains a "floor" object, dictating where a mobile object may traverse.
    - Floor objects typically have NPC pathfinding nodes referred to as "Cell Waypoints".
  - Some rooms may possess collider objects, which may be simple shapes or meshes. Some rooms contain none, as the floor object suffices for collision. These are often used to block character line of sight.
- Due to the complex hierarchy required of POBs, the SWG Helper Functions Menu contains a function to generate a POB hierarchy for you. It is highly recommended to use this as a starting point for any POB projects.
- Studying NoStyleGuy's [POB Tutorial](https://github.com/nostyleguy/io_scene_swg_msh/wiki/Portalized-Object-(POB)) is a must.

## Tool Credits
- [Nick "NoStyleGuy" Rafalski](https://github.com/nostyleguy)
  - Tool creator
- [Alec "Elour" Harley](https://github.com/AlecH92)
  - Hardpoint and collision assistance
- [Tim "RhapsodyInGeek" Maccabe](https://github.com/RhapsodyInGeek)
  - .skt import / export
- [Vera "sinewavey" Lux](https://github.com/sinewavey)
  - .skt import, .skt rotation transform math
