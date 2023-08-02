# MIT License
#
# Copyright (c) 2022 Nick Rafalski
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import math
from . import support
from . import nsg_iff
from . import vector3D
from . import vertex_buffer_format
from . import extents
from mathutils import Vector

SWG_ROOT=None
class SktFile(object):
    __slots__ = ('path', 'bones')
    def __init__(self, path, bones = None):
        self.path=path
        self.bones=bones

    def __str__(self):
        return f"{self.path}: Bones: {self.bones}"
        
    def __repr__(self):
        return self.__str__()
            
    def load(self):
        iff = nsg_iff.IFF(filename=self.path)
        iff.enterForm("SLOD")
        version=iff.getCurrentName()
        if version in ['0000']:
            iff.enterForm(version)
            iff.enterChunk("INFO")
            iff.exitChunk("INFO")
            iff.enterForm("SKTM")
            
            sktm_version=iff.getCurrentName()
            if sktm_version in ['0002']:
                iff.enterAnyForm()
                iff.enterChunk("INFO")
                iff.exitChunk("INFO")
                iff.enterChunk("NAME")
                if not self.bones:
                    self.bones = []
                while not iff.atEndOfForm():
                    self.bones.append(iff.read_string().lower())
                iff.exitChunk("NAME")
                iff.exitForm()

            else:
                print(f"ERROR: Unsupported SKTM Version: {self.path} Version: {sktm_version}")
                return
        else:
            print(f"ERROR: Unsupported SLOD Version: {self.path} Version: {version}")
            return
class LmgFile(object):
    __slots__ = ('path', 'mgns')
    def __init__(self, path, mgns):
        self.path = path
        self.mgns = mgns

    def write(self):
        iff = nsg_iff.IFF(initial_size=100000)      
        iff.insertForm("MLOD")
        iff.insertForm("0000")

        iff.insertChunk("INFO")
        iff.insert_int16(len(self.mgns))
        iff.exitChunk("INFO")
        for mgn in self.mgns:          
            iff.insertChunk("NAME")        
            iff.insertChunkString("appearance/mesh/"+mgn+".mgn")
            iff.exitChunk("NAME")

        iff.write(self.path)

class SatFile(object):
    __slots__ = ('path', 'mgns', 'skeletons')
    def __init__(self, path, mgns, skeletons):
        self.path = path
        self.mgns = mgns
        self.skeletons = skeletons

    def write(self):
        iff = nsg_iff.IFF(initial_size=100000)      
        iff.insertForm("SMAT")
        iff.insertForm("0003")

        iff.insertChunk("INFO")
        iff.insert_int32(len(self.mgns))
        iff.insert_int32(len(self.skeletons))
        iff.insert_bool(False)
        iff.exitChunk("INFO")
        
        iff.insertChunk("MSGN")
        for mgn in self.mgns:            
            iff.insertChunkString("appearance/mesh/"+mgn+".lmg")
        iff.exitChunk("MSGN")
        
        iff.insertChunk("SKTI")
        for skel in self.skeletons:            
            iff.insertChunkString(skel)            
            iff.insertChunkString("")
        iff.exitChunk("SKTI")
        iff.write(self.path)

class AptFile(object):
    __slots__ = ('path', 'filename')
    def __init__(self, path, filename):
        self.path = path
        self.filename = filename

    def write(self):
        iff = nsg_iff.IFF(initial_size=100000)      
        iff.insertForm("APT ")
        iff.insertForm("0000")
        iff.insertChunk("NAME")
        iff.insertChunkString(self.filename)
        iff.write(self.path)


class LodFile(object):

    __slots__ = ('path', 'mesh','hardpoints','collision','floor', 'lods')
    def __init__(self, path, mesh):
        self.path = path
        self.mesh = mesh
        self.collision = None
        self.hardpoints = []
        self.lods = {}
        self.floor = ""

    def __str__(self):
        return f'Path: {self.path}, Hpts: {str(len(self.hardpoints))} Lods: {str(self.lods)}'

    def __repr__(self):
        return self.__str__()

    def load(self, path):
        iff = nsg_iff.IFF(filename=path)
        #print(f"Name: {iff.getCurrentName()} Length: {iff.getCurrentLength()}")
        
        top = iff.getCurrentName()
        if top != "DTLA":
            print(f"Not an LOD file. First form: {top} should be DTLA!")
            return False
        else:
            iff.enterForm("DTLA")

        version = iff.getCurrentName()
        if version not in ["0007", "0008"]:
            print(f'Unsupported DTLA version: {version}')
            return False
        else: 
            iff.enterForm(version)

        iff.enterForm("APPR")

        version = iff.getCurrentName()
        if version not in ["0003"]:
            print(f'Unsupported APPR version: {version}')
            return False
        else: 
            iff.enterForm(version)

        # Extents (not doing anything with)
        iff.enterForm("EXBX")
        iff.exitForm("EXBX")

        # Collision
        # if iff.enterForm("NULL", True):
        #     self.collision = bytearray(0)
        #     iff.exitForm("NULL")
        # else:
        #     col_data_length = iff.getCurrentLength() + 8
        #     col_form_name = iff.getCurrentName()
        #     self.collision = iff.read_misc(col_data_length)
        #     print(f"Collision form: {col_form_name} Len: {col_data_length}")
        self.collision = extents.Extents.create(iff)

        # Hardpoints
        iff.enterForm("HPTS", True, False)
        while not iff.atEndOfForm():
            iff.enterChunk("HPNT", True)
            rotXx = iff.read_float()
            rotXy = iff.read_float()
            rotXz = iff.read_float()
            posX = iff.read_float()
            rotYx = iff.read_float()
            rotYy = iff.read_float()
            rotYz = iff.read_float()
            posY = iff.read_float()
            rotZx = iff.read_float()
            rotZy = iff.read_float()
            rotZz = iff.read_float()
            posZ = iff.read_float()
            hpntName = iff.read_string()
            self.hardpoints.append([rotXx, rotXy, rotXz, -posX, rotYx, rotYy, rotYz, posY, rotZx, rotZy, rotZz, posZ, hpntName])
            iff.exitChunk("HPNT")
        iff.exitForm("HPTS")

        if iff.enterForm("FLOR", True):
            if iff.enterChunk("DATA", True):
                self.floor = iff.read_string()
                iff.exitChunk("DATA")
            iff.exitForm("FLOR")
        
        iff.exitForm() # APPR Version
        iff.exitForm() # APPR

        # PIVT
        if iff.getCurrentName() == "PIVT":
            iff.enterChunk("PIVT")
            hasPivot = iff.read_bool8()
            iff.exitChunk("PIVT")
        
        print(f"Current: {iff.getCurrentName()} size {iff.getCurrentLength()}")
        iff.enterChunk("INFO")
        while not iff.atEndOfForm():
            id=iff.read_uint32()
            near=iff.read_float()
            far=iff.read_float()
            self.lods[id]=[near,far]
        iff.exitChunk("INFO")

        iff.enterForm("DATA")
        while not iff.atEndOfForm():
            iff.enterChunk("CHLD")
            ind = iff.read_uint32()
            self.lods[ind].append(iff.read_string())
            iff.exitChunk("CHLD")
        iff.exitForm("DATA")

        return True

    def write(self):
        iff = nsg_iff.IFF(initial_size=100000)      
        iff.insertForm("DTLA")
        iff.insertForm("0008")
        
        iff.insertForm("APPR")
        iff.exitForm()

        iff.insertChunk("PIVT")
        iff.insert_int16(0)
        iff.exitChunk("PIVT")

        iff.insertChunk("INFO")
        iff.insert_uint32(0)
        iff.insertFloat(0)
        iff.insertFloat(64000)
        iff.exitChunk("INFO")

        iff.insertForm("DATA")
        iff.insertChunk("CHLD")
        iff.insert_int32(0)
        iff.insertChunkString(self.filename)
        iff.exitChunk("CHLD")
        iff.exitForm("DATA")

        iff.insertForm("RADR")
        iff.insertChunk("INFO")
        iff.insert_bool(False)
        iff.exitChunk("INFO")
        iff.exitForm("RADR")

        iff.insertForm("TEST")
        iff.insertChunk("INFO")
        iff.insert_bool(False)
        iff.exitChunk("INFO")
        iff.exitForm("TEST")

        iff.insertForm("WRIT")
        iff.insertChunk("INFO")
        iff.insert_bool(False)
        iff.exitChunk("INFO")
        iff.exitForm("WRIT")
        
        iff.write(self.path)

