# io_scene_swg_msh
A Blender add-on for importing and export Star Wars Galaxies static mesh files (.msh)
## Blender Version Support
Should work with Blender 2.8+ and 3+
## Features
* Import and Export SWG .msh file (versions 0004 and 0005)
* UVs: Imports UVs, including multiple sets, though for now, though only UV0 will be exported
* Normals: Imported Normals are not used. Blender recomputes them and I couldn't find an API to force the original ones. 
* Extents: Automatically compute Extents (box and sphere)
* Collision Extents: Reads CollisionExtents and stores their binary data in a Custom Property so they can be exported. No edit support, but non-destructive 
* Floor: No support for the FLOR form. Will always be False
* Hardpoints: No support for the HPTS form. Will always be an empty list.
* Shader: Shader name of each SPS is read and stored on a Custom Property which will be used at export. 
 * If you are creating a new object from scratch, add a Custom Property named "Shader" with the shader path as the value (e.g: "shader/defaultappearance.sht"). On export, this will be filled in the SPS's shader NAME chunk. 
