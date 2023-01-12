# io_scene_swg_msh
A Blender add-on for importing and exporting Star Wars Galaxies static mesh files (.msh)
## Blender Version Support
Should work with Blender 2.9+ and 3+
## Features
* Import and Export SWG .msh file (versions 0004 and 0005)
* UVs: Imports UVs, including multiple sets, though for now, only UV0 will be exported
* Normals: Imported Normals are not used. Blender recomputes them and I couldn't find an API to force the original ones. 
* Vertex Colors: Not supported (can read a mesh with them, but will be unused and lost). No export support.
* Extents: Automatically compute Extents (box and sphere)
* Collision Extents: Reads CollisionExtents and stores their binary data in a Custom Property so they can be exported. No edit support, but non-destructive 
* Floor: Saves floor file name in custom property
* Hardpoints: Supports hardpoints as empty "Arrows" objects. The name of the Arrows empty will become the name of the hardpoint at export. To add a hardpoint:
  * Create an empty Arrows object in Object mode:
    * Shift+A -> Empty -> Arrows 
  * Make the new Empty a child of a mesh object:
    * In Object Mode, multi-select the Arrow then the Mesh
    * Ctrl+P -> Object 
* Shader: Shader name of each SPS is read and stored on a Custom Property which will be used at export. 
  * If you are creating a new object from scratch, add a Custom Property named "Shader" with the shader path as the value (e.g: "shader/defaultappearance.sht"). On export, this will be filled in the SPS's shader NAME chunk. 