class MgnHardpoint(object):
    __slots__ = ('name', 'parent', 'orientation', 'position')
    def __init__(self, name, parent, orientation, position):
        self.name = name
        self.parent = parent
        self.orientation = orientation
        self.position = position
    def __str__(self):
        return f'Name: {self.name}, Parent: {self.parent} Orientation: {self.orientation}, Position: {self.position}'

    def __repr__(self):
        return self.__str__()

class SWGVertex(object):
    __slots = ('pos', 'normal', 'color', 'texs')
    def __init__(self):
        self.texs = []
        self.pos = None
        self.normal = None
        self.color0 = None
        self.color1 = None

    def __str__(self):
        return f'P: {self.pos} N: {self.normal} UV0: {self.texs[0]}'

    def __repr__(self):
        return self.__str__()

class Triangle(object):
    __slots__ = ('p1', 'p2', 'p3')
    def __init__(self, p1 = None, p2 = None, p3 = None):
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        
    def __str__(self):
        return f"[{self.p1}, {self.p2}, {self.p3}]"
    def __repr__(self):
        return self.__str__()

class SWGShader(object):
    __slots__ = ('path', 'main', 'spec', 'normal', 'envm', 'effect', 'customizable', 'transparent')
    def __init__(self, path):
        self.path=path
        self.main=None
        self.spec=None
        self.normal=None
        self.envm=None
        self.customizable=False
        self.transparent=False
        self.effect = None
        self.load()

    def __str__(self):
        return f"[{self.path}, {self.main}, {self.spec}]"
        
    def __repr__(self):
        return self.__str__()

    def stripped_shader_name(self):
        if self.path == "":
            return "defaultappearance"
        else:
            return (support.clean_path(self.path).split('\\')[-1]).split('.')[0]

    def infer_features_from_effect(self):
        if self.effect:
            self.transparent = any([x in self.effect for x in ["alpha", "invis", "water"]])
            #print(f"{self.path} effect: {self.effect} transparent: {self.transparent}")
            
    def load(self):
        iff = nsg_iff.IFF(filename=self.path)
        #print(f"Name: {iff.getCurrentName()} Length: {iff.getCurrentLength()}")
        top_form = iff.getCurrentName()
        if top_form == "CSHD":
            self.customizable = True
            self.load_cshd(iff)
        elif top_form == "SSHT":
            self.customizable = False
            self.load_ssht(iff)
        elif top_form == "SWTS":
            self.customizable = False
            self.load_swts(iff)
        else: 
            print(f"Shader: {self.path} is unsupported shader type: {top_form}. Won't decode!")
            iff.exitForm()

        self.infer_features_from_effect()

    def load_cshd(self, iff):
        iff.enterForm("CSHD")
        version = iff.getCurrentName()
        if version in ["0001"]:            
            iff.enterForm(version)
            self.load_ssht(iff)
            iff.exitForm(version)
        else:            
            print(f"{iff.filename}: unsupported CSHD Version: {version}!")
        iff.exitForm("CSHD")

    def load_ssht(self, iff):
        iff.enterForm("SSHT")
        version = iff.getCurrentName()
        if version in ["0000", "0001"]: 

            iff.enterForm(version)
            if iff.getCurrentName() == "NAME":
                iff.enterChunk("NAME")
                self.effect = iff.read_string()
                iff.exitChunk("NAME")

            iff.enterForm("MATS")
            iff.exitForm("MATS")

            if iff.getCurrentName() == "TXMS":
                iff.enterForm("TXMS")
                count = 0
                while not iff.atEndOfForm():
                    count += 1
                    iff.enterForm("TXM ")
                    iff.enterAnyForm() # version
                    iff.enterChunk("DATA")
                    tag = iff.read_string()[::-1] # reverse tag
                    iff.exitChunk("DATA")
                    iff.enterChunk("NAME")
                    texture= iff.read_string()
                    iff.exitChunk("NAME")
                    iff.exitForm()
                    iff.exitForm("TXM ")
                    #print(f"Tag: {tag}: {texture}")

                    if tag == "MAIN":
                        self.main = texture
                    elif tag == "SPEC":
                        self.spec = texture
                    elif tag in ["CNRM", "NRML"]:
                        self.normal = texture
                    elif tag == "ENVM":
                        self.envm = texture
                #print(f"TXMs: {count}")
                iff.exitForm("TXMS")

            if iff.getCurrentName() == "TCSS":
                iff.enterForm("TCSS")
                iff.exitForm("TCSS")
            

            if iff.getCurrentName() == "TFNS":
                iff.enterForm("TFNS")
                iff.exitForm("TFNS")

            if iff.getCurrentName() == "ARVS":
                iff.enterForm("ARVS")
                iff.exitForm("ARVS")
            

            if iff.getCurrentName() == "SRVS":
                iff.enterForm("SRVS")
                iff.exitForm("SRVS")

            if iff.getCurrentName() == "NAME":
                iff.enterChunk("NAME")
                self.effect = iff.read_string()
                iff.exitChunk("NAME")
                
            iff.exitForm(version)
        else:            
            print(f"{iff.filename}: unsupported SSHT Version: {version}!")
        iff.exitForm("SSHT")

    def load_swts(self, iff):
        iff.enterForm("SWTS")
        version = iff.getCurrentName()
        if version in ["0000"]:            
            iff.enterForm(version)
            if iff.getCurrentName() == "NAME":
                iff.enterChunk("NAME")
                self.effect = iff.read_string()
                iff.exitChunk("NAME")

