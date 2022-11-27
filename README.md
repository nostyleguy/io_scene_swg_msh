# io_scene_swg_msh
A Blender add-on for importing and export Star Wars Galaxies static mesh files (.msh)
## Blender Version Support
Should work with Blender 2.8+ and 3+
## Features
* Import SWG .msh file (versions 0004 and 0005)
* Should keep UVs, though only UV0 will be exported
* Imported Normals are not used. Blender recomputes them and I couldn't find an API to force the original ones. 
* Extents: Automatically compute Extents (box and sphere)
* Collision Extents: Reads CollisionExtents and stores their binary data in a Custom Property so they can be exported. No edit support, but non-destructive 
* Shader: reads shaders from each SPS and stores them in a Custom Property. No material generation.
* No support for the FLOR (floor) form. Will always be False
* No support for the HPNT (hardpoints)form. Will always be an empty list.
 * If you are creating a new object (not imported), add a Custom Property named "Shader" with the shader path as the value (e.g: "shader/defaultappearance.sht"). On export, this will be filled in the SPS's shader NAME chunk. 


