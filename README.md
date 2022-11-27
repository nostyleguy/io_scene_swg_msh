# io_scene_swg_msh
A Blender add-on for importing and export Star Wars Galaxies static mesh files (.msh)
## Blender Version Support
Should work with Blender 2.8+ and 3+
## Features
* Import SWG .msh file (versions 0004 and 0005)
* Should keep UVs, though only UV0 will be exported
* Extents: Automatically compute Extents (box and sphere)
* Collision Extents: Reads CollisionExtents and stores their binary data in a Custom Property so they can be exported. No edit support, but non-destructive 
* Shader: reads shaders from each SPS and stores them in a Custom Property. No material generation.
 * If you are creating a new object (not imported), add a Custom Property named "Shader" with the shader path as the value "shader/defaultappearance.sht". On export, this will be filled in the SPS's shader NAME chunk. 