class SPS(object):
    __slots__ = ('no', 'shader', 'flags', 'verts', 'tris', 'full_shader_path', 'real_shader')
    def __init__(self):
        self.no = 0
        self.shader = ""
        self.flags = 0
        self.verts = []
        self.tris = []
        self.full_shader_path = None
        self.real_shader = None

    def __init__(self, no , shader, flags, verts, tris):
        self.no = no
        self.shader = shader
        self.flags = flags
        self.verts = verts
        self.tris = tris
        self.full_shader_path = None
        self.real_shader = None

    def hasDOT3(self):
        num_uv_sets = vertex_buffer_format.getNumberOfTextureCoordinateSets(self.flags)
        if(num_uv_sets > 0):
            return (vertex_buffer_format.getTextureCoordinateSetDimension(self.flags, num_uv_sets - 1) == 4)
        return False

    def hasColor0(self):
        return vertex_buffer_format.hasColor0(self.flags)

    def hasColor1(self):
        return vertex_buffer_format.hasColor1(self.flags)

    def getNumUVSets(self):
        num_uv_sets = vertex_buffer_format.getNumberOfTextureCoordinateSets(self.flags)
        if(num_uv_sets > 0):
            if(vertex_buffer_format.getTextureCoordinateSetDimension(self.flags, num_uv_sets - 1) == 4):
                num_uv_sets -= 1
        return num_uv_sets

    def stripped_shader_name(self):
        if self.shader == "":
            return "defaultappearance"
        else:
            return self.shader.split('/')[1].split('.')[0]

    def __str__(self):
        return f"SPS_No: {self.no} Shader: {self.shader} Flags: {self.flags} Verts: {len(self.verts)} Tris: {len(self.tris)}"

    def __repr__(self):
        return self.__str__()

class SWGMesh(object):
    __slots__ = ('filename', 'spss', 'extents', 'collision', 'realCollision', 'hardpoints', 'floor', 'root_dir')
    def __init__(self, filename, root):
        global SWG_ROOT
        SWG_ROOT = root
        self.filename = filename
        self.spss = []
        self.extents = []
        self.collision = None
        self.realCollision = None
        self.hardpoints = []
        self.floor = ""
        #self.root_dir = root

    def __str__(self):
        s = f"Filename: {self.filename}\nExtents: {str(self.extents)}\nCollision: {str(self.collision_summary_str())}\nSPS: {len(self.spss)}\n"
        for sps in self.spss:
            s += str(sps)+'\n'
        return s
        
    def __repr__(self):
        return self.__str__()

    def collision_summary_str(self):
        if self.collision:
            first = self.collision[8:12].decode('ASCII')
            return f'Type: {first} Len: {len(self.collision)}'
        else: 
            return "(No Collision)"

    def debug_flags(self, flags, sps_no):

        num_uv_sets = vertex_buffer_format.getNumberOfTextureCoordinateSets(flags)
        print(f'Mesh: {self.filename} SPS: {sps_no} Flags: {flags}')
        print(f'  hasPosition: {vertex_buffer_format.hasPosition(flags)}')
        print(f'  isTransformed: {vertex_buffer_format.isTransformed(flags)}')
        print(f'  hasNormal: {vertex_buffer_format.hasNormal(flags)}')
        print(f'  hasColor0: {vertex_buffer_format.hasColor0(flags)}')
        print(f'  hasColor1: {vertex_buffer_format.hasColor1(flags)}')
        print(f'  hasPointSize: {vertex_buffer_format.hasPointSize(flags)}')
        print(f'  uvSets: {vertex_buffer_format.getNumberOfTextureCoordinateSets(flags)}')
        for i in range(0, num_uv_sets):            
            print(f'  uvDim [{i}]: {vertex_buffer_format.getTextureCoordinateSetDimension(flags, i)}')

        if(num_uv_sets > 0) and (vertex_buffer_format.getTextureCoordinateSetDimension(flags, num_uv_sets - 1) == 4):         
            print(f'Mesh: {self.filename} SPS: {sps_no} Flags: {flags}: Has DOT3!')

        if vertex_buffer_format.hasPointSize(flags):
            print(f'Mesh: {self.filename} SPS: {sps_no} Flags: {flags}: Has PointSize. Never seen that before! Not doing anything with it FYI')
        
        if vertex_buffer_format.hasColor1(flags):
            print(f'Mesh: {self.filename} SPS: {sps_no} Flags: {flags}: Has Color1. Never seen that before! Not doing anything with it FYI')


    def read_vertex(self, flags, iff):
        v = SWGVertex()

        num_uv_sets = vertex_buffer_format.getNumberOfTextureCoordinateSets(flags)
        skip_dot3 = False
        if(num_uv_sets > 0) and (vertex_buffer_format.getTextureCoordinateSetDimension(flags, num_uv_sets - 1) == 4):
            skip_dot3 = True
            num_uv_sets -= 1

        v.texs = []

        if vertex_buffer_format.hasPosition(flags):
            v.pos =  vector3D.Vector3D(iff.read_float(), iff.read_float(), iff.read_float())

        if vertex_buffer_format.hasNormal(flags):
            v.normal =  vector3D.Vector3D(iff.read_float(), iff.read_float(), iff.read_float())

        if vertex_buffer_format.hasPointSize(flags):
            point_size = iff.read_float() # unused

        if vertex_buffer_format.hasColor0(flags):
            # NSG Seems like this should be ARGB per SOE code, but that makes 
            # the Anchorhead Cantina look gross. Used trial and error to determine
            # order: BGRA
            b = iff.read_color()
            g = iff.read_color()
            r = iff.read_color()
            a = iff.read_color()
            v.color0 = [r,g,b,a]

        if vertex_buffer_format.hasColor1(flags):
            # NSG Seems like this should be ARGB per SOE code, but that makes 
            # the Anchorhead Cantina look gross. Used trial and error to determine
            # order: BGRA
            b = iff.read_color()
            g = iff.read_color()
            r = iff.read_color()
            a = iff.read_color()
            v.color1 = [r,g,b,a]

        for i in range(0, num_uv_sets):
            dim = vertex_buffer_format.getTextureCoordinateSetDimension(flags, i)
            v.texs.append([]) 
            for j in range(0, dim):
                v.texs[i].append(iff.read_float())

        if skip_dot3:
            iff.read_float()
            iff.read_float()
            iff.read_float()
            iff.read_float()

        return v

    def load(self):
        iff = nsg_iff.IFF(filename=self.filename)
        #print(f"Name: {iff.getCurrentName()} Length: {iff.getCurrentLength()}")
        iff.enterAnyForm()
        version = iff.getCurrentName()

        if version not in ["0005", "0004"]:
            print(f'Unsupported MESH version: {version}')
            return False

        iff.enterForm(version)
        #print(iff.getCurrentName())
        iff.enterForm("APPR")

        appr_version = iff.getCurrentName()

        if appr_version == "0003":
            iff.enterAnyForm()
            iff.enterForm("EXBX")
            iff.enterForm("0001")
            iff.enterForm("EXSP")
            iff.enterForm("0001")
            iff.enterChunk("SPHR")
            x = iff.read_float()
            y = iff.read_float()
            z = iff.read_float()
            rad = iff.read_float()
            #print(f"X: {x} Y: {y} Z: {z} Radius: {rad}")
            iff.exitChunk("SPHR")
            iff.exitForm("0001")
            iff.exitForm("EXSP")

            iff.enterChunk("BOX ")    
            maxx = iff.read_float()
            maxy = iff.read_float()
            maxz = iff.read_float()
            minx = iff.read_float()
            miny = iff.read_float()
            minz = iff.read_float()
            #print(f"MaxX: {maxx} MaxY: {maxy} MaxZ: {maxz} MinX: {minx} MinY: {miny} MinZ: {minz}")
            self.extents.append([maxx, maxy, maxz])
            self.extents.append([minx, miny, minz])
            iff.exitChunk("BOX ")

            iff.exitForm("0001")
            iff.exitForm("EXBX")

            # Collision stuff
            if iff.enterForm("NULL", True):
                self.collision = bytearray(0)
                iff.exitForm("NULL")
            else:
                col_data_length = iff.getCurrentLength() + 8
                col_form_name = iff.getCurrentName()
                self.collision = iff.read_misc(col_data_length)
                print(f"Collision form: {col_form_name} Len: {col_data_length}")

            #hardpoints
            iff.enterForm("HPTS", True, False)
            while not iff.atEndOfForm():
                iff.enterChunk("HPNT", True)
                rotXx = iff.read_float()
                rotXy = iff.read_float()
                rotXz = iff.read_float()
                posX = iff.read_float()
                rotYx = iff.read_float()
                rotYy = iff.read_float()
                rotYz = iff.read_float()
                posY = iff.read_float()
                rotZx = iff.read_float()
                rotZy = iff.read_float()
                rotZz = iff.read_float()
                posZ = iff.read_float()
                hpntName = iff.read_string()
                self.hardpoints.append([rotXx, rotXy, rotXz, -posX, rotYx, rotYy, rotYz, posY, rotZx, rotZy, rotZz, posZ, hpntName])
                iff.exitChunk("HPNT")
            iff.exitForm("HPTS")

            if iff.enterForm("FLOR", True):
                if iff.enterChunk("DATA", True):
                    self.floor = iff.read_string()
                    iff.exitChunk("DATA")
                iff.exitForm("FLOR")
            
            iff.exitForm()
        else:
            print(f"Warning: Unknown APPR version: {appr_version}")

        iff.exitForm("APPR")

        iff.enterForm("SPS ")
        iff.enterForm("0001")
        iff.enterChunk("CNT ")
        cnt = iff.read_uint32()
        iff.exitChunk("CNT ")

        while(not iff.atEndOfForm()):
            sps_no = iff.getCurrentName()
            iff.enterAnyForm()

            iff.enterChunk("NAME")
            sht=iff.read_string()
            iff.exitChunk("NAME")
            #print(f"SPS {sps_no} Shader: {sht}")

            #print(f"Next: {iff.getCurrentName()}")
            iff.enterChunk("INFO")
            cnt=iff.read_uint32()
            iff.exitChunk("INFO")

            version=iff.getCurrentName()
            if version in ["0000", "0001"]:
                iff.enterForm(version)
                iff.enterChunk("INFO")
                iff.exitChunk("INFO")

                iff.enterForm("VTXA")
                iff.enterForm("0003")

                iff.enterChunk("INFO")
                bit_flag = iff.read_int32()
                self.debug_flags(bit_flag, sps_no)
                num_verts = iff.read_uint32()
                verts = [None] * num_verts
                iff.exitChunk("INFO")

                iff.enterChunk("DATA")
                for i in range(0, num_verts):
                    verts[i] = self.read_vertex(bit_flag, iff)

                iff.exitChunk("DATA")
                iff.exitForm("0003")

                iff.exitForm("VTXA")

                size = iff.getCurrentLength()
                iff.enterChunk("INDX")
                indexes = []
                index_count = iff.read_uint32()
                bpi = (size - 4) // index_count
                #print(f'Size: {size} Size - 4: {size - 4}, index_count: {index_count} bpi: {bpi}')
                for i in range(index_count//3):
                    tri = Triangle()
                    if(bpi == 2):
                        tri.p1 = iff.read_int16()
                        tri.p2 = iff.read_int16()
                        tri.p3 = iff.read_int16()
                    elif(bpi == 4):
                        tri.p1 = iff.read_int32()
                        tri.p2 = iff.read_int32()
                        tri.p3 = iff.read_int32()
                    indexes.append(tri)
                #print(f'Read Index Count: {index_count}')

                iff.exitChunk("INDX")
                iff.exitForm(version)
                print(f"SPS {sps_no} Shader: {sht} Version: {version} Verts: {len(verts)} Tris: {len(indexes)}")

                sps = SPS(sps_no, sht, bit_flag, verts, indexes)

                real_shader_path = support.find_file(sps.shader, SWG_ROOT)
                if real_shader_path:
                    sps.full_shader_path = real_shader_path
                    sps.real_shader = SWGShader(sps.full_shader_path)
                else:
                    print(f"Couldn't locate real shader path for: {sps.shader}")
                self.spss.append(sps)

            else:
                print(f"Warning: Unknown SPS {sps_no} Unhandled version: {version}")
                
            iff.exitForm()

        return True
            
    def write(self, filename):
        iff = nsg_iff.IFF(initial_size=100000)
        # - BEGIN MESH        
        iff.insertForm("MESH")
        iff.insertForm("0005")

        # -- BEGIN APPR
        iff.insertForm("APPR")
        iff.insertForm("0003")

        # --- BEGIN EXTENTS
        iff.insertForm("EXBX")
        iff.insertForm("0001")
        iff.insertForm("EXSP")
        iff.insertForm("0001")

        max = Vector(self.extents[0])
        min = Vector(self.extents[1])        
        center = (max + min) / 2.0
        diff = (max - min) / 2.0
        rad = diff.magnitude

        iff.insertChunk("SPHR")
        iff.insertFloatVector3(center[:])
        iff.insertFloat(rad)
        iff.exitChunk("SPHR")
        iff.exitForm(("0001"))
        iff.exitForm("EXSP")

        iff.insertChunk("BOX ")
        iff.insertFloatVector3(self.extents[0])
        iff.insertFloatVector3(self.extents[1])
        iff.exitChunk("BOX ")

        iff.exitForm("0001")
        iff.exitForm("EXBX")
        # --- END EXTENTS

        # --- BEGIN COLLISION
        if self.collision == None or len(self.collision) == 0 :
            iff.insertForm("NULL")
        else :
            iff.insertForm(self.collision[8:12].decode('ASCII'))
            iff.insertIffData(self.collision[12:])
        iff.exitForm()
        # --- END COLLISION

        # --- BEGIN HARDPOINTS
        iff.insertForm("HPTS")
        if len(self.hardpoints) > 0:
            for hpnt in self.hardpoints:
                iff.insertChunk("HPNT")
                iff.insertFloat(hpnt[0])
                iff.insertFloat(hpnt[1])
                iff.insertFloat(hpnt[2])
                iff.insertFloat(hpnt[3]) #x pos
                iff.insertFloat(hpnt[4])
                iff.insertFloat(hpnt[5])
                iff.insertFloat(hpnt[6])
                iff.insertFloat(hpnt[7]) #y pos
                iff.insertFloat(hpnt[8])
                iff.insertFloat(hpnt[9])
                iff.insertFloat(hpnt[10])
                iff.insertFloat(hpnt[11]) #z pos
                iff.insertChunkString(hpnt[12]) #hpnt name
                iff.exitChunk("HPNT")
        iff.exitForm()
        # --- END HARDPOINTS

        # --- BEGIN FLOOR
        iff.insertForm("FLOR")
        iff.insertChunk("DATA")
        iff.insert_bool(False)
        iff.exitChunk("DATA")
        iff.exitForm("FLOR")
        # --- END EXTENTS

        # -- END APPR
        iff.exitForm("0003")
        iff.exitForm("APPR")

        # -- BEGIN APPR
        iff.insertForm("SPS ")
        iff.insertForm("0001")

        # --- BEGIN CNT
        iff.insertChunk("CNT ")
        iff.insert_uint32(len(self.spss))
        iff.exitChunk("CNT ")

        for i in range(0, len(self.spss)):
            sps = self.spss[i]
            #print(f'Adding SPS {str(i+1).zfill(4)}')
            iff.insertNumberedForm(i+1)
            iff.insertChunk("NAME")
            iff.insertChunkString(sps.shader)
            iff.exitChunk("NAME")
            iff.insertChunk("INFO")
            iff.insert_uint32(1) #"Shader primitive count" - Never seen anything other than 1
            iff.exitChunk("INFO")

            iff.insertForm("0001")
            iff.insertChunk("INFO")
            iff.insert_uint32(9)
            iff.insert_bool(True)
            iff.insert_bool(False)
            iff.exitChunk("INFO")
            iff.insertForm("VTXA")
            iff.insertForm("0003")
            iff.insertChunk("INFO")
            #iff.insert_uint32(4357)
            #iff.insert_uint32(53765)
            iff.insert_uint32(sps.flags)
            self.debug_flags(sps.flags, i)
            iff.insert_uint32(len(sps.verts))
            iff.exitChunk("INFO")
            iff.insertChunk("DATA")
            for v in sps.verts:
                iff.insertFloatVector3((v.pos.x, v.pos.y, v.pos.z))
                iff.insertFloatVector3((v.normal.x, v.normal.y, v.normal.z))

                if vertex_buffer_format.hasColor0(sps.flags):
                    iff.insert_color(v.color0)

                if vertex_buffer_format.hasColor1(sps.flags):
                    iff.insert_color(v.color1)
                
                for uv_set in v.texs:
                    for value in uv_set:
                        iff.insertFloat(value)
            iff.exitChunk("DATA")
            iff.exitForm("0003")
            iff.exitForm("VTXA")

            iff.insertChunk("INDX")
            iff.insert_uint32(len(sps.tris)*3)
            for t in sps.tris:
                iff.insert_uint16(t.p1)
                iff.insert_uint16(t.p2)
                iff.insert_uint16(t.p3)
            iff.exitChunk("INDX")

            iff.exitForm("0001")
            iff.exitForm()


        # -- END APPR
        iff.exitForm("0001")
        iff.exitForm("SPS ")

        iff.write(filename)
        
class SWGBLendShape(object):
    def __init__(self):
        self.name = ""
        self.positions = []
        self.normals = []
        self.dot3 = None

    def __str__(self):
        return f"""Name: {self.name} Positions: {str(len(self.positions))} Norms: {str(len(self.normals))} DOT3: {(str(len(self.dot3)) if self.dot3 else "N/A")}"""

    def __repr__(self):
        return self.__str__()

class SWGPerShaderData(object):
    def __init__(self):
        self.name = ""
        self.pidx = []
        self.nidx = []
        self.dot3 = None
        self.colors = None
        self.txci = []
        self.tcsd = []
        self.num_uvs = 0
        self.uv_dimensions = []
        self.uvs = []
        self.num_prims = 0
        self.prims = []
        self.full_shader_path = None
        self.real_shader = None

    def __str__(self):
        s = f"""Name: {self.name} pidx: {str(len(self.pidx))} nidx: {str(len(self.nidx))} DOT3: {(str(len(self.dot3)) if self.dot3 else "N/A")}"""
        s += "\n"
        s += f"""UVS: {self.num_uvs} -- {', '.join( ("UVs: " + str(len(x)) + " Dim: " + str(len(x[0]))) for x in self.uvs)}"""
        s += "\n"
        s += f"""Prims: {self.num_prims} -- {', '.join( ("Tris: " + str(len(x))) for x in self.prims)}"""
        return s

    def __repr__(self):
        return self.__str__()

    def stripped_shader_name(self):
        if self.name == "":
            return "defaultappearance"
        else:
            return self.name.split('/')[1].split('.')[0]

class SWGMgn(object):
    def __init__(self, filename, root):
        global SWG_ROOT
        SWG_ROOT = root

        self.filename = filename

        self.max_transforms_vertex = 0
        self.max_transforms_shader = 0

        self.num_skeletons = 0
        self.num_vertex_groups = 0
        self.num_positions = 0
        self.num_transform_weight_data = 0
        self.num_normals = 0
        self.num_shaders = 0
        self.num_blends = 0
        
        self.num_occ_zones = 0
        self.num_occ_combo_zones = 0
        self.num_this_occludes = 0
        self.occlusion_layer = 2

        self.occlusions = []
        self.occlusion_zones = None
        self.skeletons = []
        self.bone_names = []

        self.positions = []
        self.normals = []
        self.dot3 = None

        self.twhd = []
        self.twdt = []

        self.vertex_weights = []

        self.blends = []

        self.psdts = []

        self.dynamic_hardpoints = None
        self.static_hardpoints = None

        self.binary_hardpoints = None
        self.binary_trts = None

    def __str__(self):
        s = f"""Filename: {self.filename} 
                max_transforms_vertex: {self.max_transforms_vertex}, 
                max_transforms_shader: {self.max_transforms_shader},
                self.num_skeletons {self.num_skeletons},
                self.num_vertex_groups: {self.num_vertex_groups},
                self.num_positions: {self.num_positions},
                self.num_transform_weight_data: {self.num_transform_weight_data},
                self.num_normals: {self.num_normals},
                self.num_shaders: {self.num_shaders},
                self.num_blends: {self.num_blends},
                self.num_occ_zones: {self.num_occ_zones},
                self.num_occ_combo_zones: {self.num_occ_combo_zones},
                self.num_this_occludes: {len(self.occlusions)},
                self.occlusion_layer: {self.occlusion_layer}
                self.skeletons: {",".join(self.skeletons)}
                self.bone_names: {",".join(self.bone_names)}
                self.positions: {len(self.positions)}
                self.twhd: {len(self.twhd)}
                self.twdt: {len(self.twdt)}
                self.dot3: {(str(len(self.dot3)) if self.dot3 else "NA")}
                self.occlusions: {', '.join(str(x) for x in self.occlusions)}
                self.occlusion_zones: {((', '.join(str(x) for x in self.occlusion_zones)) if self.occlusion_zones else "NONE")}
                self.dynamic_hardpoints: {((', '.join(str(x) for x in self.dynamic_hardpoints)) if self.dynamic_hardpoints else "NONE")}
                self.static_hardpoints: {((', '.join(str(x) for x in self.static_hardpoints)) if self.static_hardpoints else "NONE")}
                """
        #s += "\n".join(str(x) for x in self.positions)
        s += 'Blends: \n' + "\n".join(str(x) for x in self.blends)

        s += 'Per Shader Data: \n' + "\n".join(str(x) for x in self.psdts)
        return s
        
    def __repr__(self):
        return self.__str__()

    def normalize_vertex_weights(self, weights):
        for i , posn in enumerate(weights):
            total = 0
            for weight in posn:
                total += weight[1]

            for weight in posn:
                before = weight[1]
                weight[1] = weight[1]/total 
                if weight[1] != before:
                    print(f"Vert {i} changed weight for bone {weight[0]} from {before} to {weight[1]}")
        
    def load(self):
        iff = nsg_iff.IFF(filename=self.filename)
        print(f"Name: {iff.getCurrentName()} Length: {iff.getCurrentLength()}")
        iff.enterAnyForm()
        version = iff.getCurrentName()

        if version not in ["0003", "0004",]:
            print(f'Unsupported MGN version: {version}')
            return False
        
        print(f'Doing Mgn version: {version}')

        iff.enterForm(version)
        #print(iff.getCurrentName())
        iff.enterChunk("INFO")

        self.max_transforms_vertex = iff.read_uint32()
        self.max_transforms_shader = iff.read_uint32()

        self.num_skeletons = iff.read_uint32()
        self.num_vertex_groups = iff.read_uint32()
        self.num_positions = iff.read_uint32()
        self.num_transform_weight_data = iff.read_uint32()
        self.num_normals = iff.read_uint32()
        self.num_shaders = iff.read_uint32()
        self.num_blends = iff.read_uint32()
        
        self.num_occ_zones = iff.read_uint16()
        self.num_occ_combo_zones = iff.read_uint16()
        self.num_this_occludes = iff.read_uint16()
        self.occlusion_layer = iff.read_uint16() 

        iff.exitChunk("INFO")
        
        iff.enterChunk("SKTM")
        while not iff.atEndOfForm():
            self.skeletons.append(iff.read_string())
        iff.exitChunk("SKTM")
        
        iff.enterChunk("XFNM")
        while not iff.atEndOfForm():
            self.bone_names.append(iff.read_string())
        iff.exitChunk("XFNM")

        iff.enterChunk("POSN")  
        self.positions = [0] * self.num_positions
        i=0      
        while not iff.atEndOfForm():
            self.positions[i] = (iff.read_float(), iff.read_float(), -iff.read_float())
            i += 1
        iff.exitChunk("POSN")

        self.twhd = [0] * self.num_positions
        i = 0
        iff.enterChunk("TWHD")        
        while not iff.atEndOfForm():
            self.twhd[i] = iff.read_uint32()
            i += 1
        iff.exitChunk("TWHD")

        iff.enterChunk("TWDT")     
        self.twdt = [[0,0.0]] * self.num_transform_weight_data   
        i = 0
        while not iff.atEndOfForm():
            self.twdt[i] = [iff.read_uint32(), iff.read_float()]
            #print(f'Twdt: {i} ({str(self.twdt[i])})')
            i += 1
        iff.exitChunk("TWDT")

        i = 0
        p = 0
        self.vertex_weights = [None] * self.num_positions
        for p, h in enumerate(self.twhd):
            these_weights = []
            sum=0
            for x in range(0,h):
                twdt = self.twdt[i]
                sum += twdt[1]
                these_weights.append(twdt)
                i += 1
            
            # if sum != 1.0:
            #     print(f' *** WARN ***: Vertex Weight sum for vert: {p} != 1.0 : {sum}')
            self.vertex_weights[p] = these_weights
        
        self.normalize_vertex_weights(self.vertex_weights)

        #self.positions = list(zip(self.positions, self.vertex_weights))

        iff.enterChunk("NORM")     
        self.normals = [None] * self.num_normals   
        i = 0
        while not iff.atEndOfForm():
            self.normals[i] = (iff.read_float(), iff.read_float(), iff.read_float())
            i += 1
        iff.exitChunk("NORM")

        if iff.getCurrentName() == "DOT3":
            iff.enterChunk("DOT3")     
            num_dot3 = iff.read_uint32()
            self.dot3 = [None] * num_dot3   
            i = 0
            while not iff.atEndOfForm():
                self.dot3[i] = [iff.read_float(), iff.read_float(), iff.read_float(), iff.read_float()]
                i += 1
            iff.exitChunk("DOT3")

        if iff.getCurrentName() == "HPTS":
            data_length = iff.getCurrentLength() + 8
            form_name = iff.getCurrentName()
            self.binary_hardpoints = iff.read_misc(data_length)
            print(f"binary_hardpoints form: {data_length} Len: {form_name}")

            #iff.enterForm("HPTS")
            # if iff.getCurrentName() == "STAT":
            #     iff.enterChunk("STAT")
            #     self.static_hardpoints = []
            #     count = iff.read_int16()
            #     while not iff.atEndOfForm():
            #         self.static_hardpoints.append(MgnHardpoint(iff.read_string(), iff.read_string(), iff.read_vector4(), iff.read_vector3()))
            #     iff.exitChunk("STAT")
            # if iff.getCurrentName() == "DYN ":
            #     iff.enterChunk("DYN ")
            #     count = iff.read_int16()
            #     self.dynamic_hardpoints = []
            #     while not iff.atEndOfForm():
            #         self.dynamic_hardpoints.append(MgnHardpoint(iff.read_string(), iff.read_string(), iff.read_vector4(), iff.read_vector3()))
            #     iff.exitChunk("DYN ")  
            #iff.exitForm("HPTS")

        if iff.getCurrentName() == "BLTS":
            iff.enterForm("BLTS")
            while not iff.atEndOfForm():
                iff.enterForm("BLT ")
                blt = SWGBLendShape()
                iff.enterChunk("INFO")
                num_positions = iff.read_uint32()
                num_norms = iff.read_uint32()
                blt.name = iff.read_string()
                iff.exitChunk("INFO")
                self.blends.append(blt)

                iff.enterChunk("POSN")
                while not iff.atEndOfForm():
                    blt.positions.append( (iff.read_uint32(), (iff.read_float(), iff.read_float(), iff.read_float())))
                iff.exitChunk("POSN")

                if iff.getCurrentName == "NORM":
                    iff.enterChunk("NORM")
                    while not iff.atEndOfForm():
                        blt.normals.append( (iff.read_uint32(), (iff.read_float(), iff.read_float(), iff.read_float())))
                    iff.exitChunk("NORM")

                if iff.getCurrentName() == "DOT3":
                    iff.enterChunk("DOT3")     
                    num_dot3 = iff.read_int32()
                    blt.dot3 = []
                    #for i in range(0, num_dot3):
                    while not iff.atEndOfForm():
                        blt.dot3.append([(iff.read_int32(), (iff.read_float(), iff.read_float(), iff.read_float()))])
                    iff.exitChunk("DOT3")

                iff.exitForm("BLT ")
            iff.exitForm("BLTS")

        if iff.getCurrentName() == "OZN ":
            iff.enterChunk("OZN ")
            i = 0
            while not iff.atEndOfForm():
                self.occlusions.append([iff.read_string(), i, 1])
                i += 1
            iff.exitChunk("OZN ")

        if iff.getCurrentName() == "FOZC":
            iff.enterChunk("FOZC")
            focz_count = iff.read_int16()
            i = 0
            while not iff.atEndOfForm():
                n = iff.read_int16()
                self.occlusions[i][1] = n
                i += 1
            iff.exitChunk("FOZC")

        if iff.getCurrentName() == "OZC ":
            iff.enterChunk("OZC ")
            self.occlusion_zones=[]
            while not iff.atEndOfForm():
                this_zone=[]
                count = iff.read_int16()
                for i in range(0,count):
                    n = iff.read_int16()
                    this_zone.append(next(x[0] for x in self.occlusions if x[1] == n))
                self.occlusion_zones.append([":".join(this_zone),[]])
            iff.exitChunk("OZC ")

        if iff.getCurrentName() == "ZTO ":
            iff.enterChunk("ZTO ")
            for occ in self.occlusions:
                occ[2] = 0
            while not iff.atEndOfForm():
                index = iff.read_int16()
                for occ in self.occlusions:
                    if occ[1] == index:
                        occ[2] = 1
                        #print(f"Occ: {str(occ)} is ZTO: {index} Setting occluded to: {occ[2]}")
            iff.exitChunk("ZTO ")

        global_tri_index=0
        while iff.getCurrentName() == "PSDT":
            psdt = SWGPerShaderData()
            iff.enterForm("PSDT")

            iff.enterChunk("NAME")
            psdt.name = iff.read_string()
            real_shader_path = support.find_file(psdt.name, SWG_ROOT)
            if real_shader_path:
                psdt.full_shader_path = real_shader_path
                psdt.real_shader = SWGShader(psdt.full_shader_path)
            else:
                print(f"Couldn't locate real shader path for: {psdt.name}")

            iff.exitChunk("NAME")

            iff.enterChunk("PIDX")
            num = iff.read_uint32()
            while not iff.atEndOfForm():
                i = iff.read_uint32()
                psdt.pidx.append(i)

            iff.exitChunk("PIDX")

            iff.enterChunk("NIDX")
            while not iff.atEndOfForm():
                psdt.nidx.append(iff.read_uint32())
            iff.exitChunk("NIDX")

            if iff.getCurrentName() == "DOT3":
                psdt.dot3 = []
                iff.enterChunk("DOT3")
                while not iff.atEndOfForm():
                    psdt.dot3.append(iff.read_uint32())
                iff.exitChunk("DOT3")

            if iff.getCurrentName() == "VDCL":
                psdt.colors = []
                iff.enterChunk("VDCL")
                while not iff.atEndOfForm():
                    psdt.colors.append([iff.read_byte(), iff.read_byte(), iff.read_byte(), iff.read_byte()])
                iff.exitChunk("VDCL")

            if iff.getCurrentName() == "TXCI":
                iff.enterChunk("TXCI")
                psdt.num_uvs = iff.read_uint32()
                while not iff.atEndOfForm():
                    psdt.uv_dimensions.append(iff.read_uint32())
                iff.exitChunk("TXCI")

                iff.enterForm("TCSF")
                i = 0
                while not iff.atEndOfForm(): 
                    dim = psdt.uv_dimensions[i]
                    num = iff.getCurrentLength() // 4 // dim             
                    psdt.uvs.append([None] * num)                 
                    iff.enterChunk("TCSD")
                    for n in range(0, num):
                        uv = []
                        for m in range(0, dim):
                            uv.append(iff.read_float())
                        psdt.uvs[i][n] = uv
                    iff.exitChunk("TCSD")                    
                    i += 1
                iff.exitForm("TCSF")

            iff.enterForm("PRIM")
            iff.enterChunk("INFO")
            psdt.num_prims = iff.read_uint32()
            iff.exitChunk("INFO")
            while not iff.atEndOfForm():
                prim_type = iff.getCurrentName()
                iff.enterChunk(prim_type)

                triangle_list = []
                if prim_type == "OITL":
                    num_tris = iff.read_uint32()
                    #for n in range(0, num_tris):
                    while not iff.atEndOfForm():
                        occ = iff.read_int16()
                        self.occlusion_zones[occ][1].append(global_tri_index)
                        global_tri_index += 1
                        p1 = iff.read_int32()
                        p2 = iff.read_int32()
                        p3 = iff.read_int32()
                        tri = Triangle(p1, p2, p3)
                        triangle_list.append(tri)
                    psdt.prims.append(triangle_list)
                elif prim_type == "ITL ":
                    num_tris = iff.read_uint32()
                    for n in range(0, num_tris):
                        p1 = iff.read_int32()
                        p2 = iff.read_int32()
                        p3 = iff.read_int32()
                        tri = Triangle(p1, p2, p3)
                        triangle_list.append(tri)
                    psdt.prims.append(triangle_list)
                else:
                    print(f'Unhandled PRIM type: {prim_type}')
                iff.exitChunk(prim_type)

            iff.exitForm("PRIM")
            self.psdts.append(psdt)
            iff.exitForm("PSDT")

        if iff.getCurrentName() == "TRTS":
            data_length = iff.getCurrentLength() + 8
            form_name = iff.getCurrentName()
            self.binary_trts = iff.read_misc(data_length)
            print(f"binary_trts form: {data_length} Len: {form_name}")


        print(self)

    def get_zones_this_occludes(self):
        i = 0
        for zone in self.occlusions:
            if zone[2] == 1:
                i += 1
        return i

    def write(self):
        tris_with_no_facemap=[]
        iff = nsg_iff.IFF(initial_size=10000)
        print(f"Name: {iff.getCurrentName()} Length: {iff.getCurrentLength()}")
        iff.insertForm("SKMG")
        iff.insertForm("0004")

        iff.insertChunk("INFO")
        iff.insert_uint32(self.max_transforms_vertex)
        iff.insert_uint32(self.max_transforms_shader)
        iff.insert_uint32(len(self.skeletons))
        iff.insert_uint32(len(self.bone_names))
        iff.insert_uint32(len(self.positions))
        iff.insert_uint32(len([vv for v in self.twdt for vv in v ]))
        iff.insert_uint32(len(self.normals))
        iff.insert_uint32(len(self.psdts))
        iff.insert_uint32(len(self.blends))
        
        iff.insert_uint16(len(self.occlusions))
        iff.insert_uint16(len(self.occlusion_zones) if self.occlusion_zones else 0)
        iff.insert_uint16(self.get_zones_this_occludes())
        iff.insert_uint16(self.occlusion_layer) 
        iff.exitChunk("INFO")
        
        iff.insertChunk("SKTM")
        for skel in self.skeletons:
            iff.insertChunkString(skel)
        iff.exitChunk("SKTM")

        iff.insertChunk("XFNM")
        for bone in self.bone_names:
            iff.insertChunkString(bone)
        iff.exitChunk("XFNM")

        iff.insertChunk("POSN")
        for pos in self.positions:
            #pos[0] = -pos[0]
            iff.insertFloatVector3(pos)
        iff.exitChunk("POSN")

        iff.insertChunk("TWHD")
        for twdt in self.twdt:
            iff.insert_uint32(len(twdt))
        iff.exitChunk("TWHD")
        
        iff.insertChunk("TWDT")
        for twdt in self.twdt:
            for weight in twdt:
                iff.insert_uint32(weight[0])
                iff.insertFloat(weight[1])
        iff.exitChunk("TWDT")

        iff.insertChunk("NORM")
        for norm in self.normals:
            iff.insertFloatVector3(norm)
        iff.exitChunk("NORM") 

        if self.dot3:
            iff.insertChunk("DOT3")
            iff.insert_uint32(len(self.dot3))
            for dot3 in self.dot3:
                iff.insertFloatVector4(dot3)
            iff.exitChunk("DOT3")
        
        if self.binary_hardpoints:
            iff.insertForm(self.binary_hardpoints[8:12].decode('ASCII'))
            iff.insertIffData(self.binary_hardpoints[12:])
            iff.exitForm()
        
        if(len(self.blends) > 0):
            iff.insertForm("BLTS")
            for blend in self.blends:
                iff.insertForm("BLT ")

                iff.insertChunk("INFO")
                iff.insert_uint32(len(blend.positions))
                iff.insert_uint32(len(blend.normals))
                iff.insertChunkString(blend.name)
                iff.exitChunk("INFO")

                iff.insertChunk("POSN")
                for p in blend.positions:
                    iff.insert_uint32(p[0])
                    iff.insertFloatVector3(p[1])
                iff.exitChunk("POSN")

                iff.insertChunk("NORM")
                for n in blend.normals:
                    iff.insert_uint32(n[0])
                    iff.insertFloatVector3(n[1])
                iff.exitChunk("NORM")

                if blend.dot3:
                    iff.insertChunk("DOT3")
                    iff.insert_uint32(len(blend.dot3))
                    for n in blend.dot3:
                        iff.insert_uint32(n[0])
                        iff.insertFloatVector3(n[1])
                    iff.exitChunk("DOT3")

                iff.exitForm("BLT ")
            iff.exitForm("BLTS")

        if len(self.occlusions) > 0:
            iff.insertChunk("OZN ")
            for occ in self.occlusions:
                iff.insertChunkString(occ[0])
            iff.exitChunk("OZN ")

        if len(self.occlusions) > 0:
            iff.insertChunk("FOZC")
            count=len(self.occlusions)
            iff.insert_int16(count)
            # for n in range(0, count):
            #     iff.insert_int16(n)
            for occ in self.occlusions:
                iff.insert_int16(occ[1])
                print(f"Wrote FOZC {occ[0]} which is {occ[1]}")
            iff.exitChunk("FOZC")

        if self.occlusion_zones and len(self.occlusion_zones) > 0:
            iff.insertChunk("OZC ")
            for i, occ in enumerate(self.occlusion_zones):
                print(f"OZC {i}: {occ[0]} has tris: {str(len(occ[1]))}")
                zones=occ[0].split(':')                
                iff.insert_int16(len(zones))
                for zone_name in zones:
                    for zone in self.occlusions:
                        if zone[0] == zone_name:
                            iff.insert_int16(zone[1])
                            print(f"Adding OZC {zone[1]} which is {zone_name}")
            iff.exitChunk("OZC ")

        if len(self.occlusions) > 0:
            iff.insertChunk("ZTO ")
            for occ in self.occlusions:
                if occ[2] == 1:
                    iff.insert_int16(occ[1])
            iff.exitChunk("ZTO ")

        global_tri_index=0
        for psdt in self.psdts:
            iff.insertForm("PSDT")
            iff.insertChunk("NAME")
            iff.insertChunkString(f'shader/{psdt.name}.sht')
            iff.exitChunk("NAME")

            iff.insertChunk("PIDX")
            iff.insert_uint32(len(psdt.pidx))
            for pidx in psdt.pidx:
                iff.insert_uint32(pidx)
            iff.exitChunk("PIDX")

            iff.insertChunk("NIDX")
            for nidx in psdt.nidx:
                iff.insert_uint32(nidx)
            iff.exitChunk("NIDX")

            if psdt.dot3:
                iff.insertChunk("DOT3")
                for dot3 in psdt.dot3:
                    iff.insert_uint32(dot3)
                iff.exitChunk("DOT3")

            if len(psdt.uvs) > 0:
                iff.insertChunk("TXCI")
                iff.insert_int32(len(psdt.uvs))
                for uv_set in psdt.uvs:
                    iff.insert_int32(len(uv_set[0]))
                iff.exitChunk("TXCI")

                iff.insertForm("TCSF")
                for uv_set in psdt.uvs:
                    iff.insertChunk("TCSD")
                    for uv in uv_set:
                        iff.insertFloat(uv[0])
                        iff.insertFloat(1 - uv[1]) 
                    iff.exitChunk("TCSD")
                iff.exitForm("TCSF")

            iff.insertForm("PRIM")
            
            iff.insertChunk("INFO")
            iff.insert_uint32(len(psdt.prims))
            iff.exitChunk("INFO")

            if self.occlusion_zones:
                for prim in psdt.prims:
                    iff.insertChunk("OITL")
                    iff.insert_uint32(len(prim) // 3)
                    for value in prim:
                        if global_tri_index % 3 == 0:
                            found=False
                            for i, occ in enumerate(self.occlusion_zones):
                                if (global_tri_index // 3) in occ[1]:
                                    iff.insert_int16(i)
                                    found=True
                                    break
                            if not found:
                                #print(f"WARNING: Tri: {global_tri_index // 3} Not in any Face Map (occlusion zone). Assuming 0!")
                                tris_with_no_facemap.append(global_tri_index)
                                iff.insert_int16(0)
                        iff.insert_uint32(value)
                        global_tri_index += 1
                    iff.exitChunk("OITL")
            else:
                for prim in psdt.prims:
                    iff.insertChunk("ITL ")
                    iff.insert_uint32(len(prim) // 3)
                    for value in prim:
                        iff.insert_uint32(value)
                    iff.exitChunk("ITL ")
            iff.exitForm("PRIM")
            
            iff.exitForm("PSDT")

        if self.binary_trts:
            iff.insertForm(self.binary_trts[8:12].decode('ASCII'))
            iff.insertIffData(self.binary_trts[12:])
            iff.exitForm()

        if self.occlusion_zones and len(tris_with_no_facemap) > 0:
            print(f"WARNING: Tris without assigned occlusion zone: {str(len(tris_with_no_facemap))}")
        iff.write(self.filename)